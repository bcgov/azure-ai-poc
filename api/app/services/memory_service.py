"""
LangChain memory service with Cosmos DB persistence.

This service provides conversation memory management using:
- LangChain's BaseChatMessageHistory for standard interface
- Cosmos DB for persistent storage across sessions
- User-specific conversation isolation
- Message history retrieval and management
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.logger import get_logger
from app.services.cosmos_db_service import CosmosDbService


class ConversationMetadata(BaseModel):
    """Metadata for a conversation session."""

    session_id: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message_count: int = 0
    title: str | None = None
    tags: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    """A chat message with metadata."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    message_type: str  # "human", "ai", "system"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class CosmosDBChatMessageHistory(BaseChatMessageHistory):
    """
    LangChain-compatible chat message history backed by Cosmos DB.

    This class implements the BaseChatMessageHistory interface to provide
    persistent conversation memory using Cosmos DB as the storage backend.
    """

    def __init__(self, session_id: str, user_id: str, cosmos_service: CosmosDbService):
        """
        Initialize the chat message history.

        Args:
            session_id: Unique identifier for the conversation session
            user_id: User identifier for isolation
            cosmos_service: Cosmos DB service instance
        """
        self.session_id = session_id
        self.user_id = user_id
        self.cosmos_service = cosmos_service
        self.logger = get_logger(__name__)

        # Use a separate container for chat history if needed
        # For now, we'll use the same container with a different document type
        self._messages: list[BaseMessage] = []
        self._loaded = False

    @property
    def messages(self) -> list[BaseMessage]:
        """Get all messages in the conversation."""
        if not self._loaded:
            self._load_messages()
        return self._messages

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation history."""
        self._messages.append(message)
        self._save_message(message)

    def add_messages(self, messages: list[BaseMessage]) -> None:
        """Add multiple messages to the conversation history."""
        for message in messages:
            self.add_message(message)

    def clear(self) -> None:
        """Clear all messages from the conversation history."""
        try:
            # Delete all messages for this session from Cosmos DB
            query = "SELECT * FROM c WHERE c.type = 'chat_message' AND c.session_id = @session_id"
            parameters = [{"name": "@session_id", "value": self.session_id}]

            items = list(
                self.cosmos_service.container.query_items(
                    query=query, parameters=parameters, enable_cross_partition_query=True
                )
            )

            for item in items:
                self.cosmos_service.container.delete_item(
                    item=item["id"], partition_key=item["user_id"]
                )

            self._messages.clear()
            self.logger.info(f"Cleared {len(items)} messages for session {self.session_id}")

        except Exception as error:
            self.logger.error(f"Error clearing messages for session {self.session_id}: {error}")
            raise

    def _load_messages(self) -> None:
        """Load messages from Cosmos DB."""
        try:
            query = """
                SELECT * FROM c 
                WHERE c.type = 'chat_message' 
                AND c.session_id = @session_id 
                AND c.user_id = @user_id
                ORDER BY c.timestamp ASC
            """
            parameters = [
                {"name": "@session_id", "value": self.session_id},
                {"name": "@user_id", "value": self.user_id},
            ]

            items = list(
                self.cosmos_service.container.query_items(
                    query=query, parameters=parameters, enable_cross_partition_query=True
                )
            )

            self._messages = []
            for item in items:
                message = self._item_to_message(item)
                if message:
                    self._messages.append(message)

            self._loaded = True
            self.logger.debug(
                f"Loaded {len(self._messages)} messages for session {self.session_id}"
            )

        except Exception as error:
            self.logger.error(f"Error loading messages for session {self.session_id}: {error}")
            self._messages = []
            self._loaded = True

    def _save_message(self, message: BaseMessage) -> None:
        """Save a message to Cosmos DB."""
        try:
            chat_message = ChatMessage(
                session_id=self.session_id,
                message_type=self._get_message_type(message),
                content=message.content,
                metadata=getattr(message, "additional_kwargs", {}),
            )

            item = {
                "id": chat_message.id,
                "type": "chat_message",
                "session_id": self.session_id,
                "user_id": self.user_id,
                "message_type": chat_message.message_type,
                "content": chat_message.content,
                "timestamp": chat_message.timestamp.isoformat(),
                "metadata": chat_message.metadata,
            }

            self.cosmos_service.container.create_item(body=item)
            self.logger.debug(f"Saved message {chat_message.id} to session {self.session_id}")

        except Exception as error:
            self.logger.error(f"Error saving message to session {self.session_id}: {error}")
            # Don't raise here to avoid breaking the conversation flow

    def _item_to_message(self, item: dict[str, Any]) -> BaseMessage | None:
        """Convert a Cosmos DB item to a LangChain message."""
        try:
            message_type = item.get("message_type", "")
            content = item.get("content", "")
            metadata = item.get("metadata", {})

            if message_type == "human":
                return HumanMessage(content=content, additional_kwargs=metadata)
            elif message_type == "ai":
                return AIMessage(content=content, additional_kwargs=metadata)
            elif message_type == "system":
                return SystemMessage(content=content, additional_kwargs=metadata)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                return None

        except Exception as error:
            self.logger.error(f"Error converting item to message: {error}")
            return None

    def _get_message_type(self, message: BaseMessage) -> str:
        """Get the string representation of the message type."""
        if isinstance(message, HumanMessage):
            return "human"
        elif isinstance(message, AIMessage):
            return "ai"
        elif isinstance(message, SystemMessage):
            return "system"
        else:
            return "unknown"


class MemoryService:
    """
    Service for managing conversation memory across sessions.

    This service provides higher-level memory management operations
    including session creation, metadata management, and cleanup.
    """

    def __init__(self, cosmos_service: CosmosDbService):
        """
        Initialize the memory service.

        Args:
            cosmos_service: Cosmos DB service instance
        """
        self.cosmos_service = cosmos_service
        self.logger = get_logger(__name__)

    def get_chat_history(self, session_id: str, user_id: str) -> CosmosDBChatMessageHistory:
        """
        Get chat history for a session.

        Args:
            session_id: Session identifier
            user_id: User identifier

        Returns:
            Chat message history instance
        """
        return CosmosDBChatMessageHistory(
            session_id=session_id, user_id=user_id, cosmos_service=self.cosmos_service
        )

    async def create_session(self, user_id: str, title: str | None = None) -> str:
        """
        Create a new conversation session.

        Args:
            user_id: User identifier
            title: Optional session title

        Returns:
            New session ID
        """
        session_id = str(uuid.uuid4())

        metadata = ConversationMetadata(
            session_id=session_id,
            user_id=user_id,
            title=title or f"Conversation {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}",
        )

        item = {
            "id": f"session_{session_id}",
            "type": "conversation_metadata",
            "session_id": session_id,
            "user_id": user_id,
            "created_at": metadata.created_at.isoformat(),
            "last_updated": metadata.last_updated.isoformat(),
            "message_count": metadata.message_count,
            "title": metadata.title,
            "tags": metadata.tags,
        }

        try:
            await self.cosmos_service.create_item(item, user_id)
            self.logger.info(f"Created new session {session_id} for user {user_id}")
            return session_id

        except Exception as error:
            self.logger.error(f"Error creating session for user {user_id}: {error}")
            raise

    async def get_user_sessions(self, user_id: str, limit: int = 10) -> list[ConversationMetadata]:
        """
        Get recent conversation sessions for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return

        Returns:
            List of conversation metadata
        """
        try:
            query = """
                SELECT * FROM c 
                WHERE c.type = 'conversation_metadata' 
                AND c.user_id = @user_id 
                ORDER BY c.last_updated DESC
                OFFSET 0 LIMIT @limit
            """
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@limit", "value": limit},
            ]

            items = list(
                self.cosmos_service.container.query_items(
                    query=query, parameters=parameters, enable_cross_partition_query=True
                )
            )

            sessions = []
            for item in items:
                sessions.append(
                    ConversationMetadata(
                        session_id=item["session_id"],
                        user_id=item["user_id"],
                        created_at=datetime.fromisoformat(item["created_at"]),
                        last_updated=datetime.fromisoformat(item["last_updated"]),
                        message_count=item.get("message_count", 0),
                        title=item.get("title"),
                        tags=item.get("tags", []),
                    )
                )

            return sessions

        except Exception as error:
            self.logger.error(f"Error getting sessions for user {user_id}: {error}")
            return []

    async def update_session_metadata(self, session_id: str, user_id: str, **kwargs) -> None:
        """
        Update session metadata.

        Args:
            session_id: Session identifier
            user_id: User identifier
            **kwargs: Fields to update
        """
        try:
            item_id = f"session_{session_id}"
            existing_item = await self.cosmos_service.get_item(item_id, user_id)

            if not existing_item:
                self.logger.warning(f"Session {session_id} not found for user {user_id}")
                return

            # Update allowed fields
            allowed_fields = ["title", "tags", "message_count"]
            for field, value in kwargs.items():
                if field in allowed_fields:
                    existing_item[field] = value

            existing_item["last_updated"] = datetime.now(UTC).isoformat()

            await self.cosmos_service.update_item(item_id, existing_item, user_id)
            self.logger.debug(f"Updated session {session_id} metadata")

        except Exception as error:
            self.logger.error(f"Error updating session {session_id} metadata: {error}")

    async def delete_session(self, session_id: str, user_id: str) -> None:
        """
        Delete a conversation session and all its messages.

        Args:
            session_id: Session identifier
            user_id: User identifier
        """
        try:
            # Delete session metadata
            await self.cosmos_service.delete_item(f"session_{session_id}", user_id)

            # Clear all messages (this will delete them from Cosmos DB)
            chat_history = self.get_chat_history(session_id, user_id)
            chat_history.clear()

            self.logger.info(f"Deleted session {session_id} for user {user_id}")

        except Exception as error:
            self.logger.error(f"Error deleting session {session_id}: {error}")
            raise
