"""Chat router - API endpoints for chat functionality."""

from textwrap import shorten
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user_from_request
from app.auth.models import AuthenticatedUser
from app.logger import get_logger
from app.services.azure_search_service import (
    AzureSearchService,
    get_azure_search_service,
)
from app.services.chat_agent import ChatAgentService, get_chat_agent_service
from app.services.cosmos_db_service import CosmosDbService, get_cosmos_db_service
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.utils import sort_source_dicts_by_confidence

logger = get_logger(__name__)

router = APIRouter()

# Prompt/cost guards
MAX_CONTEXT_CHARS_PER_CHUNK = 600


class ChatMessage(BaseModel):
    """A single message in the conversation."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    session_id: str | None = Field(
        default=None, description="Session ID for conversation continuity"
    )
    history: list[ChatMessage] | None = Field(default=None, description="Conversation history")
    document_id: str | None = Field(
        default=None, description="Optional document ID for RAG context"
    )
    model: str | None = Field(
        default=None,
        description="Model to use: 'gpt-4o-mini' (default) or 'gpt-41-nano'",
    )


class SourceInfoResponse(BaseModel):
    """Information about a source used in the response."""

    source_type: str = Field(
        ..., description="Type of source: 'llm_knowledge', 'document', 'web', 'api'"
    )
    description: str = Field(..., description="Description of the source")
    confidence: str = Field(default="high", description="Confidence level: 'high', 'medium', 'low'")
    url: str | None = Field(default=None, description="URL of the source if available")


class ChatResponse(BaseModel):
    """Response from chat endpoint - always includes source attribution."""

    response: str = Field(..., description="Assistant's response")
    session_id: str = Field(..., description="Session ID for the conversation")
    sources: list[SourceInfoResponse] = Field(
        ...,
        min_length=1,
        description="Sources used to generate the response (REQUIRED for traceability)",
    )
    has_sufficient_info: bool = Field(
        default=True, description="Whether the AI had sufficient information to answer"
    )


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: Annotated[ChatAgentService, Depends(get_chat_agent_service)],
    cosmos: Annotated[CosmosDbService, Depends(get_cosmos_db_service)],
    search: Annotated[AzureSearchService, Depends(get_azure_search_service)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user_from_request)],
) -> ChatResponse:
    """
    Send a message to the chat agent and receive a response with source attribution.

    - **message**: The user's message to the agent
    - **session_id**: Optional session ID for conversation continuity
    - **history**: Optional list of previous messages in the conversation
    - **document_id**: Optional document ID to use for RAG context

    Response always includes:
    - **sources**: List of sources used to generate the response
    - **has_sufficient_info**: Whether the AI had enough information to answer accurately

    Chat history is persisted to Cosmos DB for session continuity.
    """
    session_id = request.session_id or str(uuid4())
    user_id = current_user.sub

    logger.info(
        "chat_request_received",
        user_id=user_id,
        session_id=session_id,
        message_preview=request.message[:100],
        has_history=request.history is not None,
        document_id=request.document_id,
    )

    # If no history provided but session_id exists, try to load from Cosmos DB
    history = None
    if request.history:
        history = [{"role": msg.role, "content": msg.content} for msg in request.history]
    elif request.session_id:
        # Load history from Cosmos DB
        stored_messages = await cosmos.get_chat_history(session_id, user_id)
        if stored_messages:
            history = [{"role": msg.role, "content": msg.content} for msg in stored_messages]

    # If document_id is provided, search for relevant context
    document_context = None
    document_sources = []
    if request.document_id:
        try:
            # Get embedding for the user's message
            embedding = await embedding_service.generate_embedding(request.message)
            if embedding:
                from app.services.azure_search_service import VectorSearchOptions

                search_options = VectorSearchOptions(
                    user_id=user_id,
                    document_id=request.document_id,
                    top_k=5,  # Fewer chunks to reduce prompt size/cost
                    min_similarity=0.4,  # Slightly stricter to avoid weak matches
                )
                search_results = await search.vector_search(embedding, search_options)

                if search_results:
                    # Build document context from search results
                    context_parts = []
                    for result in search_results:
                        content_snippet = shorten(
                            result["content"], width=MAX_CONTEXT_CHARS_PER_CHUNK, placeholder=" …"
                        )
                        context_parts.append(
                            f"[Source: {result['metadata'].get('title', 'Document')}]\n"
                            f"{content_snippet}"
                        )
                        # Azure Search returns cosine similarity scores
                        # Scores above 0.5 are typically good matches
                        similarity = result.get("similarity", 0)
                        if similarity > 0.6:
                            confidence = "high"
                        elif similarity > 0.4:
                            confidence = "medium"
                        else:
                            confidence = "low"

                        # Use page number if available, otherwise fall back to chunk index
                        page_num = result.get("page_number", 0)
                        if page_num and page_num > 0:
                            location_info = f"(page {page_num})"
                        else:
                            location_info = f"(chunk {result.get('chunk_index', 0) + 1})"

                        document_sources.append(
                            {
                                "source_type": "document",
                                "description": (
                                    f"From document: {result['metadata'].get('title', 'Unknown')} "
                                    f"{location_info}"
                                ),
                                "confidence": confidence,
                                "url": None,
                            }
                        )

                    document_context = "\n\n---\n\n".join(context_parts)
        except Exception as e:
            # Log but don't fail the request if document search fails
            import logging

            logging.error(f"Document search failed: {e}")

    try:
        # Save user message to Cosmos DB
        await cosmos.save_message(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=request.message,
        )

        result = await agent.chat(
            message=request.message,
            history=history,
            session_id=session_id,
            user_id=user_id,
            document_context=document_context,
            model=request.model,
        )

        # Convert sources to response format
        # When document context is provided, use document sources (from RAG search)
        # Otherwise, use agent sources (from LLM knowledge)
        sources = []

        if document_sources:
            # Use document sources from RAG search (more accurate citations)
            # Sort by confidence (highest first)
            sorted_doc_sources = sort_source_dicts_by_confidence(document_sources)
            for doc_src in sorted_doc_sources:
                sources.append(
                    SourceInfoResponse(
                        source_type=doc_src["source_type"],
                        description=doc_src["description"],
                        confidence=doc_src["confidence"],
                        url=doc_src.get("url"),
                    )
                )
        else:
            # No document context - use agent's LLM knowledge sources
            # Sources are already sorted in the chat_agent service
            for src in result.sources:
                sources.append(
                    SourceInfoResponse(
                        source_type=src.source_type,
                        description=src.description,
                        confidence=src.confidence,
                        url=src.url,
                    )
                )

        if not sources:
            raise HTTPException(
                status_code=500,
                detail="Citations are required but none were returned by the chat agent",
            )

        # Save assistant response to Cosmos DB
        all_sources = (
            document_sources
            if document_sources
            else [
                {
                    "source_type": src.source_type,
                    "description": src.description,
                    "confidence": src.confidence,
                    "url": src.url,
                }
                for src in result.sources
            ]
        )

        await cosmos.save_message(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=result.response,
            sources=all_sources,
        )

        logger.info(
            "chat_request_completed",
            user_id=user_id,
            session_id=session_id,
            source_count=len(sources),
            has_sufficient_info=result.has_sufficient_info,
        )

        return ChatResponse(
            response=result.response,
            session_id=session_id,
            sources=sources,
            has_sufficient_info=result.has_sufficient_info,
        )

    except Exception as e:
        logger.error(
            "chat_request_failed",
            user_id=user_id,
            session_id=session_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}") from e


class SessionResponse(BaseModel):
    """Response for session creation."""

    session_id: str = Field(..., description="The created session ID")
    title: str = Field(..., description="Session title")


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[dict] = Field(..., description="List of user sessions")


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    cosmos: Annotated[CosmosDbService, Depends(get_cosmos_db_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user_from_request)],
    title: str | None = None,
) -> SessionResponse:
    """Create a new chat session."""
    user_id = current_user.sub
    session = await cosmos.create_session(user_id, title)
    return SessionResponse(session_id=session.session_id, title=session.title)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    cosmos: Annotated[CosmosDbService, Depends(get_cosmos_db_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user_from_request)],
    limit: int = 20,
) -> SessionListResponse:
    """List user's chat sessions."""
    user_id = current_user.sub
    sessions = await cosmos.get_user_sessions(user_id, limit)
    return SessionListResponse(
        sessions=[
            {
                "session_id": s.session_id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "last_updated": s.last_updated.isoformat(),
                "message_count": s.message_count,
            }
            for s in sessions
        ]
    )


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    cosmos: Annotated[CosmosDbService, Depends(get_cosmos_db_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user_from_request)],
    limit: int = 50,
) -> dict:
    """Get chat history for a session."""
    user_id = current_user.sub
    messages = await cosmos.get_chat_history(session_id, user_id, limit)
    return {
        "session_id": session_id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "sources": m.sources,
            }
            for m in messages
        ],
    }


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    cosmos: Annotated[CosmosDbService, Depends(get_cosmos_db_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user_from_request)],
) -> dict:
    """Delete a chat session and all its messages."""
    user_id = current_user.sub
    success = await cosmos.delete_session(session_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


@router.get("/health")
async def chat_health() -> dict[str, str]:
    """Health check for the chat service."""
    return {"status": "ok", "service": "chat"}
