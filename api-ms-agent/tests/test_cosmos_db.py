"""Tests for Cosmos DB service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.azure_search_service import DocumentChunk, VectorSearchOptions
from app.services.cosmos_db_service import (
    ChatMessage,
    ConversationSession,
    CosmosDbService,
)


class AsyncIterator:
    """Helper class to create async iterators from lists for testing."""

    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


class TestCosmosDbServiceUnconfigured:
    """Tests for Cosmos DB service when not configured."""

    def test_service_initialization(self):
        """Test service initializes without Cosmos DB configured."""
        with patch("app.services.cosmos_db_service.settings") as mock_settings:
            mock_settings.cosmos_db_endpoint = ""
            mock_settings.cosmos_db_database_name = ""
            mock_settings.cosmos_db_key = ""
            mock_settings.environment = "local"

            service = CosmosDbService()
            assert service._initialized is False
            assert service.client is None

    @pytest.mark.asyncio
    async def test_create_session_without_cosmos(self):
        """Test creating a session returns local session when Cosmos not configured."""
        with patch("app.services.cosmos_db_service.settings") as mock_settings:
            mock_settings.cosmos_db_endpoint = ""
            mock_settings.cosmos_db_database_name = ""

            service = CosmosDbService()
            session = await service.create_session("user123", "Test Session")

            assert session.user_id == "user123"
            assert session.title == "Test Session"
            assert session.session_id is not None

    @pytest.mark.asyncio
    async def test_save_message_without_cosmos(self):
        """Test saving a message returns message when Cosmos not configured."""
        with patch("app.services.cosmos_db_service.settings") as mock_settings:
            mock_settings.cosmos_db_endpoint = ""
            mock_settings.cosmos_db_database_name = ""

            service = CosmosDbService()
            message = await service.save_message(
                session_id="session123",
                user_id="user123",
                role="user",
                content="Hello!",
            )

            assert message.session_id == "session123"
            assert message.user_id == "user123"
            assert message.role == "user"
            assert message.content == "Hello!"

    @pytest.mark.asyncio
    async def test_get_chat_history_without_cosmos(self):
        """Test getting chat history returns empty list when Cosmos not configured."""
        with patch("app.services.cosmos_db_service.settings") as mock_settings:
            mock_settings.cosmos_db_endpoint = ""
            mock_settings.cosmos_db_database_name = ""

            service = CosmosDbService()
            history = await service.get_chat_history("session123", "user123")

            assert history == []

    @pytest.mark.asyncio
    async def test_health_check_unconfigured(self):
        """Test health check returns unconfigured status when Cosmos not configured."""
        with patch("app.services.cosmos_db_service.settings") as mock_settings:
            mock_settings.cosmos_db_endpoint = ""
            mock_settings.cosmos_db_database_name = ""

            service = CosmosDbService()
            health = await service.health_check()

            assert health["status"] == "unconfigured"


class TestCosmosDbServiceConfigured:
    """Tests for Cosmos DB service when configured (mocked)."""

    @pytest.fixture
    def mock_cosmos_client(self):
        """Create a mock Cosmos DB client."""
        with patch("app.services.cosmos_db_service.CosmosClient") as mock:
            mock_client = MagicMock()
            mock_database = MagicMock()
            mock_container = MagicMock()

            mock.return_value = mock_client
            mock_client.get_database_client.return_value = mock_database
            mock_database.get_container_client.return_value = mock_container

            yield {
                "client_class": mock,
                "client": mock_client,
                "database": mock_database,
                "container": mock_container,
            }

    @pytest.fixture
    def configured_settings(self):
        """Create mock configured settings."""
        with patch("app.services.cosmos_db_service.settings") as mock_settings:
            mock_settings.cosmos_db_endpoint = "https://test.documents.azure.com:443/"
            mock_settings.cosmos_db_database_name = "testdb"
            mock_settings.cosmos_db_key = "test-key"
            mock_settings.environment = "local"
            yield mock_settings

    @pytest.mark.asyncio
    async def test_create_session_with_cosmos(self, mock_cosmos_client, configured_settings):
        """Test creating a session with Cosmos configured."""
        container = mock_cosmos_client["container"]
        container.create_item = AsyncMock(return_value={"id": "session123"})

        service = CosmosDbService()
        service._initialized = True
        service.chat_container = container

        session = await service.create_session("user123", "Test Session")

        assert session.user_id == "user123"
        assert session.title == "Test Session"
        container.create_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_and_load_message(self, mock_cosmos_client, configured_settings):
        """Test saving and loading messages."""
        container = mock_cosmos_client["container"]

        # Setup mock for query - use async iterator
        container.query_items.return_value = AsyncIterator(
            [
                {
                    "id": "msg1",
                    "session_id": "session123",
                    "user_id": "user123",
                    "role": "user",
                    "content": "Hello!",
                    "timestamp": "2024-01-01T00:00:00+00:00",
                    "sources": [],
                    "metadata": {},
                }
            ]
        )

        # Setup mock for create_item as AsyncMock
        container.create_item = AsyncMock(return_value={"id": "msg1"})

        service = CosmosDbService()
        service._initialized = True
        service.chat_container = container

        # Save a message
        await service.save_message(
            session_id="session123",
            user_id="user123",
            role="user",
            content="Hello!",
        )
        container.create_item.assert_called_once()

        # Load history
        history = await service.get_chat_history("session123", "user123")
        assert len(history) == 1
        assert history[0].content == "Hello!"

    @pytest.mark.asyncio
    async def test_delete_session(self, mock_cosmos_client, configured_settings):
        """Test deleting a session."""
        container = mock_cosmos_client["container"]
        container.query_items.return_value = AsyncIterator([{"id": "msg1"}, {"id": "msg2"}])
        container.delete_item = AsyncMock()

        service = CosmosDbService()
        service._initialized = True
        service.chat_container = container

        result = await service.delete_session("session123", "user123")

        assert result is True
        # Should delete messages + session
        assert container.delete_item.call_count >= 2


class TestVectorSearchOptions:
    """Tests for VectorSearchOptions dataclass."""

    def test_default_options(self):
        """Test default vector search options."""
        options = VectorSearchOptions()
        assert options.user_id is None
        assert options.document_id is None
        assert options.top_k == 5
        assert options.min_similarity == 0.0

    def test_custom_options(self):
        """Test custom vector search options."""
        options = VectorSearchOptions(
            user_id="user123",
            document_id="doc456",
            top_k=10,
            min_similarity=0.5,
        )
        assert options.user_id == "user123"
        assert options.document_id == "doc456"
        assert options.top_k == 10
        assert options.min_similarity == 0.5


class TestDataClasses:
    """Tests for service data classes."""

    def test_chat_message(self):
        """Test ChatMessage dataclass."""
        msg = ChatMessage(
            id="msg1",
            session_id="session1",
            user_id="user1",
            role="user",
            content="Hello",
        )
        assert msg.id == "msg1"
        assert msg.role == "user"
        assert msg.sources == []
        assert msg.metadata == {}

    def test_conversation_session(self):
        """Test ConversationSession dataclass."""
        session = ConversationSession(
            id="session_123",
            session_id="123",
            user_id="user1",
            title="Test",
        )
        assert session.session_id == "123"
        assert session.message_count == 0
        assert session.tags == []

    def test_document_chunk(self):
        """Test DocumentChunk dataclass."""
        chunk = DocumentChunk(
            id="chunk1",
            document_id="doc1",
            user_id="user1",
            content="Test content",
            embedding=[0.1, 0.2, 0.3],
            chunk_index=0,
        )
        assert chunk.chunk_index == 0
        assert len(chunk.embedding) == 3
