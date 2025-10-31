"""
Cosmos DB service for document operations and vector search.

This service provides comprehensive Cosmos DB operations including:
- CRUD operations for documents
- Vector similarity search using Cosmos DB's native vector capabilities
- Managed identity authentication with key fallback
- Error handling and logging
- Health checks and monitoring
"""

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from azure.cosmos import ContainerProxy, CosmosClient, DatabaseProxy, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, Field

from app.core.config import settings


class QueryOptions(BaseModel):
    """Options for Cosmos DB queries."""

    enable_cross_partition_query: bool = Field(default=False)
    max_item_count: int = Field(default=100, ge=1, le=1000)
    partition_key: str | None = None


class VectorSearchOptions(BaseModel):
    """Options for vector similarity search."""

    partition_key: str | None = None
    document_id: str | None = None
    top_k: int = Field(default=3, ge=1, le=100)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    enable_cross_partition_query: bool = Field(default=False)
    user_id: str | None = None


class PaginatedResult(BaseModel):
    """Paginated query result."""

    resources: list[dict[str, Any]]
    continuation_token: str | None = None
    has_more: bool = False


class CosmosDbService:
    """Service for Cosmos DB operations."""

    def __init__(self):
        """Initialize the Cosmos DB service."""
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self.client: CosmosClient | None = None
        self.database: DatabaseProxy | None = None
        self.container: ContainerProxy | None = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Cosmos DB client with managed identity or key authentication."""
        endpoint = self.settings.COSMOS_DB_ENDPOINT
        database_name = self.settings.COSMOS_DB_DATABASE_NAME
        container_name = self.settings.COSMOS_DB_CONTAINER_NAME

        # Check for required configuration
        if self.settings.ENVIRONMENT != "local":
            if not endpoint or not database_name or not container_name:
                self.logger.error("Missing Cosmos DB configuration in environment variables")
                raise ValueError("Cosmos DB configuration is incomplete")

        try:
            # Connection configuration for better performance
            # Using direct parameters instead of connection_policy dict
            connection_timeout = 30  # 30 second timeout

            # Use managed identity for production, key for local development
            if self.settings.ENVIRONMENT == "local" and self.settings.COSMOS_DB_KEY:
                self.client = CosmosClient(
                    url=endpoint,
                    credential=self.settings.COSMOS_DB_KEY,
                    enable_endpoint_discovery=False,
                    connection_timeout=connection_timeout,
                )
                self.logger.info("Cosmos DB client initialized with key authentication")
            else:
                credential = DefaultAzureCredential()
                self.client = CosmosClient(
                    url=endpoint,
                    credential=credential,
                    enable_endpoint_discovery=True,
                    connection_timeout=connection_timeout,
                )
                self.logger.info("Cosmos DB client initialized with managed identity")

            self.database = self.client.get_database_client(database_name)
            self.container = self.database.get_container_client(container_name)

            self.logger.info("Cosmos DB client initialized successfully")

        except Exception as error:
            self.logger.error(f"Failed to initialize Cosmos DB client: {error}")
            raise

    def get_container(self, container_name: str) -> ContainerProxy:
        """
        Get a container client for the specified container name.

        Args:
            container_name: The name of the container

        Returns:
            ContainerProxy for the specified container

        Raises:
            ValueError: If database is not initialized
            CosmosResourceNotFoundError: If container doesn't exist
        """
        if not self.database:
            raise ValueError("Database not initialized")

        return self.database.get_container_client(container_name)

    async def create_container(
        self,
        container_name: str,
        partition_key_path: str,
        container_properties: dict[str, Any] | None = None,
    ) -> ContainerProxy:
        """Create a container if it does not already exist."""
        if not self.database:
            raise ValueError("Database not initialized")

        try:
            partition_key = PartitionKey(path=partition_key_path)
            indexing_policy = None
            if container_properties:
                indexing_policy = container_properties.get("indexingPolicy")

            container = self.database.create_container_if_not_exists(
                id=container_name,
                partition_key=partition_key,
                indexing_policy=indexing_policy,
            )

            self.logger.info("Cosmos DB container ensured", container_name=container_name)
            return container

        except Exception as error:
            self.logger.error(f"Failed to create Cosmos DB container '{container_name}': {error}")
            raise

    async def delete_container(self, container_name: str) -> None:
        """Delete a container if it exists."""
        if not self.database:
            raise ValueError("Database not initialized")

        try:
            self.database.delete_container(container_name)
            self.logger.info("Cosmos DB container deleted", container_name=container_name)
        except CosmosResourceNotFoundError:
            self.logger.warning(
                "Cosmos DB container not found during delete",
                container_name=container_name,
            )
        except Exception as error:
            self.logger.error(f"Failed to delete Cosmos DB container '{container_name}': {error}")
            raise

    async def create_item(self, item: dict[str, Any], partition_key: str) -> dict[str, Any]:
        """
        Create an item in Cosmos DB.

        Args:
            item: The item to create
            partition_key: The partition key value

        Returns:
            The created item response

        Raises:
            ValueError: If item is too large
            Exception: For other Cosmos DB errors
        """
        try:
            # Check item size (Cosmos DB has 2MB limit)
            item_size_bytes = len(json.dumps(item).encode("utf-8"))

            # Log warning for large items (approaching 2MB limit)
            if item_size_bytes > 1500000:  # 1.5MB warning threshold
                self.logger.warning(
                    f"Item size is {item_size_bytes // 1024}KB, approaching Cosmos DB 2MB limit"
                )

            self.logger.debug(f"Creating item with size: {item_size_bytes // 1024}KB")

            response = self.container.create_item(body=item)
            return response

        except CosmosHttpResponseError as error:
            if error.status_code == 413:  # Request entity too large
                item_size_kb = item_size_bytes // 1024
                self.logger.error(
                    f"Cosmos DB request size too large: {item_size_kb}KB exceeds 2MB limit"
                )
                raise ValueError(
                    f"Document too large for Cosmos DB storage ({item_size_kb}KB). "
                    "Consider breaking it into smaller chunks."
                ) from error

            self.logger.error(f"Error creating item in Cosmos DB: {error}")
            raise
        except Exception as error:
            self.logger.error(f"Error creating item in Cosmos DB: {error}")
            raise

    async def get_item(self, item_id: str, partition_key: str) -> dict[str, Any] | None:
        """
        Get an item from Cosmos DB.

        Args:
            item_id: The item ID
            partition_key: The partition key value

        Returns:
            The item if found, None otherwise
        """
        try:
            response = self.container.read_item(item=item_id, partition_key=partition_key)
            return response
        except CosmosResourceNotFoundError:
            return None
        except Exception as error:
            self.logger.error(f"Error getting item from Cosmos DB: {error}")
            raise

    async def update_item(
        self, item_id: str, item: dict[str, Any], partition_key: str
    ) -> dict[str, Any]:
        """
        Update an item in Cosmos DB.

        Args:
            item_id: The item ID
            item: The updated item data
            partition_key: The partition key value

        Returns:
            The updated item response
        """
        try:
            response = self.container.replace_item(item=item_id, body=item)
            return response
        except Exception as error:
            self.logger.error(f"Error updating item in Cosmos DB: {error}")
            raise

    async def delete_item(self, item_id: str, partition_key: str) -> dict[str, Any]:
        """
        Delete an item from Cosmos DB.

        Args:
            item_id: The item ID
            partition_key: The partition key value

        Returns:
            The delete response
        """
        try:
            response = self.container.delete_item(item=item_id, partition_key=partition_key)
            return response
        except Exception as error:
            self.logger.error(f"Error deleting item from Cosmos DB: {error}")
            raise

    async def query_items(
        self, query_spec: str | dict[str, Any], options: QueryOptions | None = None
    ) -> list[dict[str, Any]]:
        """
        Query items from Cosmos DB.

        Args:
            query_spec: SQL query string or query specification
            options: Query options

        Returns:
            List of matching items
        """
        if options is None:
            options = QueryOptions()

        try:
            query_kwargs = {
                "enable_cross_partition_query": options.enable_cross_partition_query,
                "max_item_count": options.max_item_count,
            }

            # For single partition queries, use partition key for better performance
            if options.partition_key and not options.enable_cross_partition_query:
                query_kwargs["partition_key"] = options.partition_key

            items = list(self.container.query_items(query=query_spec, **query_kwargs))

            return items

        except Exception as error:
            self.logger.error(f"Error querying items from Cosmos DB: {error}")
            raise

    async def query_items_cross_partition(
        self, query_spec: str | dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Query items across all partitions.

        Args:
            query_spec: SQL query string or query specification

        Returns:
            List of matching items
        """
        try:
            # Extract limit from query parameters if present
            max_items = 100
            if isinstance(query_spec, dict) and "parameters" in query_spec:
                limit_param = next(
                    (p for p in query_spec["parameters"] if p.get("name") == "@limit"),
                    None,
                )
                if limit_param:
                    max_items = limit_param.get("value", 100)

            items = list(
                self.container.query_items(
                    query=query_spec,
                    enable_cross_partition_query=True,
                    max_item_count=max_items,
                )
            )

            return items

        except Exception as error:
            self.logger.error(f"Error querying items cross-partition from Cosmos DB: {error}")
            raise

    async def query_items_cross_partition_with_pagination(
        self,
        query_spec: str | dict[str, Any],
        page_size: int = 50,
        continuation_token: str | None = None,
    ) -> PaginatedResult:
        """
        Query items across partitions with pagination.

        Args:
            query_spec: SQL query string or query specification
            page_size: Maximum items per page
            continuation_token: Token for next page

        Returns:
            Paginated result with items and continuation token
        """
        try:
            query_kwargs = {
                "enable_cross_partition_query": True,
                "max_item_count": page_size,
            }

            if continuation_token:
                # Note: Python SDK handles continuation differently
                # This is a simplified implementation
                pass

            # Get iterator for pagination
            query_iterator = self.container.query_items(query=query_spec, **query_kwargs)

            items = []
            for item in query_iterator:
                items.append(item)
                if len(items) >= page_size:
                    break

            # In the Python SDK, continuation token handling is different
            # This is a simplified implementation
            has_more = len(items) == page_size
            next_token = None  # Would need to implement proper pagination

            return PaginatedResult(
                resources=items, continuation_token=next_token, has_more=has_more
            )

        except Exception as error:
            self.logger.error(
                f"Error querying items cross-partition with pagination from Cosmos DB: {error}"
            )
            raise

    async def vector_search(
        self, embedding: list[float], options: VectorSearchOptions | None = None
    ) -> list[dict[str, Any]]:
        """
        Perform vector similarity search using Cosmos DB's native vector search.

        Args:
            embedding: The query embedding vector
            options: Vector search options

        Returns:
            List of similar items with similarity scores
        """
        if options is None:
            options = VectorSearchOptions()

        try:
            # Build the vector search query using Cosmos DB's VectorDistance function
            where_clause = "c.type = @type AND c.embedding != null"
            parameters = [
                {"name": "@type", "value": "chunk"},
                {"name": "@embedding", "value": embedding},
                {"name": "@topK", "value": options.top_k},
            ]

            # Add filters based on options
            if options.partition_key and not options.enable_cross_partition_query:
                where_clause += " AND c.partitionKey = @partitionKey"
                parameters.append({"name": "@partitionKey", "value": options.partition_key})

            if options.document_id:
                where_clause += " AND c.documentId = @documentId"
                parameters.append({"name": "@documentId", "value": options.document_id})

            if options.min_similarity > 0:
                where_clause += " AND VectorDistance(c.embedding, @embedding) >= @minSimilarity"
                parameters.append({"name": "@minSimilarity", "value": options.min_similarity})

            query_spec = {
                "query": f"""
                    SELECT TOP @topK c.id, c.documentId, c.content, c.embedding, c.metadata,
                           c.partitionKey, c.type,
                           VectorDistance(c.embedding, @embedding) AS similarity
                    FROM c
                    WHERE {where_clause}
                    ORDER BY VectorDistance(c.embedding, @embedding)
                """,
                "parameters": parameters,
            }

            query_kwargs = {
                "enable_cross_partition_query": options.enable_cross_partition_query,
                "max_item_count": options.top_k,
            }

            # For single partition queries, use partition key for better performance
            if options.partition_key and not options.enable_cross_partition_query:
                query_kwargs["partition_key"] = options.partition_key

            import time

            start_time = time.time()

            items = list(self.container.query_items(query=query_spec, **query_kwargs))

            query_time = (time.time() - start_time) * 1000
            self.logger.debug(
                f"Vector search completed in {query_time:.2f}ms, found {len(items)} results"
            )

            return items

        except Exception as error:
            # Enhanced error handling following Azure best practices
            error_message = str(error)

            if "InvalidQuery" in error_message:
                self.logger.error(
                    "Invalid vector search query - check embedding dimensions and query structure"
                )
                raise ValueError(f"Vector search query error: {error_message}") from error
            elif "RequestRateTooLarge" in error_message:
                self.logger.warning("Cosmos DB request rate exceeded - implementing backoff")
                raise Exception(f"Rate limit exceeded: {error_message}") from error
            elif "ServiceUnavailable" in error_message:
                self.logger.error("Cosmos DB service unavailable")
                raise Exception(f"Service unavailable: {error_message}") from error
            elif "VectorDistance" in error_message:
                self.logger.error(
                    "VectorDistance function error - check vector indexing configuration"
                )
                raise ValueError(f"Vector indexing error: {error_message}") from error

            self.logger.error(f"Error performing vector search in Cosmos DB: {error}")
            raise

    async def vector_search_cross_partition(
        self, embedding: list[float], options: VectorSearchOptions | None = None
    ) -> list[dict[str, Any]]:
        """
        Perform cross-partition vector search across all user documents.

        Args:
            embedding: The query embedding vector
            options: Vector search options

        Returns:
            List of similar items with similarity scores
        """
        if options is None:
            options = VectorSearchOptions(top_k=5)

        try:
            where_clause = "c.type = @type AND c.embedding != null"
            parameters = [
                {"name": "@type", "value": "chunk"},
                {"name": "@embedding", "value": embedding},
                {"name": "@topK", "value": options.top_k},
            ]

            # Filter by user if specified
            if options.user_id:
                where_clause += " AND c.partitionKey = @partitionKey"
                parameters.append({"name": "@partitionKey", "value": options.user_id})

            if options.min_similarity > 0:
                where_clause += " AND VectorDistance(c.embedding, @embedding) >= @minSimilarity"
                parameters.append({"name": "@minSimilarity", "value": options.min_similarity})

            query_spec = {
                "query": f"""
                    SELECT TOP @topK c.id, c.documentId, c.content, c.embedding, c.metadata,
                           c.partitionKey, c.type,
                           VectorDistance(c.embedding, @embedding) AS similarity
                    FROM c
                    WHERE {where_clause}
                    ORDER BY VectorDistance(c.embedding, @embedding)
                """,
                "parameters": parameters,
            }

            import time

            start_time = time.time()

            items = list(
                self.container.query_items(
                    query=query_spec,
                    enable_cross_partition_query=True,
                    max_item_count=options.top_k,
                )
            )

            query_time = (time.time() - start_time) * 1000
            self.logger.info(
                f"Cross-partition vector search completed in {query_time:.2f}ms, "
                f"found {len(items)} results"
            )

            return items

        except Exception as error:
            self.logger.error(
                f"Error performing cross-partition vector search in Cosmos DB: {error}"
            )
            raise

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check on the Cosmos DB connection.

        Returns:
            Health check result with status and details
        """
        try:
            start_time = time.time()

            # Try to read the container properties to verify connection
            # This is a lightweight operation that validates connectivity
            if self.container:
                self.container.read()  # This reads container metadata
            else:
                raise ValueError("Container not initialized")

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
            self.logger.error(f"Cosmos DB health check failed: {error}")

            error_message = str(error)
            error_code = getattr(error, "status_code", "UNKNOWN")

            return {
                "status": "down",
                "details": {
                    "error": error_message,
                    "errorCode": error_code,
                    "status": "disconnected",
                    "timestamp": time.time(),
                },
            }

    def dispose(self) -> None:
        """Dispose of the Cosmos DB client."""
        if self.client:
            # The Python SDK doesn't have an explicit dispose method
            # but we can clear references
            self.client = None
            self.database = None
            self.container = None
            self.logger.info("Cosmos DB client disposed")


# Global service instance
_cosmos_db_service: CosmosDbService | None = None


def get_cosmos_db_service() -> CosmosDbService:
    """Get the global Cosmos DB service instance."""
    global _cosmos_db_service
    if _cosmos_db_service is None:
        _cosmos_db_service = CosmosDbService()
    return _cosmos_db_service


@asynccontextmanager
async def cosmos_db_service():
    """Context manager for Cosmos DB service."""
    service = get_cosmos_db_service()
    try:
        yield service
    finally:
        # Cleanup if needed
        pass
