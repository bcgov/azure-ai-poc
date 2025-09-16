"""
Document router for document management and processing.

This router provides document management functionality including:
- Document upload and processing (PDF, Markdown, HTML)
- Document-based Q&A with context-aware responses
- Document listing and deletion
- Search across documents
"""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import RequireAuth, require_roles
from app.auth.models import KeycloakUser
from app.services.document_service import UploadedFile, get_document_service


class QuestionDto(BaseModel):
    """Question DTO for document Q&A."""

    question: str = Field(..., description="Question to ask about the document")
    document_id: str = Field(..., description="ID of the document to query")


class AnswerDto(BaseModel):
    """Answer DTO for document Q&A responses."""

    answer: str = Field(..., description="AI assistant's answer")
    document_id: str = Field(..., description="Document ID that was queried")
    question: str = Field(..., description="Original question")
    timestamp: datetime = Field(..., description="Response timestamp")


class DocumentResponseDto(BaseModel):
    """Document response DTO for upload responses."""

    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    user_id: str | None = Field(None, description="User ID who uploaded the document")
    total_chunks: int = Field(..., description="Number of chunks created")
    total_pages: int | None = Field(None, description="Total pages (for PDFs)")
    uploaded_at: str = Field(..., description="Upload timestamp")


class SearchDto(BaseModel):
    """Search DTO for document search."""

    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of top results to return")


class SearchResultDto(BaseModel):
    """Search result DTO."""

    content: str = Field(..., description="Chunk content")
    filename: str = Field(..., description="Document filename")
    document_id: str = Field(..., description="Document ID")
    chunk_index: int = Field(..., description="Chunk index within document")
    similarity: float = Field(..., description="Similarity score")
    uploaded_at: str = Field(..., description="Document upload timestamp")


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
        None, Depends(require_roles(["azure-ai-poc-super-admin", "ai-poc-participant"]))
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
    _: Annotated[None, Depends(require_roles(["azure-ai-poc-super-admin", "ai-poc-participant"]))],
    document_service=Depends(get_document_service),
) -> list[DocumentResponseDto]:
    """Get all documents for the current user."""
    try:
        paginated_result = await document_service.get_all_documents(user_id=current_user.sub)

        # Convert ProcessedDocument objects to DocumentResponseDto
        documents = []
        for doc in paginated_result.documents:
            documents.append(
                DocumentResponseDto(
                    id=doc.id,
                    filename=doc.filename,
                    user_id=doc.user_id,
                    total_chunks=len(doc.chunk_ids),
                    total_pages=doc.total_pages,
                    uploaded_at=doc.uploaded_at,
                )
            )

        return documents

    except Exception as error:
        logging.error(f"Error retrieving documents: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(error)}",
        ) from error


@router.post(
    "/ask",
    summary="Ask a question about a specific document",
    description="Ask a question about a specific document and get an AI-generated answer",
    response_model=AnswerDto,
    responses={
        200: {
            "description": "Question answered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "answer": "The document discusses the implementation of AI systems...",
                        "document_id": "doc_123456",
                        "question": "What is the main topic?",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        400: {"description": "Bad request - Missing question or document ID"},
        404: {"description": "Document not found"},
        401: {"description": "Unauthorized - Invalid or missing JWT token"},
        403: {"description": "Forbidden - Insufficient permissions"},
    },
)
async def ask_question(
    question_dto: QuestionDto,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles(["azure-ai-poc-super-admin", "ai-poc-participant"]))],
    document_service=Depends(get_document_service),
) -> AnswerDto:
    """Ask a question about a specific document."""

    try:
        answer = await document_service.answer_question(
            question_dto.document_id, question_dto.question, current_user.sub
        )

        return AnswerDto(
            answer=answer,
            document_id=question_dto.document_id,
            question=question_dto.question,
            timestamp=datetime.utcnow(),
        )

    except ValueError as error:
        if "Document not found" in str(error):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            ) from error
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except Exception as error:
        logging.error(f"Error answering question: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {str(error)}",
        ) from error


@router.post(
    "/ask/stream",
    summary="Ask a question about a document with streaming response",
    description="Ask a question and receive a Server-Sent Events stream of the AI response",
    responses={
        200: {
            "description": "Streaming answer response",
            "content": {
                "text/event-stream": {
                    "example": 'data: {"type":"token","content":"The document"}\n\n'
                }
            },
            "headers": {
                "Content-Type": {"description": "text/event-stream"},
                "Cache-Control": {"description": "no-cache"},
                "Connection": {"description": "keep-alive"},
            },
        },
        400: {"description": "Bad request - Missing question or document ID"},
        404: {"description": "Document not found"},
        401: {"description": "Unauthorized - Invalid or missing JWT token"},
        403: {"description": "Forbidden - Insufficient permissions"},
    },
)
async def ask_question_stream(
    question_dto: QuestionDto,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles(["azure-ai-poc-super-admin", "ai-poc-participant"]))],
    document_service=Depends(get_document_service),
) -> StreamingResponse:
    """Ask a question about a document with streaming response."""

    async def generate_stream():
        """Generate Server-Sent Events stream."""
        import json

        try:
            # Send start event
            start_event = {
                "type": "start",
                "document_id": question_dto.document_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            yield f"data: {json.dumps(start_event)}\n\n"

            # Stream the response
            async for chunk in document_service.answer_question_streaming(
                question_dto.document_id, question_dto.question, current_user.sub
            ):
                if chunk:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

            # Send completion event
            end_event = {"type": "end", "timestamp": datetime.utcnow().isoformat() + "Z"}
            yield f"data: {json.dumps(end_event)}\n\n"

        except ValueError as error:
            if "Document not found" in str(error):
                error_event = {
                    "type": "error",
                    "message": "Document not found",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
                yield f"data: {json.dumps(error_event)}\n\n"
            else:
                error_event = {
                    "type": "error",
                    "message": str(error),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
                yield f"data: {json.dumps(error_event)}\n\n"
        except Exception as error:
            error_event = {
                "type": "error",
                "message": f"Failed to answer question: {str(error)}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@router.get(
    "/",
    summary="List user's documents",
    description="Get a list of all documents uploaded by the current user",
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
async def list_documents(
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles(["azure-ai-poc-super-admin", "ai-poc-participant"]))],
    document_service=Depends(get_document_service),
) -> list[DocumentResponseDto]:
    """List all documents for the current user."""

    try:
        documents = await document_service.get_all_documents(current_user.sub)

        return [
            DocumentResponseDto(
                id=doc.id,
                filename=doc.filename,
                user_id=doc.user_id,
                total_chunks=len(doc.chunk_ids),
                total_pages=doc.total_pages,
                uploaded_at=doc.uploaded_at,
            )
            for doc in documents
        ]

    except Exception as error:
        logging.error(f"Error listing documents: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(error)}",
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
    _: Annotated[None, Depends(require_roles(["azure-ai-poc-super-admin", "ai-poc-participant"]))],
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
    _: Annotated[None, Depends(require_roles(["azure-ai-poc-super-admin", "ai-poc-participant"]))],
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
