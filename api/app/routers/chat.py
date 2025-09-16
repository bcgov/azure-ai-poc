"""
Chat router for AI conversation endpoints.

This router provides general AI chat functionality including:
- Question answering with context-aware responses
- Streaming responses for real-time conversation
- Role-based access control
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import RequireAuth, require_roles
from app.auth.models import KeycloakUser
from app.services.azure_openai_service import get_azure_openai_service


class ChatQuestionDto(BaseModel):
    """Chat question request model."""

    question: str = Field(
        ...,
        description="The question to ask the AI assistant",
        example="Hello, how can you help me today?",
    )


class ChatResponseDto(BaseModel):
    """Chat response model."""

    answer: str = Field(..., description="AI assistant's response")
    timestamp: datetime = Field(..., description="Response timestamp")


router = APIRouter(tags=["chat"])


@router.post(
    "/ask",
    summary="Ask a general question to the AI chat assistant",
    description="Ask a question to the AI assistant and get a complete response",
    response_model=ChatResponseDto,
    responses={
        200: {
            "description": "Chat response generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "answer": (
                            "Hello! I'm here to help you with questions and "
                            "provide information. How can I assist you today?"
                        ),
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        401: {"description": "Unauthorized - Invalid or missing JWT token"},
        403: {"description": "Forbidden - Insufficient permissions"},
    },
)
async def ask_question(
    chat_question: ChatQuestionDto,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles(["azure-ai-poc-super-admin", "ai-poc-participant"]))],
    azure_openai_service=Depends(get_azure_openai_service),
) -> ChatResponseDto:
    """Ask a general question to the AI chat assistant."""
    try:
        answer = await azure_openai_service.chat_completion(chat_question.question)

        return ChatResponseDto(answer=answer, timestamp=datetime.utcnow())

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to process chat question: {str(error)}"
        ) from error


@router.post(
    "/ask/stream",
    summary="Ask a general question to the AI chat assistant with streaming response",
    description=("Ask a question and receive a Server-Sent Events stream of the AI response"),
    responses={
        200: {
            "description": "Streaming chat response",
            "content": {
                "text/event-stream": {"example": 'data: {"type":"token","content":"Hello"}\n\n'}
            },
            "headers": {
                "Content-Type": {"description": "text/event-stream"},
                "Cache-Control": {"description": "no-cache"},
                "Connection": {"description": "keep-alive"},
            },
        },
        401: {"description": "Unauthorized - Invalid or missing JWT token"},
        403: {"description": "Forbidden - Insufficient permissions"},
    },
)
async def ask_question_stream(
    chat_question: ChatQuestionDto,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles(["azure-ai-poc-super-admin", "ai-poc-participant"]))],
    azure_openai_service=Depends(get_azure_openai_service),
) -> StreamingResponse:
    """Ask a question with streaming response."""

    async def generate_stream():
        """Generate Server-Sent Events stream."""
        import json

        try:
            # Send start event
            timestamp = datetime.utcnow().isoformat() + "Z"
            start_data = json.dumps({"type": "start", "timestamp": timestamp})
            yield f"data: {start_data}\n\n"

            # Stream the response
            async for chunk in azure_openai_service.chat_completion_streaming(
                chat_question.question
            ):
                if chunk:
                    token_data = json.dumps({"type": "token", "content": chunk})
                    yield f"data: {token_data}\n\n"

            # Send completion event
            timestamp = datetime.utcnow().isoformat() + "Z"
            end_data = json.dumps({"type": "end", "timestamp": timestamp})
            yield f"data: {end_data}\n\n"

        except Exception as error:
            # Send error event
            timestamp = datetime.utcnow().isoformat() + "Z"
            error_data = json.dumps(
                {"type": "error", "message": str(error), "timestamp": timestamp}
            )
            yield f"data: {error_data}\n\n"

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
