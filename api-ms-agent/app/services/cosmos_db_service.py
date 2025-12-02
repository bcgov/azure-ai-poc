"""
Cosmos DB service for chat history and vector embeddings storage.

This service provides:
- Chat history storage and retrieval
- Vector similarity search using Cosmos DB's native vector capabilities
- Document embeddings storage
- Managed identity authentication with key fallback
"""

import json
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
class DocumentChunk:
    """A document chunk with vector embedding stored in Cosmos DB."""

    id: str
    document_id: str
    user_id: str  # Partition key
    content: str
    embedding: list[float]
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class VectorSearchOptions:
    """Options for vector similarity search."""

    user_id: str | None = None
    document_id: str | None = None
    top_k: int = 5
    min_similarity: float = 0.0


class CosmosDbService:
    """Service for Cosmos DB operations including chat history and vector search."""

    # Container names
    CHAT_CONTAINER = "chat_history"
    DOCUMENTS_CONTAINER = "documents"

    def __init__(self) -> None:
        """Initialize the Cosmos DB service."""
        self.client: CosmosClient | None = None
        self.database: DatabaseProxy | None = None
        self.chat_container: ContainerProxy | None = None
        self.documents_container: ContainerProxy | None = None
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
                message="Cosmos DB not configured - chat history will not be persisted",
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

        # Create documents container if it doesn't exist
        # This container needs vector indexing policy for embeddings
        try:
            # Define indexing policy with vector index for embeddings
            indexing_policy = {
                "indexingMode": "consistent",
                "automatic": True,
                "includedPaths": [{"path": "/*"}],
                "excludedPaths": [{"path": '/"_etag"/?'}],
            }

            # Define vector embedding policy
            vector_embedding_policy = {
                "vectorEmbeddings": [
                    {
                        "path": "/embedding",
                        "dataType": "float32",
                        "distanceFunction": "cosine",
                        "dimensions": 1536,  # text-embedding-ada-002 dimensions
                    }
                ]
            }

            self.database.create_container_if_not_exists(
                id=self.DOCUMENTS_CONTAINER,
                partition_key=PartitionKey(path="/user_id"),
                offer_throughput=400,
                indexing_policy=indexing_policy,
                vector_embedding_policy=vector_embedding_policy,
            )
            logger.info("container_ensured", container=self.DOCUMENTS_CONTAINER)
        except CosmosHttpResponseError as e:
            if e.status_code != 409:  # 409 = already exists
                logger.warning(
                    "container_create_warning",
                    container=self.DOCUMENTS_CONTAINER,
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

    # ============= Vector Search Operations =============

    async def store_document_chunk(
        self,
        document_id: str,
        user_id: str,
        content: str,
        embedding: list[float],
        chunk_index: int,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentChunk:
        """
        Store a document chunk with its vector embedding.

        Args:
            document_id: The parent document identifier
            user_id: The user identifier (partition key)
            content: The text content of the chunk
            embedding: The vector embedding
            chunk_index: Index of this chunk in the document
            metadata: Optional additional metadata

        Returns:
            The stored document chunk
        """
        chunk_id = f"{document_id}_chunk_{chunk_index}"
        chunk = DocumentChunk(
            id=chunk_id,
            document_id=document_id,
            user_id=user_id,
            content=content,
            embedding=embedding,
            chunk_index=chunk_index,
            metadata=metadata or {},
        )

        if not self._ensure_initialized():
            return chunk

        # Check embedding size (Cosmos DB has 2MB item limit)
        item = {
            "id": chunk_id,
            "type": "chunk",
            "document_id": document_id,
            "user_id": user_id,
            "content": content,
            "embedding": embedding,
            "chunk_index": chunk_index,
            "metadata": metadata or {},
            "created_at": chunk.created_at.isoformat(),
        }

        item_size = len(json.dumps(item).encode("utf-8"))
        if item_size > 1500000:  # 1.5MB warning threshold
            logger.warning(
                "chunk_size_warning",
                size_kb=item_size // 1024,
                chunk_id=chunk_id,
            )

        try:
            self.documents_container.create_item(body=item)
            logger.debug(
                "chunk_stored",
                chunk_id=chunk_id,
                document_id=document_id,
                embedding_dims=len(embedding),
            )
            return chunk
        except CosmosHttpResponseError as error:
            if error.status_code == 413:
                logger.error("chunk_too_large", size_kb=item_size // 1024)
                raise ValueError(f"Document chunk too large: {item_size // 1024}KB") from error
            raise
        except Exception as error:
            logger.error("chunk_store_failed", error=str(error), chunk_id=chunk_id)
            raise

    async def vector_search(
        self,
        embedding: list[float],
        options: VectorSearchOptions | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform vector similarity search using Cosmos DB's native vector search.

        Args:
            embedding: The query embedding vector
            options: Vector search options

        Returns:
            List of similar document chunks with similarity scores
        """
        if not self._ensure_initialized():
            return []

        if options is None:
            options = VectorSearchOptions()

        try:
            where_clause = "c.type = 'chunk' AND c.embedding != null"
            parameters = [
                {"name": "@embedding", "value": embedding},
                {"name": "@topK", "value": options.top_k},
            ]

            # Filter by user if specified
            if options.user_id:
                where_clause += " AND c.user_id = @user_id"
                parameters.append({"name": "@user_id", "value": options.user_id})

            # Filter by document if specified
            if options.document_id:
                where_clause += " AND c.document_id = @document_id"
                parameters.append({"name": "@document_id", "value": options.document_id})

            # Filter by minimum similarity
            if options.min_similarity > 0:
                where_clause += " AND VectorDistance(c.embedding, @embedding) >= @minSimilarity"
                parameters.append({"name": "@minSimilarity", "value": options.min_similarity})

            query_spec = {
                "query": f"""
                    SELECT TOP @topK c.id, c.document_id, c.content, c.metadata,
                           c.user_id, c.chunk_index,
                           VectorDistance(c.embedding, @embedding) AS similarity
                    FROM c
                    WHERE {where_clause}
                    ORDER BY VectorDistance(c.embedding, @embedding)
                """,
                "parameters": parameters,
            }

            start_time = time.time()

            items = list(
                self.documents_container.query_items(
                    query=query_spec,
                    enable_cross_partition_query=True,
                    max_item_count=options.top_k,
                )
            )

            query_time = (time.time() - start_time) * 1000
            logger.info(
                "vector_search_completed",
                results=len(items),
                query_time_ms=f"{query_time:.2f}",
                top_k=options.top_k,
            )

            return items

        except Exception as error:
            error_message = str(error)

            if "VectorDistance" in error_message:
                logger.error(
                    "vector_search_config_error",
                    message="Check vector indexing configuration",
                )
                raise ValueError(f"Vector indexing error: {error_message}") from error

            logger.error("vector_search_failed", error=error_message)
            raise

    async def list_user_documents(self, user_id: str, limit: int = 50) -> list[dict]:
        """
        List documents for a user by aggregating unique document IDs from chunks.

        Args:
            user_id: The user identifier
            limit: Maximum number of documents to return

        Returns:
            List of document metadata
        """
        if not self._ensure_initialized():
            return []

        try:
            # Query to get unique documents with their metadata
            query = """
                SELECT DISTINCT VALUE {
                    'id': c.document_id,
                    'document_id': c.document_id,
                    'title': c.metadata.title,
                    'created_at': c.created_at,
                    'chunk_count': 1
                }
                FROM c
                WHERE c.type = 'chunk' AND c.user_id = @user_id
            """
            parameters = [{"name": "@user_id", "value": user_id}]

            items = list(
                self.documents_container.query_items(
                    query=query,
                    parameters=parameters,
                    partition_key=user_id,
                    max_item_count=limit,
                )
            )

            # Aggregate to get unique documents (query returns duplicates for each chunk)
            documents_map: dict[str, dict] = {}
            for item in items:
                doc_id = item.get("document_id")
                if doc_id and doc_id not in documents_map:
                    documents_map[doc_id] = {
                        "id": doc_id,
                        "document_id": doc_id,
                        "title": item.get("title") or f"Document {doc_id[:8]}...",
                        "created_at": item.get("created_at"),
                    }

            # Now count chunks per document
            for doc_id in documents_map:
                count_query = """
                    SELECT VALUE COUNT(1) FROM c
                    WHERE c.type = 'chunk' AND c.document_id = @doc_id AND c.user_id = @user_id
                """
                count_params = [
                    {"name": "@doc_id", "value": doc_id},
                    {"name": "@user_id", "value": user_id},
                ]
                count_result = list(
                    self.documents_container.query_items(
                        query=count_query,
                        parameters=count_params,
                        partition_key=user_id,
                    )
                )
                documents_map[doc_id]["chunk_count"] = count_result[0] if count_result else 0

            result = list(documents_map.values())[:limit]
            logger.info("documents_listed", user_id=user_id, count=len(result))
            return result

        except CosmosResourceNotFoundError:
            # Container or partition doesn't exist yet - return empty list
            logger.info("documents_list_empty", user_id=user_id, reason="partition_not_found")
            return []
        except Exception as error:
            logger.error("documents_list_failed", error=str(error), user_id=user_id)
            return []

    async def delete_document_chunks(self, document_id: str, user_id: str) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_id: The document identifier
            user_id: The user identifier

        Returns:
            Number of chunks deleted
        """
        if not self._ensure_initialized():
            return 0

        try:
            query = """
                SELECT c.id FROM c
                WHERE c.type = 'chunk'
                AND c.document_id = @document_id
            """
            parameters = [{"name": "@document_id", "value": document_id}]

            items = list(
                self.documents_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )

            deleted_count = 0
            for item in items:
                self.documents_container.delete_item(
                    item=item["id"],
                    partition_key=user_id,
                )
                deleted_count += 1

            logger.info(
                "chunks_deleted",
                document_id=document_id,
                count=deleted_count,
            )
            return deleted_count

        except Exception as error:
            logger.error(
                "chunks_delete_failed",
                error=str(error),
                document_id=document_id,
            )
            return 0

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
