"""Documents router - API endpoints for document indexing and vector search."""

import logging
from datetime import datetime, UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user_from_request
from app.auth.models import KeycloakUser
from app.services.cosmos_db_service import CosmosDbService, get_cosmos_db_service
from app.services.document_intelligence_service import (
    DocumentIntelligenceService,
    get_document_intelligence_service,
    SUPPORTED_EXTENSIONS,
)
from app.services.embedding_service import EmbeddingService, get_embedding_service

router = APIRouter()

logger = logging.getLogger(__name__)


class IndexDocumentRequest(BaseModel):
    """Request body for indexing a document."""

    content: str = Field(..., min_length=1, description="Document content to index")
    document_id: str | None = Field(default=None, description="Optional document ID")
    title: str | None = Field(default=None, description="Optional document title")
    metadata: dict | None = Field(default=None, description="Optional metadata")
    chunk_size: int = Field(default=1000, ge=100, le=4000, description="Chunk size")
    chunk_overlap: int = Field(default=200, ge=0, le=500, description="Chunk overlap")


class IndexDocumentResponse(BaseModel):
    """Response from document indexing."""

    document_id: str = Field(..., description="The indexed document ID")
    chunks_created: int = Field(..., description="Number of chunks created")
    message: str = Field(..., description="Status message")


class SearchRequest(BaseModel):
    """Request body for vector search."""

    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")
    document_id: str | None = Field(default=None, description="Optional document filter")
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Min similarity")


class SearchResultItem(BaseModel):
    """A single search result."""

    chunk_id: str = Field(..., description="Chunk identifier")
    document_id: str = Field(..., description="Parent document ID")
    content: str = Field(..., description="Chunk content")
    similarity: float = Field(..., description="Similarity score")
    metadata: dict = Field(default_factory=dict, description="Chunk metadata")


class SearchResponse(BaseModel):
    """Response from vector search."""

    query: str = Field(..., description="Original search query")
    results: list[SearchResultItem] = Field(..., description="Search results")
    total: int = Field(..., description="Total results returned")


class DocumentItem(BaseModel):
    """A document in the list."""

    id: str = Field(..., description="Document ID")
    document_id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    chunk_count: int = Field(default=0, description="Number of chunks")


class DocumentListResponse(BaseModel):
    """Response for listing documents."""

    documents: list[DocumentItem] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")


class UploadDocumentResponse(BaseModel):
    """Response from document upload."""

    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    user_id: str | None = Field(None, description="User ID who uploaded")
    total_chunks: int = Field(..., description="Number of chunks created")
    total_pages: int | None = Field(None, description="Total pages (for PDFs)")
    uploaded_at: str = Field(..., description="Upload timestamp")


@router.post(
    "/upload",
    response_model=UploadDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a document",
)
async def upload_document(
    file: UploadFile,
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    doc_intelligence: Annotated[
        DocumentIntelligenceService, Depends(get_document_intelligence_service)
    ],
    current_user: Annotated[KeycloakUser, Depends(get_current_user_from_request)],
) -> UploadDocumentResponse:
    """
    Upload and process a document for indexing.

    Supports multiple formats including:
    - PDF (including scanned/image-based with OCR)
    - Microsoft Office: DOCX, XLSX, PPTX
    - Web: HTML
    - Text: Markdown, plain text
    - Images: JPEG, PNG, BMP, TIFF
    """
    if not file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded")

    # Validate file type
    file_extension = f".{file.filename.lower().split('.')[-1]}" if file.filename else ""

    if not doc_intelligence.is_supported_format(file.filename or ""):
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS.keys()))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Supported formats: {supported}",
        )

    user_id = current_user.sub if current_user else "anonymous"

    try:
        content_bytes = await file.read()

        # Use Azure Document Intelligence to analyze the document
        result = await doc_intelligence.analyze_document(
            content=content_bytes,
            filename=file.filename or "unknown",
            content_type=file.content_type,
        )

        content = result.content
        total_pages = result.pages

        if not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from document. "
                "The document may be empty or corrupted.",
            )

        # Index the document with embeddings
        document = await embedding_service.index_document(
            content=content,
            user_id=user_id,
            document_id=None,  # Auto-generate
            metadata={
                "title": file.filename,
                "filename": file.filename,
                "content_type": file.content_type,
                "pages": total_pages,
                "tables_count": len(result.tables),
                "source": result.metadata.get("source", "unknown"),
            },
            chunk_size=1000,
            chunk_overlap=200,
        )

        return UploadDocumentResponse(
            id=document.id,
            filename=file.filename or "unknown",
            user_id=user_id,
            total_chunks=len(document.chunks),
            total_pages=total_pages,
            uploaded_at=datetime.now(UTC).isoformat(),
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error processing document upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload error: {str(e)}",
        ) from e


@router.get("/supported-formats")
async def get_supported_formats() -> dict:
    """Get list of supported document formats."""
    return {
        "formats": list(SUPPORTED_EXTENSIONS.keys()),
        "descriptions": {
            ".pdf": "PDF documents (including scanned with OCR)",
            ".docx": "Microsoft Word documents",
            ".doc": "Microsoft Word (legacy)",
            ".xlsx": "Microsoft Excel spreadsheets",
            ".xls": "Microsoft Excel (legacy)",
            ".pptx": "Microsoft PowerPoint presentations",
            ".ppt": "Microsoft PowerPoint (legacy)",
            ".html": "HTML web pages",
            ".htm": "HTML web pages",
            ".md": "Markdown files",
            ".txt": "Plain text files",
            ".jpg": "JPEG images",
            ".jpeg": "JPEG images",
            ".png": "PNG images",
            ".bmp": "BMP images",
            ".tiff": "TIFF images",
            ".tif": "TIFF images",
        },
    }


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    current_user: Annotated[KeycloakUser, Depends(get_current_user_from_request)],
    limit: int = 50,
) -> DocumentListResponse:
    """List all indexed documents for the current user."""
    user_id = current_user.sub

    try:
        documents = await embedding_service.list_documents(user_id, limit)
        return DocumentListResponse(
            documents=[
                DocumentItem(
                    id=doc["id"],
                    document_id=doc["document_id"],
                    title=doc.get("title") or f"Document {doc['id'][:8]}...",
                    created_at=doc.get("created_at"),
                    chunk_count=doc.get("chunk_count", 0),
                )
                for doc in documents
            ],
            total=len(documents),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List error: {str(e)}") from e


@router.post("/index", response_model=IndexDocumentResponse)
async def index_document(
    request: IndexDocumentRequest,
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    current_user: Annotated[KeycloakUser, Depends(get_current_user_from_request)],
) -> IndexDocumentResponse:
    """
    Index a document for vector search.

    The document is chunked and each chunk is embedded and stored in Cosmos DB.
    """
    user_id = current_user.sub

    try:
        document = await embedding_service.index_document(
            content=request.content,
            user_id=user_id,
            document_id=request.document_id,
            metadata={
                "title": request.title,
                **(request.metadata or {}),
            },
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )

        return IndexDocumentResponse(
            document_id=document.id,
            chunks_created=len(document.chunks),
            message=f"Document indexed successfully with {len(document.chunks)} chunks",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing error: {str(e)}") from e


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    current_user: Annotated[KeycloakUser, Depends(get_current_user_from_request)],
) -> SearchResponse:
    """
    Perform vector similarity search across indexed documents.
    """
    user_id = current_user.sub

    try:
        results = await embedding_service.search(
            query=request.query,
            user_id=user_id,
            document_id=request.document_id,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )

        return SearchResponse(
            query=request.query,
            results=[
                SearchResultItem(
                    chunk_id=r.chunk_id,
                    document_id=r.document_id,
                    content=r.content,
                    similarity=r.similarity,
                    metadata=r.metadata,
                )
                for r in results
            ],
            total=len(results),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}") from e


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    current_user: Annotated[KeycloakUser, Depends(get_current_user_from_request)],
) -> dict:
    """Delete a document and all its chunks."""
    user_id = current_user.sub

    try:
        count = await embedding_service.delete_document(document_id, user_id)
        return {
            "status": "deleted",
            "document_id": document_id,
            "chunks_deleted": count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete error: {str(e)}") from e


@router.get("/health")
async def documents_health(
    cosmos: Annotated[CosmosDbService, Depends(get_cosmos_db_service)],
) -> dict:
    """Health check for the documents service including Cosmos DB status."""
    cosmos_health = await cosmos.health_check()
    return {
        "status": "ok",
        "service": "documents",
        "cosmos_db": cosmos_health,
    }
