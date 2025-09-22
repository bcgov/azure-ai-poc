"""
LangGraph Chat router for unified AI conversation endpoints.

This router provides LangGraph-based AI chat functionality including:
- Unified AI responses through LangGraph agent workflow
- Document-aware question answering with citations
- Conversation memory and session management
- Role-based access control
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import RequireAuth, require_roles
from app.auth.models import KeycloakUser
from app.routers.models.memory_models import (
    ChatRequest,
    CreateSessionRequest,
    CreateSessionResponse,
    ListSessionsResponse,
    SessionMetadata,
    UpdateSessionRequest,
)
from app.services.langchain_service import get_langchain_ai_service
from app.services.langgraph_agent_service import get_langgraph_agent_service


class ChatResponseDto(BaseModel):
    """Chat response model."""

    answer: str = Field(..., description="AI assistant's response")
    timestamp: datetime = Field(..., description="Response timestamp")


router = APIRouter(tags=["chat"])


# Session Management Endpoints


@router.post(
    "/sessions",
    summary="Create a new chat session",
    description="Create a new conversation session to maintain chat history",
    response_model=CreateSessionResponse,
)
async def create_session(
    request: CreateSessionRequest,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant"))],
    langchain_service=Depends(get_langchain_ai_service),
) -> CreateSessionResponse:
    """Create a new chat session."""
    try:
        await langchain_service.memory_service.create_session(
            user_id=current_user.sub,
            title=request.title,
        )

        # Get the created session metadata
        sessions = await langchain_service.memory_service.get_user_sessions(
            user_id=current_user.sub,
            limit=1,
        )

        if not sessions:
            raise HTTPException(status_code=500, detail="Failed to retrieve created session")

        session = sessions[0]
        return CreateSessionResponse(
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at,
        )

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(error)}"
        ) from error


@router.get(
    "/sessions",
    summary="List user chat sessions",
    description="Get a list of the user's chat sessions",
    response_model=ListSessionsResponse,
)
async def list_sessions(
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant"))],
    limit: int = 10,
    langchain_service=Depends(get_langchain_ai_service),
) -> ListSessionsResponse:
    """List user's chat sessions."""
    try:
        sessions = await langchain_service.memory_service.get_user_sessions(
            user_id=current_user.sub,
            limit=limit,
        )

        session_metadata = [
            SessionMetadata(
                session_id=session.session_id,
                title=session.title,
                created_at=session.created_at,
                last_updated=session.last_updated,
                message_count=session.message_count,
                tags=session.tags,
            )
            for session in sessions
        ]

        return ListSessionsResponse(
            sessions=session_metadata,
            total=len(session_metadata),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to list sessions: {str(error)}"
        ) from error


@router.patch(
    "/sessions/{session_id}",
    summary="Update session metadata",
    description="Update title and tags for a chat session",
)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant"))],
    langchain_service=Depends(get_langchain_ai_service),
):
    """Update session metadata."""
    try:
        update_data = {}
        if request.title is not None:
            update_data["title"] = request.title
        if request.tags is not None:
            update_data["tags"] = request.tags

        await langchain_service.memory_service.update_session_metadata(
            session_id=session_id,
            user_id=current_user.sub,
            **update_data,
        )

        return {"message": "Session updated successfully"}

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to update session: {str(error)}"
        ) from error


@router.delete(
    "/sessions/{session_id}",
    summary="Delete a chat session",
    description="Delete a chat session and all its messages",
)
async def delete_session(
    session_id: str,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant"))],
    langchain_service=Depends(get_langchain_ai_service),
):
    """Delete a chat session."""
    try:
        await langchain_service.memory_service.delete_session(
            session_id=session_id,
            user_id=current_user.sub,
        )

        return {"message": "Session deleted successfully"}

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(error)}"
        ) from error


# Unified LangGraph Chat Endpoint


@router.post(
    "/ask",
    summary="Ask a question using the unified LangGraph AI agent",
    description="Ask a question to the LangGraph AI agent with document-aware responses, "
    "multi-step reasoning, and automatic source citations. This is the unified chat endpoint "
    "that provides intelligent responses for all queries.",
    response_model=ChatResponseDto,
)
async def ask_question(
    chat_request: ChatRequest,
    current_user: Annotated[KeycloakUser, RequireAuth],
    _: Annotated[None, Depends(require_roles("azure-ai-poc-super-admin", "ai-poc-participant"))],
    agent_service=Depends(get_langgraph_agent_service),
) -> ChatResponseDto:
    """Ask a question using the unified LangGraph AI agent with document search and citations."""
    try:
        answer = await agent_service.process_message(
            message=chat_request.message,
            user_id=current_user.sub,
            session_id=chat_request.session_id,
            context=chat_request.context,
            selected_document_ids=chat_request.selected_document_ids,
        )

        return ChatResponseDto(answer=answer, timestamp=datetime.utcnow())

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to process chat request: {str(error)}"
        ) from error
