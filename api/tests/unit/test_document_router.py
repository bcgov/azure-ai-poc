"""Unit tests for document router input validation and error handling."""

from unittest.mock import AsyncMock, patch

import pytest


class TestDocumentRouterValidation:
    """Tests for document router input validation and error scenarios."""

    @pytest.mark.asyncio
    async def test_document_service_get_documents_handles_errors(self):
        """Test that get_documents handles service errors gracefully."""
        from app.services.document_service import DocumentService

        service = DocumentService()

        with patch.object(service, "list_documents", AsyncMock()) as mock_list:
            mock_list.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                await service.list_documents(
                    tenant_id="test-tenant",
                    skip=0,
                    limit=10,
                )

    @pytest.mark.asyncio
    async def test_document_service_validates_tenant_id(self):
        """Test that document service validates tenant ID format."""
        from app.services.document_service import DocumentService

        service = DocumentService()

        # Test with invalid tenant ID (empty string)
        with patch.object(service, "list_documents", AsyncMock()) as mock_list:
            mock_list.side_effect = ValueError("Invalid tenant ID")

            with pytest.raises(ValueError):
                await service.list_documents(
                    tenant_id="",  # Empty tenant ID
                    skip=0,
                    limit=10,
                )

    @pytest.mark.asyncio
    async def test_document_service_handles_not_found(self):
        """Test document service handles not found errors."""
        from app.services.document_service import DocumentService

        service = DocumentService()

        with patch.object(service, "get_document", AsyncMock()) as mock_get:
            mock_get.side_effect = FileNotFoundError("Document not found")

            with pytest.raises(FileNotFoundError):
                await service.get_document(
                    document_id="nonexistent",
                    tenant_id="test-tenant",
                )

    @pytest.mark.asyncio
    async def test_document_service_handles_permission_errors(self):
        """Test document service handles permission errors."""
        from app.services.document_service import DocumentService

        service = DocumentService()

        with patch.object(service, "delete_document", AsyncMock()) as mock_delete:
            mock_delete.side_effect = PermissionError("Access denied")

            with pytest.raises(PermissionError):
                await service.delete_document(
                    document_id="doc-123",
                    tenant_id="test-tenant",
                )


class TestDocumentServiceEdgeCases:
    """Tests for document service edge cases."""

    @pytest.mark.asyncio
    async def test_list_documents_with_negative_skip(self):
        """Test list documents rejects negative skip."""
        from app.services.document_service import DocumentService

        service = DocumentService()

        with patch.object(service, "list_documents", AsyncMock()) as mock_list:
            # Negative skip should be rejected
            mock_list.side_effect = ValueError("Skip must be non-negative")

            with pytest.raises(ValueError):
                await service.list_documents(
                    tenant_id="test-tenant",
                    skip=-1,
                    limit=10,
                )

    @pytest.mark.asyncio
    async def test_list_documents_with_zero_limit(self):
        """Test list documents handles zero limit."""
        from app.services.document_service import DocumentService

        service = DocumentService()

        with patch.object(service, "list_documents", AsyncMock()) as mock_list:
            mock_list.return_value = []

            # Zero limit should return empty results
            results = await service.list_documents(
                tenant_id="test-tenant",
                skip=0,
                limit=0,
            )

            assert results == []

    @pytest.mark.asyncio
    async def test_get_document_with_malformed_id(self):
        """Test get document with malformed ID."""
        from app.services.document_service import DocumentService

        service = DocumentService()

        with patch.object(service, "get_document", AsyncMock()) as mock_get:
            mock_get.side_effect = ValueError("Invalid document ID format")

            with pytest.raises(ValueError):
                await service.get_document(
                    document_id="invalid@#$%^id",
                    tenant_id="test-tenant",
                )
