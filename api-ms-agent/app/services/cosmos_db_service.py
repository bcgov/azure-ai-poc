"""
Cosmos DB service for chat history, metadata, and workflow persistence.

This service provides:
- Chat session management
- Chat history storage and retrieval
- Document metadata storage (not embeddings)
- Workflow state persistence for Microsoft Agent Framework
- Managed identity authentication with key fallback
"""

import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from azure.cosmos import ContainerProxy, CosmosClient, DatabaseProxy, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChatMessage:
    """A chat message stored in Cosmos DB."""

    id: str
    session_id: str
    user_id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConversationSession:
    """A conversation session with metadata."""

    id: str
    session_id: str
    user_id: str
    title: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    message_count: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class DocumentMetadata:
    """Document metadata stored in Cosmos DB (embeddings stored in Azure AI Search)."""

    id: str
    document_id: str
    user_id: str
    title: str
    filename: str | None = None
    content_type: str | None = None
    chunk_count: int = 0
    pages: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """Workflow state for Microsoft Agent Framework distributed workflows."""

    id: str
    workflow_id: str
    user_id: str
    workflow_type: str
    status: str  # "pending", "running", "completed", "failed"
    current_step: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class CosmosDbService:
    """Service for Cosmos DB operations for chat, metadata, and workflow persistence."""

    # Container names
    CHAT_CONTAINER = "chat_history"
    DOCUMENTS_CONTAINER = "documents"
    WORKFLOWS_CONTAINER = "workflows"

    def __init__(self) -> None:
        """Initialize the Cosmos DB service."""
        self.client: CosmosClient | None = None
        self.database: DatabaseProxy | None = None
        self.chat_container: ContainerProxy | None = None
        self.documents_container: ContainerProxy | None = None
        self.workflows_container: ContainerProxy | None = None
        self._initialized = False

    def _initialize_client(self) -> None:
        """Initialize the Cosmos DB client with managed identity or key authentication."""
        if self._initialized:
            return

        endpoint = settings.cosmos_db_endpoint
        database_name = settings.cosmos_db_database_name

        if not endpoint or not database_name:
            logger.warning(
                "cosmos_db_config_missing",
                message="Cosmos DB not configured - persistence will not be available",
            )
            return

        try:
            connection_timeout = 30  # 30 second timeout

            # Use key authentication for local, managed identity for cloud
            if settings.environment == "local" and settings.cosmos_db_key:
                self.client = CosmosClient(
                    url=endpoint,
                    credential=settings.cosmos_db_key,
                    enable_endpoint_discovery=False,
                    connection_timeout=connection_timeout,
                )
                logger.info("cosmos_db_init", auth_method="key")
            else:
                credential = DefaultAzureCredential()
                self.client = CosmosClient(
                    url=endpoint,
                    credential=credential,
                    enable_endpoint_discovery=True,
                    connection_timeout=connection_timeout,
                )
                logger.info("cosmos_db_init", auth_method="managed_identity")

            self.database = self.client.get_database_client(database_name)

            # Ensure containers exist (create if they don't)
            self._ensure_containers_exist()

            # Get container clients
            self.chat_container = self.database.get_container_client(self.CHAT_CONTAINER)
            self.documents_container = self.database.get_container_client(self.DOCUMENTS_CONTAINER)
            self.workflows_container = self.database.get_container_client(self.WORKFLOWS_CONTAINER)

            self._initialized = True
            logger.info("cosmos_db_initialized", database=database_name)

        except Exception as error:
            logger.error("cosmos_db_init_failed", error=str(error))
            # Don't raise - allow service to work without persistence

    def _ensure_containers_exist(self) -> None:
        """Ensure the required containers exist in the database."""
        if not self.database:
            return

        # Create chat_history container if it doesn't exist
        try:
            self.database.create_container_if_not_exists(
                id=self.CHAT_CONTAINER,
                partition_key=PartitionKey(path="/user_id"),
                offer_throughput=400,
            )
            logger.info("container_ensured", container=self.CHAT_CONTAINER)
        except CosmosHttpResponseError as e:
            if e.status_code != 409:  # 409 = already exists
                logger.warning(
                    "container_create_warning",
                    container=self.CHAT_CONTAINER,
                    error=str(e),
                )

        # Create documents container for metadata only (embeddings in Azure AI Search)
        try:
            self.database.create_container_if_not_exists(
                id=self.DOCUMENTS_CONTAINER,
                partition_key=PartitionKey(path="/user_id"),
                offer_throughput=400,
            )
            logger.info("container_ensured", container=self.DOCUMENTS_CONTAINER)
        except CosmosHttpResponseError as e:
            if e.status_code != 409:  # 409 = already exists
                logger.warning(
                    "container_create_warning",
                    container=self.DOCUMENTS_CONTAINER,
                    error=str(e),
                )

        # Create workflows container for agent framework state persistence
        try:
            self.database.create_container_if_not_exists(
                id=self.WORKFLOWS_CONTAINER,
                partition_key=PartitionKey(path="/user_id"),
                offer_throughput=400,
            )
            logger.info("container_ensured", container=self.WORKFLOWS_CONTAINER)
        except CosmosHttpResponseError as e:
            if e.status_code != 409:  # 409 = already exists
                logger.warning(
                    "container_create_warning",
                    container=self.WORKFLOWS_CONTAINER,
                    error=str(e),
                )

    def _ensure_initialized(self) -> bool:
        """Ensure the service is initialized. Returns True if ready."""
        if not self._initialized:
            self._initialize_client()
        return self._initialized

    # ============= Chat History Operations =============

    async def create_session(self, user_id: str, title: str | None = None) -> ConversationSession:
        """
        Create a new conversation session.

        Args:
            user_id: The user identifier
            title: Optional session title

        Returns:
            The created conversation session
        """
        session_id = f"session_{uuid.uuid4()}"

        if not self._ensure_initialized():
            return ConversationSession(
                id=f"sess_{session_id}",
                session_id=session_id,
                user_id=user_id,
                title=title or "New conversation",
            )

        session = ConversationSession(
            id=f"sess_{session_id}",
            session_id=session_id,
            user_id=user_id,
            title=title or "New conversation",
        )

        item = {
            "id": session.id,
            "type": "session",
            "session_id": session_id,
            "user_id": user_id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
            "last_updated": session.last_updated.isoformat(),
            "message_count": 0,
            "tags": [],
        }

        try:
            self.chat_container.create_item(body=item)
            logger.info("session_created", session_id=session_id, user_id=user_id)
            return session
        except Exception as error:
            logger.error("session_create_failed", error=str(error), user_id=user_id)
            return session  # Return session even on failure

    async def save_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessage:
        """
        Save a chat message to Cosmos DB.

        Args:
            session_id: The session identifier
            user_id: The user identifier
            role: Message role (user, assistant, system)
            content: Message content
            sources: Optional source attribution
            metadata: Optional additional metadata

        Returns:
            The saved chat message
        """
        message_id = str(uuid.uuid4())
        message = ChatMessage(
            id=message_id,
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            sources=sources or [],
            metadata=metadata or {},
        )

        if not self._ensure_initialized():
            return message

        item = {
            "id": message_id,
            "type": "message",
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": message.timestamp.isoformat(),
            "sources": sources or [],
            "metadata": metadata or {},
        }

        try:
            self.chat_container.create_item(body=item)
            logger.debug("message_saved", message_id=message_id, session_id=session_id)

            # Update session metadata - pass content for title if user message
            first_msg = content if role == "user" else None
            await self._update_session_message_count(session_id, user_id, first_msg)
            return message
        except Exception as error:
            logger.error(
                "message_save_failed",
                error=str(error),
                session_id=session_id,
            )
            return message

    async def get_chat_history(
        self,
        session_id: str,
        user_id: str,
        limit: int = 50,
    ) -> list[ChatMessage]:
        """
        Get chat history for a session.

        Args:
            session_id: The session identifier
            user_id: The user identifier
            limit: Maximum messages to return

        Returns:
            List of chat messages ordered by timestamp
        """
        if not self._ensure_initialized():
            return []

        try:
            query = """
                SELECT * FROM c
                WHERE c.type = 'message'
                AND c.session_id = @session_id
                AND c.user_id = @user_id
                ORDER BY c.timestamp ASC
                OFFSET 0 LIMIT @limit
            """
            parameters = [
                {"name": "@session_id", "value": session_id},
                {"name": "@user_id", "value": user_id},
                {"name": "@limit", "value": limit},
            ]

            items = list(
                self.chat_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )

            messages = []
            for item in items:
                messages.append(
                    ChatMessage(
                        id=item["id"],
                        session_id=item["session_id"],
                        user_id=item["user_id"],
                        role=item["role"],
                        content=item["content"],
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        sources=item.get("sources", []),
                        metadata=item.get("metadata", {}),
                    )
                )

            logger.debug(
                "chat_history_loaded",
                session_id=session_id,
                message_count=len(messages),
            )
            return messages

        except Exception as error:
            logger.error(
                "chat_history_load_failed",
                error=str(error),
                session_id=session_id,
            )
            return []

    async def get_user_sessions(self, user_id: str, limit: int = 20) -> list[ConversationSession]:
        """
        Get recent conversation sessions for a user.

        Args:
            user_id: The user identifier
            limit: Maximum sessions to return

        Returns:
            List of conversation sessions
        """
        if not self._ensure_initialized():
            return []

        try:
            query = """
                SELECT * FROM c
                WHERE c.type = 'session'
                AND c.user_id = @user_id
                ORDER BY c.last_updated DESC
                OFFSET 0 LIMIT @limit
            """
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@limit", "value": limit},
            ]

            items = list(
                self.chat_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )

            sessions = []
            for item in items:
                sessions.append(
                    ConversationSession(
                        id=item["id"],
                        session_id=item["session_id"],
                        user_id=item["user_id"],
                        title=item.get("title", "Untitled"),
                        created_at=datetime.fromisoformat(item["created_at"]),
                        last_updated=datetime.fromisoformat(item["last_updated"]),
                        message_count=item.get("message_count", 0),
                        tags=item.get("tags", []),
                    )
                )

            return sessions

        except Exception as error:
            logger.error(
                "get_sessions_failed",
                error=str(error),
                user_id=user_id,
            )
            return []

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """
        Delete a conversation session and all its messages.

        Args:
            session_id: The session identifier
            user_id: The user identifier

        Returns:
            True if deletion was successful
        """
        if not self._ensure_initialized():
            return False

        try:
            # Delete all messages in the session - try both with and without prefix
            session_ids_to_try = [session_id]
            if not session_id.startswith("session_"):
                session_ids_to_try.append(f"session_{session_id}")

            for sid in session_ids_to_try:
                query = """
                    SELECT c.id FROM c
                    WHERE c.type = 'message'
                    AND c.session_id = @session_id
                """
                parameters = [{"name": "@session_id", "value": sid}]

                items = list(
                    self.chat_container.query_items(
                        query=query,
                        parameters=parameters,
                        enable_cross_partition_query=True,
                    )
                )

                for item in items:
                    try:
                        self.chat_container.delete_item(item=item["id"], partition_key=user_id)
                    except CosmosResourceNotFoundError:
                        pass

            # Delete the session metadata - try multiple ID formats
            doc_ids_to_try = [
                f"sess_{session_id}",
                f"session_{session_id}",
                session_id,
            ]

            deleted = False
            for doc_id in doc_ids_to_try:
                try:
                    self.chat_container.delete_item(
                        item=doc_id,
                        partition_key=user_id,
                    )
                    deleted = True
                    break
                except CosmosResourceNotFoundError:
                    continue

            if deleted:
                logger.info("session_deleted", session_id=session_id, user_id=user_id)
                return True
            else:
                logger.warning("session_not_found", session_id=session_id)
                return False

        except Exception as error:
            logger.error(
                "session_delete_failed",
                error=str(error),
                session_id=session_id,
            )
            return False

    async def _update_session_message_count(
        self, session_id: str, user_id: str, first_message: str | None = None
    ) -> None:
        """Update the message count and last_updated for a session, creating if needed."""
        # Use session_id as-is for item_id (consistent with how messages store it)
        item_id = f"sess_{session_id}"  # Unique document ID

        try:
            existing = self.chat_container.read_item(
                item=item_id,
                partition_key=user_id,
            )
            existing["message_count"] = existing.get("message_count", 0) + 1
            existing["last_updated"] = datetime.now(UTC).isoformat()
            self.chat_container.replace_item(item=item_id, body=existing)
        except CosmosResourceNotFoundError:
            # Session doesn't exist yet - create it
            now = datetime.now(UTC)
            # Generate a better title from first message
            title = self._generate_session_title(first_message) if first_message else None
            if not title:
                title = "New conversation"

            new_session = {
                "id": item_id,
                "type": "session",
                "session_id": session_id,  # Keep original session_id
                "user_id": user_id,
                "title": title,
                "created_at": now.isoformat(),
                "last_updated": now.isoformat(),
                "message_count": 1,
                "tags": [],
            }
            try:
                self.chat_container.create_item(body=new_session)
                logger.info("session_auto_created", session_id=session_id, user_id=user_id)
            except Exception as create_error:
                logger.debug(
                    "session_auto_create_failed",
                    error=str(create_error),
                    session_id=session_id,
                )
        except Exception as error:
            logger.debug("session_update_failed", error=str(error), session_id=session_id)

    def _generate_session_title(self, message: str) -> str:
        """Generate a short title from the first message."""
        if not message:
            return ""
        # Take first 50 chars, cut at word boundary
        title = message.strip()[:50]
        if len(message) > 50:
            # Cut at last space to avoid cutting words
            last_space = title.rfind(" ")
            if last_space > 20:
                title = title[:last_space]
            title += "..."
        return title

    # ============= Document Metadata Operations =============

    async def save_document_metadata(
        self,
        document_id: str,
        user_id: str,
        title: str,
        filename: str | None = None,
        content_type: str | None = None,
        chunk_count: int = 0,
        pages: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentMetadata:
        """
        Save document metadata to Cosmos DB.

        Note: Embeddings are stored in Azure AI Search, not here.

        Args:
            document_id: The document identifier
            user_id: The user identifier
            title: Document title
            filename: Original filename
            content_type: MIME type
            chunk_count: Number of chunks in Azure AI Search
            pages: Number of pages (for PDFs)
            metadata: Additional metadata

        Returns:
            The saved document metadata
        """
        doc_meta = DocumentMetadata(
            id=f"doc_{document_id}",
            document_id=document_id,
            user_id=user_id,
            title=title,
            filename=filename,
            content_type=content_type,
            chunk_count=chunk_count,
            pages=pages,
            metadata=metadata or {},
        )

        if not self._ensure_initialized():
            return doc_meta

        item = {
            "id": doc_meta.id,
            "type": "document",
            "document_id": document_id,
            "user_id": user_id,
            "title": title,
            "filename": filename,
            "content_type": content_type,
            "chunk_count": chunk_count,
            "pages": pages,
            "created_at": doc_meta.created_at.isoformat(),
            "metadata": metadata or {},
        }

        try:
            self.documents_container.upsert_item(body=item)
            logger.info("document_metadata_saved", document_id=document_id, user_id=user_id)
            return doc_meta
        except Exception as error:
            logger.error("document_metadata_save_failed", error=str(error), document_id=document_id)
            return doc_meta

    async def list_user_documents(self, user_id: str, limit: int = 50) -> list[dict]:
        """
        List document metadata for a user.

        Args:
            user_id: The user identifier
            limit: Maximum number of documents to return

        Returns:
            List of document metadata
        """
        if not self._ensure_initialized():
            return []

        try:
            query = """
                SELECT * FROM c
                WHERE c.type = 'document' AND c.user_id = @user_id
                ORDER BY c.created_at DESC
                OFFSET 0 LIMIT @limit
            """
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@limit", "value": limit},
            ]

            items = list(
                self.documents_container.query_items(
                    query=query,
                    parameters=parameters,
                    partition_key=user_id,
                )
            )

            result = [
                {
                    "id": item["document_id"],
                    "document_id": item["document_id"],
                    "title": item.get("title") or f"Document {item['document_id'][:8]}...",
                    "filename": item.get("filename"),
                    "created_at": item.get("created_at"),
                    "chunk_count": item.get("chunk_count", 0),
                }
                for item in items
            ]

            logger.info("documents_listed", user_id=user_id, count=len(result))
            return result

        except CosmosResourceNotFoundError:
            logger.info("documents_list_empty", user_id=user_id, reason="partition_not_found")
            return []
        except Exception as error:
            logger.error("documents_list_failed", error=str(error), user_id=user_id)
            return []

    async def delete_document_metadata(self, document_id: str, user_id: str) -> bool:
        """
        Delete document metadata from Cosmos DB.

        Note: Also delete chunks from Azure AI Search separately.

        Args:
            document_id: The document identifier
            user_id: The user identifier

        Returns:
            True if deleted successfully
        """
        if not self._ensure_initialized():
            return False

        try:
            self.documents_container.delete_item(
                item=f"doc_{document_id}",
                partition_key=user_id,
            )
            logger.info("document_metadata_deleted", document_id=document_id)
            return True
        except CosmosResourceNotFoundError:
            logger.warning("document_metadata_not_found", document_id=document_id)
            return False
        except Exception as error:
            logger.error(
                "document_metadata_delete_failed", error=str(error), document_id=document_id
            )
            return False

    # ============= Workflow Persistence Operations (Microsoft Agent Framework) =============

    async def save_workflow_state(
        self,
        workflow_id: str,
        user_id: str,
        workflow_type: str,
        status: str,
        current_step: str | None = None,
        context: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> WorkflowState:
        """
        Save or update workflow state for distributed workflow persistence.

        Args:
            workflow_id: The workflow identifier
            user_id: The user identifier
            workflow_type: Type of workflow (e.g., "research", "document_qa")
            status: Workflow status (pending, running, completed, failed)
            current_step: Current step in the workflow
            context: Workflow context/state data
            result: Workflow result (when completed)
            error: Error message (when failed)

        Returns:
            The saved workflow state
        """
        now = datetime.now(UTC)
        workflow_state = WorkflowState(
            id=f"wf_{workflow_id}",
            workflow_id=workflow_id,
            user_id=user_id,
            workflow_type=workflow_type,
            status=status,
            current_step=current_step,
            context=context or {},
            result=result,
            error=error,
            updated_at=now,
        )

        if not self._ensure_initialized():
            return workflow_state

        item = {
            "id": workflow_state.id,
            "type": "workflow",
            "workflow_id": workflow_id,
            "user_id": user_id,
            "workflow_type": workflow_type,
            "status": status,
            "current_step": current_step,
            "context": context or {},
            "result": result,
            "error": error,
            "created_at": workflow_state.created_at.isoformat(),
            "updated_at": now.isoformat(),
        }

        try:
            self.workflows_container.upsert_item(body=item)
            logger.info(
                "workflow_state_saved",
                workflow_id=workflow_id,
                status=status,
                current_step=current_step,
            )
            return workflow_state
        except Exception as err:
            logger.error("workflow_state_save_failed", error=str(err), workflow_id=workflow_id)
            return workflow_state

    async def get_workflow_state(self, workflow_id: str, user_id: str) -> WorkflowState | None:
        """
        Get workflow state by ID.

        Args:
            workflow_id: The workflow identifier
            user_id: The user identifier

        Returns:
            The workflow state or None if not found
        """
        if not self._ensure_initialized():
            return None

        try:
            item = self.workflows_container.read_item(
                item=f"wf_{workflow_id}",
                partition_key=user_id,
            )

            return WorkflowState(
                id=item["id"],
                workflow_id=item["workflow_id"],
                user_id=item["user_id"],
                workflow_type=item["workflow_type"],
                status=item["status"],
                current_step=item.get("current_step"),
                context=item.get("context", {}),
                result=item.get("result"),
                error=item.get("error"),
                created_at=datetime.fromisoformat(item["created_at"]),
                updated_at=datetime.fromisoformat(item["updated_at"]),
            )
        except CosmosResourceNotFoundError:
            return None
        except Exception as error:
            logger.error("workflow_state_get_failed", error=str(error), workflow_id=workflow_id)
            return None

    async def list_user_workflows(
        self,
        user_id: str,
        workflow_type: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[WorkflowState]:
        """
        List workflows for a user with optional filters.

        Args:
            user_id: The user identifier
            workflow_type: Optional filter by workflow type
            status: Optional filter by status
            limit: Maximum number of workflows to return

        Returns:
            List of workflow states
        """
        if not self._ensure_initialized():
            return []

        try:
            conditions = ["c.type = 'workflow'", "c.user_id = @user_id"]
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@limit", "value": limit},
            ]

            if workflow_type:
                conditions.append("c.workflow_type = @workflow_type")
                parameters.append({"name": "@workflow_type", "value": workflow_type})

            if status:
                conditions.append("c.status = @status")
                parameters.append({"name": "@status", "value": status})

            query = f"""
                SELECT * FROM c
                WHERE {" AND ".join(conditions)}
                ORDER BY c.updated_at DESC
                OFFSET 0 LIMIT @limit
            """

            items = list(
                self.workflows_container.query_items(
                    query=query,
                    parameters=parameters,
                    partition_key=user_id,
                )
            )

            return [
                WorkflowState(
                    id=item["id"],
                    workflow_id=item["workflow_id"],
                    user_id=item["user_id"],
                    workflow_type=item["workflow_type"],
                    status=item["status"],
                    current_step=item.get("current_step"),
                    context=item.get("context", {}),
                    result=item.get("result"),
                    error=item.get("error"),
                    created_at=datetime.fromisoformat(item["created_at"]),
                    updated_at=datetime.fromisoformat(item["updated_at"]),
                )
                for item in items
            ]

        except Exception as error:
            logger.error("workflows_list_failed", error=str(error), user_id=user_id)
            return []

    async def delete_workflow(self, workflow_id: str, user_id: str) -> bool:
        """
        Delete a workflow state.

        Args:
            workflow_id: The workflow identifier
            user_id: The user identifier

        Returns:
            True if deleted successfully
        """
        if not self._ensure_initialized():
            return False

        try:
            self.workflows_container.delete_item(
                item=f"wf_{workflow_id}",
                partition_key=user_id,
            )
            logger.info("workflow_deleted", workflow_id=workflow_id)
            return True
        except CosmosResourceNotFoundError:
            logger.warning("workflow_not_found", workflow_id=workflow_id)
            return False
        except Exception as error:
            logger.error("workflow_delete_failed", error=str(error), workflow_id=workflow_id)
            return False

    # ============= Health Check =============

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check on the Cosmos DB connection.

        Returns:
            Health check result with status and details
        """
        if not self._ensure_initialized():
            return {
                "status": "unconfigured",
                "details": {
                    "message": "Cosmos DB not configured",
                    "timestamp": time.time(),
                },
            }

        try:
            start_time = time.time()

            # Read container metadata to verify connection
            if self.chat_container:
                self.chat_container.read()

            response_time = (time.time() - start_time) * 1000

            return {
                "status": "up",
                "details": {
                    "responseTime": f"{response_time:.2f}ms",
                    "status": "connected",
                    "timestamp": time.time(),
                },
            }

        except Exception as error:
            logger.error("cosmos_health_check_failed", error=str(error))
            return {
                "status": "down",
                "details": {
                    "error": str(error),
                    "status": "disconnected",
                    "timestamp": time.time(),
                },
            }

    def dispose(self) -> None:
        """Dispose of the Cosmos DB client."""
        if self.client:
            self.client = None
            self.database = None
            self.chat_container = None
            self.documents_container = None
            self.workflows_container = None
            self._initialized = False
            logger.info("cosmos_db_disposed")


# Global service instance
_cosmos_db_service: CosmosDbService | None = None


def get_cosmos_db_service() -> CosmosDbService:
    """Get the global Cosmos DB service instance."""
    global _cosmos_db_service
    if _cosmos_db_service is None:
        _cosmos_db_service = CosmosDbService()
    return _cosmos_db_service


@asynccontextmanager
async def cosmos_db_context():
    """Context manager for Cosmos DB service."""
    service = get_cosmos_db_service()
    try:
        yield service
    finally:
        pass  # Cleanup if needed
