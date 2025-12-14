"""
Azure Document Intelligence Service for document parsing.

This service uses Azure Document Intelligence (formerly Form Recognizer) to extract
text and structure from various document formats including:
- PDF (including scanned/image-based PDFs with OCR)
- DOCX (Microsoft Word)
- XLSX (Microsoft Excel)
- PPTX (Microsoft PowerPoint)
- HTML
- Images (JPEG, PNG, BMP, TIFF)

Falls back to pypdf for PDF files when Document Intelligence is not configured.
"""

import asyncio
import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any
from urllib.parse import urlparse

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


# Supported file extensions and their MIME types
SUPPORTED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".html": "text/html",
    ".htm": "text/html",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".md": "text/markdown",
    ".txt": "text/plain",
}


@dataclass
class ParagraphWithPage:
    """A paragraph with its page number."""

    content: str
    page_number: int  # 1-based page number


@dataclass
class DocumentAnalysisResult:
    """Result from document analysis."""

    content: str
    pages: int
    tables: list[dict[str, Any]] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    paragraphs_with_pages: list[ParagraphWithPage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _create_proxy_polling_method(proxy_base_url: str):
    """
    Create a custom polling method that rewrites Operation-Location URLs to go through the proxy.

    The Azure Document Intelligence SDK uses LRO (Long Running Operations) which return an
    Operation-Location header pointing to the Azure endpoint. When using a proxy, we need to
    rewrite these URLs to go through the proxy instead of directly to Azure.

    Args:
        proxy_base_url: The base URL of the proxy (e.g., https://proxy.example.com/document-intelligence)

    Returns:
        A custom LROBasePolling instance that rewrites URLs
    """
    from azure.core.polling.base_polling import LROBasePolling, OperationResourcePolling

    class ProxyOperationResourcePolling(OperationResourcePolling):
        """Custom polling that rewrites Operation-Location URLs to go through the proxy."""

        def __init__(self, proxy_url: str, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._proxy_url = proxy_url.rstrip("/")

        def _set_async_url_if_present(self, response) -> None:
            """Override to rewrite the Operation-Location URL to use the proxy."""
            original_url = response.headers.get(self._operation_location_header)
            if original_url:
                # Parse the original URL to extract the path
                parsed = urlparse(original_url)
                # The path after /documentintelligence/
                # Original: https://xxx.cognitiveservices.azure.com/documentintelligence/documentModels/...
                # We want: https://proxy/document-intelligence/documentintelligence/documentModels/...
                path_match = re.search(r"/documentintelligence(/.*)", parsed.path)
                if path_match:
                    new_path = f"/documentintelligence{path_match.group(1)}"
                    self._async_url = f"{self._proxy_url}{new_path}"
                    if parsed.query:
                        self._async_url += f"?{parsed.query}"
                else:
                    # Fallback: just use the path as-is
                    self._async_url = f"{self._proxy_url}{parsed.path}"
                    if parsed.query:
                        self._async_url += f"?{parsed.query}"

                logger.debug(
                    "rewriting_operation_location",
                    original_url=original_url,
                    rewritten_url=self._async_url,
                )

            location_url = response.headers.get("location")
            if location_url:
                # Also rewrite the location header if present
                parsed = urlparse(location_url)
                path_match = re.search(r"/documentintelligence(/.*)", parsed.path)
                if path_match:
                    new_path = f"/documentintelligence{path_match.group(1)}"
                    self._location_url = f"{self._proxy_url}{new_path}"
                    if parsed.query:
                        self._location_url += f"?{parsed.query}"
                else:
                    self._location_url = f"{self._proxy_url}{parsed.path}"
                    if parsed.query:
                        self._location_url += f"?{parsed.query}"

    class ProxyLROBasePolling(LROBasePolling):
        """LRO polling that uses the proxy for all polling requests."""

        def __init__(self, proxy_url: str, timeout: int = 30, **kwargs):
            # Create custom lro_algorithms with our proxy-aware polling
            lro_algorithms = [
                ProxyOperationResourcePolling(proxy_url),
            ]
            super().__init__(timeout=timeout, lro_algorithms=lro_algorithms, **kwargs)

    return ProxyLROBasePolling(proxy_base_url)


class DocumentIntelligenceService:
    """Service for analyzing documents using Azure Document Intelligence."""

    def __init__(self) -> None:
        """Initialize the Document Intelligence service."""
        self._client = None
        self._credential = None
        self._use_fallback = not settings.azure_document_intelligence_endpoint
        if self._use_fallback:
            logger.warning(
                "Document Intelligence endpoint not configured, using pypdf fallback for PDFs"
            )
        logger.info("DocumentIntelligenceService initialized")

    async def _get_client(self):
        """Get or create the Document Intelligence client."""
        if self._use_fallback:
            raise ValueError(
                "Azure Document Intelligence not configured. "
                "Only PDF, TXT, MD, and HTML files are supported in fallback mode."
            )

        if self._client is None:
            # Lazy import Azure SDK only when needed - use async client
            from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
            from azure.ai.documentintelligence.models import (
                AnalyzeResult,
                DocumentAnalysisFeature,
            )
            from azure.core.credentials import AzureKeyCredential
            from azure.identity.aio import DefaultAzureCredential

            # Store references for use in analyze_document
            self._AnalyzeResult = AnalyzeResult
            self._DocumentAnalysisFeature = DocumentAnalysisFeature

            endpoint = settings.azure_document_intelligence_endpoint

            # Validate endpoint format
            if not endpoint:
                raise ValueError("Document Intelligence endpoint is not configured")

            # Log endpoint for debugging (mask sensitive parts)
            logger.debug(
                "initializing_document_intelligence_client",
                endpoint=endpoint,
                endpoint_valid=endpoint.startswith("https://"),
                use_managed_identity=settings.use_managed_identity,
            )

            # Ensure endpoint doesn't have trailing slash
            endpoint = endpoint.rstrip("/")

            if settings.use_managed_identity:
                self._credential = DefaultAzureCredential()
                self._client = DocumentIntelligenceClient(
                    endpoint=endpoint,
                    credential=self._credential,
                )
                logger.info(
                    "Using managed identity for Document Intelligence",
                    endpoint=endpoint,
                )
            else:
                if not settings.azure_document_intelligence_key:
                    raise ValueError(
                        "Azure Document Intelligence key not configured. "
                        "Set AZURE_DOCUMENT_INTELLIGENCE_KEY or use managed identity."
                    )
                # Log key presence (not the actual key)
                key = settings.azure_document_intelligence_key
                logger.debug(
                    "using_api_key_auth",
                    key_length=len(key) if key else 0,
                    key_preview=f"{key[:4]}...{key[-4:]}" if key and len(key) > 8 else "***",
                )
                self._client = DocumentIntelligenceClient(
                    endpoint=endpoint,
                    credential=AzureKeyCredential(key),
                )
                logger.info(
                    "Using API key for Document Intelligence",
                    endpoint=endpoint,
                )

        return self._client

    @staticmethod
    def is_supported_format(filename: str) -> bool:
        """Check if the file format is supported."""
        if not filename:
            return False
        extension = f".{filename.lower().split('.')[-1]}"
        return extension in SUPPORTED_EXTENSIONS

    @staticmethod
    def get_supported_extensions() -> list[str]:
        """Get list of supported file extensions."""
        return list(SUPPORTED_EXTENSIONS.keys())

    @staticmethod
    def is_text_based(filename: str) -> bool:
        """Check if the file is a simple text-based format that doesn't need DI."""
        if not filename:
            return False
        extension = f".{filename.lower().split('.')[-1]}"
        return extension in [".md", ".txt", ".html", ".htm"]

    async def analyze_document(
        self,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> DocumentAnalysisResult:
        """
        Analyze a document and extract text content.

        Args:
            content: The document content as bytes
            filename: The original filename (used for format detection)
            content_type: Optional MIME type

        Returns:
            DocumentAnalysisResult with extracted text and metadata
        """
        # For simple text files, just decode directly
        if self.is_text_based(filename):
            logger.debug(
                "processing_text_file",
                filename=filename,
                content_length=len(content),
            )
            text_content = content.decode("utf-8", errors="ignore")
            return DocumentAnalysisResult(
                content=text_content,
                pages=1,
                metadata={"source": "text_decode", "filename": filename},
            )

        # Determine content type for the document
        extension = f".{filename.lower().split('.')[-1]}" if filename else ""
        resolved_content_type = content_type or SUPPORTED_EXTENSIONS.get(
            extension, "application/octet-stream"
        )

        logger.info(
            "starting_document_analysis",
            filename=filename,
            content_length=len(content),
            content_type=resolved_content_type,
            extension=extension,
            endpoint=settings.azure_document_intelligence_endpoint,
        )

        client = await self._get_client()

        try:
            logger.debug(
                "calling_document_intelligence_api",
                model_id="prebuilt-layout",
                content_type=resolved_content_type,
                content_size_bytes=len(content),
            )

            # Check if we're using a proxy (endpoint doesn't end with cognitiveservices.azure.com)
            endpoint = settings.azure_document_intelligence_endpoint
            is_proxy = not endpoint.rstrip("/").endswith(".cognitiveservices.azure.com")

            if is_proxy:
                # Use custom polling that rewrites URLs to go through the proxy
                logger.debug(
                    "using_proxy_polling",
                    proxy_endpoint=endpoint,
                )
                polling_method = _create_proxy_polling_method(endpoint)
                poller = await client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    body=BytesIO(content),
                    content_type=resolved_content_type,
                    polling=polling_method,
                )
            else:
                # Use default polling for direct Azure endpoint
                poller = await client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    body=BytesIO(content),
                    content_type=resolved_content_type,
                )

            logger.debug(
                "document_intelligence_polling",
                operation_id=getattr(poller, "operation_id", "unknown"),
                status=str(poller.status()) if hasattr(poller, "status") else "unknown",
            )

            timeout_s = float(getattr(settings, "document_intelligence_timeout_seconds", 300.0))
            try:
                result = await asyncio.wait_for(poller.result(), timeout=timeout_s)
            except TimeoutError as exc:
                raise ValueError(
                    f"Document Intelligence timed out after {timeout_s} seconds"
                ) from exc

            logger.debug(
                "document_intelligence_result_received",
                has_content=bool(result.content),
                content_length=len(result.content) if result.content else 0,
                has_pages=bool(result.pages),
                page_count=len(result.pages) if result.pages else 0,
                has_paragraphs=bool(result.paragraphs),
                has_tables=bool(result.tables),
            )

            # Extract full text content
            full_content = result.content or ""

            # Extract paragraphs for structured access (legacy: just content)
            paragraphs = []
            # Extract paragraphs with page numbers for citations
            paragraphs_with_pages = []
            if result.paragraphs:
                for p in result.paragraphs:
                    if p.content:
                        paragraphs.append(p.content)
                        # Get page number from bounding_regions (1-based)
                        page_num = 1  # Default to page 1
                        if p.bounding_regions and len(p.bounding_regions) > 0:
                            page_num = p.bounding_regions[0].page_number
                        paragraphs_with_pages.append(
                            ParagraphWithPage(content=p.content, page_number=page_num)
                        )

            # Extract tables as structured data
            tables = []
            if result.tables:
                for table in result.tables:
                    table_data = {
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "cells": [],
                    }
                    if table.cells:
                        for cell in table.cells:
                            table_data["cells"].append(
                                {
                                    "row": cell.row_index,
                                    "column": cell.column_index,
                                    "content": cell.content,
                                }
                            )
                    tables.append(table_data)

            # Count pages
            page_count = len(result.pages) if result.pages else 1

            logger.info(
                "document_analyzed",
                filename=filename,
                pages=page_count,
                content_length=len(full_content),
                tables=len(tables),
                paragraphs=len(paragraphs),
            )

            return DocumentAnalysisResult(
                content=full_content,
                pages=page_count,
                tables=tables,
                paragraphs=paragraphs,
                paragraphs_with_pages=paragraphs_with_pages,
                metadata={
                    "source": "azure_document_intelligence",
                    "model": "prebuilt-layout",
                    "filename": filename,
                },
            )

        except Exception as e:
            # Enhanced error logging to diagnose issues
            error_type = type(e).__name__
            error_message = str(e)

            # Check for common Azure SDK error types
            extra_info = {}
            if hasattr(e, "response"):
                response = e.response
                extra_info["status_code"] = getattr(response, "status_code", None)
                extra_info["reason"] = getattr(response, "reason", None)
                # Try to get response body for debugging
                try:
                    if hasattr(response, "text"):
                        body_text = response.text()
                        extra_info["response_body_preview"] = body_text[:500] if body_text else None
                    elif hasattr(response, "content"):
                        extra_info["response_body_preview"] = str(response.content)[:500]
                except Exception:
                    pass
            if hasattr(e, "error"):
                extra_info["azure_error"] = str(e.error)
            if hasattr(e, "message"):
                extra_info["azure_message"] = e.message

            logger.error(
                "document_analysis_failed",
                error=error_message,
                error_type=error_type,
                filename=filename,
                content_length=len(content),
                content_type=resolved_content_type,
                endpoint=settings.azure_document_intelligence_endpoint,
                **extra_info,
            )

            # Provide more helpful error messages based on error type
            if "Expecting value" in error_message:
                raise ValueError(
                    f"Document Intelligence API returned invalid JSON response. "
                    f"This may indicate an endpoint configuration issue or service error. "
                    f"Endpoint: {settings.azure_document_intelligence_endpoint}, "
                    f"Error: {error_message}"
                ) from e
            elif "401" in error_message or "Unauthorized" in error_message.lower():
                raise ValueError(
                    f"Authentication failed for Document Intelligence. "
                    f"Check your API key or managed identity configuration. "
                    f"Error: {error_message}"
                ) from e
            elif "404" in error_message or "Not Found" in error_message:
                raise ValueError(
                    f"Document Intelligence endpoint not found. "
                    f"Check your endpoint URL: {settings.azure_document_intelligence_endpoint}. "
                    f"Error: {error_message}"
                ) from e
            else:
                raise ValueError(f"Failed to analyze document: {error_message}") from e

    async def close(self) -> None:
        """Close the client and release resources."""
        if self._client:
            await self._client.close()
            self._client = None
        if self._credential:
            await self._credential.close()
            self._credential = None
        logger.info("DocumentIntelligenceService closed")


# Singleton instance
_document_intelligence_service: DocumentIntelligenceService | None = None


def get_document_intelligence_service() -> DocumentIntelligenceService:
    """Get or create the Document Intelligence service instance."""
    global _document_intelligence_service
    if _document_intelligence_service is None:
        _document_intelligence_service = DocumentIntelligenceService()
    return _document_intelligence_service
