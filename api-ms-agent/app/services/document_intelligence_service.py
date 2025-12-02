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

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

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
class DocumentAnalysisResult:
    """Result from document analysis."""

    content: str
    pages: int
    tables: list[dict[str, Any]] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


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

    def _get_client(self):
        """Get or create the Document Intelligence client."""
        if self._use_fallback:
            raise ValueError(
                "Azure Document Intelligence not configured. "
                "Only PDF, TXT, MD, and HTML files are supported in fallback mode."
            )

        if self._client is None:
            # Lazy import Azure SDK only when needed
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.ai.documentintelligence.models import (
                AnalyzeResult,
                DocumentAnalysisFeature,
            )
            from azure.core.credentials import AzureKeyCredential
            from azure.identity import DefaultAzureCredential

            # Store references for use in analyze_document
            self._AnalyzeResult = AnalyzeResult
            self._DocumentAnalysisFeature = DocumentAnalysisFeature

            endpoint = settings.azure_document_intelligence_endpoint

            if settings.use_managed_identity:
                self._credential = DefaultAzureCredential()
                self._client = DocumentIntelligenceClient(
                    endpoint=endpoint,
                    credential=self._credential,
                )
                logger.info("Using managed identity for Document Intelligence")
            else:
                if not settings.azure_document_intelligence_key:
                    raise ValueError(
                        "Azure Document Intelligence key not configured. "
                        "Set AZURE_DOCUMENT_INTELLIGENCE_KEY or use managed identity."
                    )
                self._client = DocumentIntelligenceClient(
                    endpoint=endpoint,
                    credential=AzureKeyCredential(settings.azure_document_intelligence_key),
                )
                logger.info("Using API key for Document Intelligence")

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
            text_content = content.decode("utf-8", errors="ignore")
            return DocumentAnalysisResult(
                content=text_content,
                pages=1,
                metadata={"source": "text_decode", "filename": filename},
            )

        client = self._get_client()

        try:
            # Use the prebuilt-layout model for general document analysis
            # It extracts text, tables, and structure from documents
            poller = client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=BytesIO(content),
                content_type=content_type or "application/octet-stream",
            )

            result = poller.result()

            # Extract full text content
            full_content = result.content or ""

            # Extract paragraphs for structured access
            paragraphs = []
            if result.paragraphs:
                paragraphs = [p.content for p in result.paragraphs if p.content]

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
                metadata={
                    "source": "azure_document_intelligence",
                    "model": "prebuilt-layout",
                    "filename": filename,
                },
            )

        except Exception as e:
            logger.error("document_analysis_failed", error=str(e), filename=filename)
            raise ValueError(f"Failed to analyze document: {e}") from e

    async def close(self) -> None:
        """Close the client and release resources."""
        if self._client:
            self._client.close()
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
