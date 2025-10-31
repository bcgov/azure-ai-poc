"""API models for memory and session management."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Request model for creating a new chat session."""

    title: str | None = Field(None, description="Optional title for the session")


class CreateSessionResponse(BaseModel):
    """Response model for creating a new chat session."""

    session_id: str = Field(description="Unique identifier for the session")
    title: str = Field(description="Title of the session")
    created_at: datetime = Field(description="When the session was created")


class ChatRequest(BaseModel):
    """Request model for chat with session support and document context."""

    message: str = Field(description="The user's message")
    session_id: str | None = Field(None, description="Optional session ID for conversation memory")
    context: str | None = Field(None, description="Optional context for the conversation")
    selected_document_ids: list[str] | None = Field(
        None,
        description="Optional list of document IDs to search. If None, searches all user documents",
    )


class SessionMetadata(BaseModel):
    """Session metadata for API responses."""

    session_id: str = Field(description="Unique identifier for the session")
    title: str = Field(description="Title of the session")
    created_at: datetime = Field(description="When the session was created")
    last_updated: datetime = Field(description="When the session was last updated")
    message_count: int = Field(description="Number of messages in the session")
    tags: list[str] = Field(default_factory=list, description="Session tags")


class ListSessionsResponse(BaseModel):
    """Response model for listing user sessions."""

    sessions: list[SessionMetadata] = Field(description="List of user sessions")
    total: int = Field(description="Total number of sessions")


class UpdateSessionRequest(BaseModel):
    """Request model for updating session metadata."""

    title: str | None = Field(None, description="New title for the session")
    tags: list[str] | None = Field(None, description="New tags for the session")
