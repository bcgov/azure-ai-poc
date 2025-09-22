"""
Document router for document management and processing.

This router provides document management functionality including:
- Document upload and processing (PDF, Markdown, HTML)
- Document listing and deletion
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.auth.dependencies import RequireAuth, require_roles
from app.auth.models import KeycloakUser
from app.services.document_service import UploadedFile, get_document_service


class DocumentResponseDto(BaseModel):
    """Document response DTO for upload responses."""

    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    user_id: str | None = Field(None, description="User ID who uploaded the document")
    total_chunks: int = Field(..., description="Number of chunks created")
    total_pages: int | None = Field(None, description="Total pages (for PDFs)")
    uploaded_at: str = Field(..., description="Upload timestamp")


router = APIRouter(tags=["documents"])


@router.post(
    "/upload",
    summary="Upload and process a document",
    description="Upload and process a document (PDF, Markdown, or HTML) for Q&A",
    response_model=DocumentResponseDto,
    responses={
        201: {
            "description": "Document successfully uploaded and processed",
            "content": {
                "application/json": {
                    "example": {
                        "id": "doc_123456",
                        "filename": "example.pdf",
                        "user_id": "user123",
                        "total_chunks": 15,
                        "total_pages": 10,
                        "uploaded_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        400: {"description": "Bad request - Invalid file type or file too large"},
        401: {"description": "Unauthorized - Invalid or missing JWT token"},
        403: {"description": "Forbidden - Insufficient permissions"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload (max 100MB)"),
    current_user: Annotated[KeycloakUser, RequireAuth] = None,
    _: Annotated[
        None, Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant"))
    ] = None,
    document_service=Depends(get_document_service),
) -> DocumentResponseDto:
    """Upload and process a document for Q&A."""

    if not file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded")

    # Validate file type
    allowed_types = [
        "application/pdf",
        "text/markdown",
        "text/x-markdown",
        "text/html",
        "text/plain",
    ]

    allowed_extensions = [".pdf", ".md", ".markdown", ".html", ".htm", ".txt"]
    file_extension = f".{file.filename.lower().split('.')[-1]}" if file.filename else ""

    if file.content_type not in allowed_types and file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, Markdown (.md), HTML (.html, .htm), and text files are supported",
        )

    # Read file content
    try:
        content = await file.read()

        # Create UploadedFile object
        uploaded_file = UploadedFile(
            filename=file.filename or "unknown",
            content=content,
            content_type=file.content_type or "application/octet-stream",
            size=len(content),
        )

        # Process document
        result = await document_service.process_document(uploaded_file, current_user.sub)

        # Return clean response
        return DocumentResponseDto(
            id=result.id,
            filename=result.filename,
            user_id=result.user_id,
            total_chunks=len(result.chunk_ids),
            total_pages=result.total_pages,
            uploaded_at=result.uploaded_at,
        )

    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except Exception as error:
        logging.error(f"Error processing document upload: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(error)}",
        ) from error


@router.get(
    "",
    summary="Get all documents for the current user",
    description="Retrieve a list of all documents uploaded by the current user",
    response_model=list[DocumentResponseDto],
    responses={
        200: {
            "description": "Documents retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "doc_123456",
                            "filename": "example.pdf",
                            "user_id": "user123",
                            "total_chunks": 15,
                            "total_pages": 10,
                            "uploaded_at": "2024-01-15T10:30:00Z",
                        }
                    ]
                }
            },
        },
        401: {"description": "Unauthorized - Invalid or missing JWT token"},
        403: {"description": "Forbidden - Insufficient permissions"},
    },
)
async def get_documents(
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant"))],
    document_service=Depends(get_document_service),
) -> list[DocumentResponseDto]:
    """Get all documents for the current user."""
    import traceback

    request_user = getattr(current_user, "sub", None)
    logging.debug("[get_documents] Start - user_sub=%s", request_user)
    try:
        documents = await document_service.get_all_documents(user_id=request_user)
        logging.debug(
            "[get_documents] Retrieved %d documents for user_sub=%s", len(documents), request_user
        )
        if documents:
            first = documents[0]
            # Safely log a subset of first doc fields (avoid large logs)
            logging.debug(
                "[get_documents] First doc sample: id=%s filename=%s chunk_ids=%d uploaded_at=%s",
                getattr(first, "id", None),
                getattr(first, "filename", None),
                len(getattr(first, "chunk_ids", []) or []),
                getattr(first, "uploaded_at", None),
            )

        response = [
            DocumentResponseDto(
                id=doc.id,
                filename=doc.filename,
                user_id=doc.user_id,
                total_chunks=len(getattr(doc, "chunk_ids", []) or []),
                total_pages=doc.total_pages,
                uploaded_at=doc.uploaded_at,
            )
            for doc in documents
        ]
        logging.debug(
            "[get_documents] Serialized %d documents for response (user_sub=%s)",
            len(response),
            request_user,
        )
        return response
    except HTTPException:
        # Re-raise untouched
        raise
    except Exception as error:  # noqa: BLE001
        tb = traceback.format_exc(limit=20)
        logging.error(
            "[get_documents] Unhandled error user_sub=%s error=%r traceback=%s",
            request_user,
            error,
            tb,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents",
        ) from error


@router.get(
    "/{document_id}",
    summary="Get document details",
    description="Get details of a specific document",
    response_model=DocumentResponseDto,
    responses={
        200: {"description": "Document details retrieved successfully"},
        404: {"description": "Document not found"},
        401: {"description": "Unauthorized - Invalid or missing JWT token"},
        403: {"description": "Forbidden - Insufficient permissions"},
    },
)
async def get_document(
    document_id: str,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant"))],
    document_service=Depends(get_document_service),
) -> DocumentResponseDto:
    """Get details of a specific document."""

    try:
        document = await document_service.get_document(document_id, current_user.sub)

        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        return DocumentResponseDto(
            id=document.id,
            filename=document.filename,
            user_id=document.user_id,
            total_chunks=len(document.chunk_ids),
            total_pages=document.total_pages,
            uploaded_at=document.uploaded_at,
        )

    except HTTPException:
        raise
    except Exception as error:
        logging.error(f"Error getting document: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document: {str(error)}",
        ) from error


@router.delete(
    "/{document_id}",
    summary="Delete a document",
    description="Delete a document and all its associated chunks",
    responses={
        204: {"description": "Document deleted successfully"},
        404: {"description": "Document not found"},
        401: {"description": "Unauthorized - Invalid or missing JWT token"},
        403: {"description": "Forbidden - Insufficient permissions"},
    },
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: str,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant"))],
    document_service=Depends(get_document_service),
) -> None:
    """Delete a document and all its chunks."""

    try:
        deleted = await document_service.delete_document(document_id, current_user.sub)

        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    except HTTPException:
        raise
    except Exception as error:
        logging.error(f"Error deleting document: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(error)}",
        ) from error
