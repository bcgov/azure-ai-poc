"""Tests for document indexing and vector search endpoints."""

from unittest.mock import AsyncMock, MagicMock

from app.config import settings
from app.main import app
from app.services.azure_search_service import get_azure_search_service
from app.services.cosmos_db_service import get_cosmos_db_service
from app.services.document_intelligence_service import get_document_intelligence_service
from app.services.embedding_service import Document, SearchResult, get_embedding_service


class TestDocumentsEndpoints:
    """Tests for documents API endpoints."""

    def test_index_document(self, client, auth_headers):
        """Test indexing a document."""
        mock_service = MagicMock()
        mock_service.index_document = AsyncMock(
            return_value=Document(
                id="doc123",
                content="Test content",
                user_id="default_user",
                chunks=["chunk1", "chunk2"],
            )
        )
        app.dependency_overrides[get_embedding_service] = lambda: mock_service

        try:
            response = client.post(
                "/api/v1/documents/index",
                json={
                    "content": "This is test content for indexing",
                    "title": "Test Document",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == "doc123"
            assert data["chunks_created"] == 2
        finally:
            app.dependency_overrides.clear()

    def test_search_documents(self, client, auth_headers):
        """Test searching documents."""
        mock_service = MagicMock()
        mock_service.search = AsyncMock(
            return_value=[
                SearchResult(
                    chunk_id="chunk1",
                    document_id="doc1",
                    content="Relevant content",
                    similarity=0.95,
                    metadata={"title": "Test"},
                )
            ]
        )
        app.dependency_overrides[get_embedding_service] = lambda: mock_service

        try:
            response = client.post(
                "/api/v1/documents/search",
                json={"query": "test query", "top_k": 5},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["results"][0]["similarity"] == 0.95
        finally:
            app.dependency_overrides.clear()

    def test_delete_document(self, client, auth_headers):
        """Test deleting a document."""
        mock_service = MagicMock()
        mock_service.delete_document = AsyncMock(return_value=3)
        app.dependency_overrides[get_embedding_service] = lambda: mock_service

        try:
            response = client.delete(
                "/api/v1/documents/doc123",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "deleted"
            assert data["chunks_deleted"] == 3
        finally:
            app.dependency_overrides.clear()

    def test_documents_health(self, client, auth_headers):
        """Test documents health endpoint."""
        mock_cosmos = MagicMock()
        mock_cosmos.health_check = AsyncMock(
            return_value={
                "status": "up",
                "details": {"responseTime": "5.00ms"},
            }
        )
        mock_search = MagicMock()
        mock_search.health_check = AsyncMock(
            return_value={
                "status": "up",
                "details": {"responseTime": "5.00ms"},
            }
        )
        app.dependency_overrides[get_cosmos_db_service] = lambda: mock_cosmos
        app.dependency_overrides[get_azure_search_service] = lambda: mock_search

        try:
            response = client.get("/api/v1/documents/health", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["service"] == "documents"
        finally:
            app.dependency_overrides.clear()

    def test_index_document_validation_error(self, client, auth_headers):
        """Test indexing with invalid data."""
        response = client.post(
            "/api/v1/documents/index",
            json={"content": ""},  # Empty content should fail
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    def test_list_documents(self, client, auth_headers):
        """Test listing documents."""
        mock_service = MagicMock()
        mock_service.list_documents = AsyncMock(
            return_value=[
                {
                    "id": "doc1",
                    "document_id": "doc1",
                    "title": "Test Document 1",
                    "created_at": "2024-01-01T00:00:00Z",
                    "chunk_count": 5,
                },
                {
                    "id": "doc2",
                    "document_id": "doc2",
                    "title": "Test Document 2",
                    "created_at": "2024-01-02T00:00:00Z",
                    "chunk_count": 3,
                },
            ]
        )
        app.dependency_overrides[get_embedding_service] = lambda: mock_service

        try:
            response = client.get(
                "/api/v1/documents/",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["documents"]) == 2
            assert data["documents"][0]["title"] == "Test Document 1"
            assert data["documents"][1]["chunk_count"] == 3
        finally:
            app.dependency_overrides.clear()

    def test_upload_document_too_large(self, client, auth_headers, monkeypatch):
        """Upload should reject files exceeding max_upload_bytes."""
        monkeypatch.setattr(settings, "max_upload_bytes", 10)

        mock_embedding = MagicMock()
        mock_embedding.index_document = AsyncMock()
        app.dependency_overrides[get_embedding_service] = lambda: mock_embedding

        mock_doc_intel = MagicMock()
        mock_doc_intel.is_supported_format = MagicMock(return_value=True)
        mock_doc_intel.analyze_document = AsyncMock()
        app.dependency_overrides[get_document_intelligence_service] = lambda: mock_doc_intel

        try:
            response = client.post(
                "/api/v1/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", b"0123456789ABC", "text/plain")},
            )
            assert response.status_code == 413
            # Ensure downstream services were not called
            mock_doc_intel.analyze_document.assert_not_called()
            mock_embedding.index_document.assert_not_called()
        finally:
            app.dependency_overrides.clear()
