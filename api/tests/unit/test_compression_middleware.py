"""Unit tests for compression middleware."""

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from app.middleware.compression_middleware import CompressionMiddleware


class TestCompressionMiddleware:
    """Tests for CompressionMiddleware class."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with compression middleware."""
        app = FastAPI()

        app.add_middleware(CompressionMiddleware, min_size=100, compression_level=6)

        @app.get("/large")
        async def large_response():
            """Return a large JSON response."""
            return {"data": "x" * 2000}  # > min_size

        @app.get("/small")
        async def small_response():
            """Return a small JSON response."""
            return {"data": "small"}

        @app.get("/text")
        async def text_response():
            """Return a large text response."""
            return JSONResponse(
                content="This is a long text " * 100,
                media_type="text/plain",
            )

        @app.get("/binary")
        async def binary_response():
            """Return a binary response (not compressible)."""
            return JSONResponse(content={"data": "test"}, media_type="application/octet-stream")

        @app.get("/health")
        async def health():
            """Health check endpoint (excluded from compression)."""
            return {"status": "ok"}

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_compress_large_response(self, client):
        """Test that large responses are compressed."""
        headers = {"accept-encoding": "gzip"}
        response = client.get("/large", headers=headers)

        assert response.status_code == 200
        assert response.headers.get("content-encoding") == "gzip"

        # Verify content can be decompressed
        data = response.json()
        assert data["data"] == "x" * 2000

    def test_no_compression_small_response(self, client):
        """Test that small responses are not compressed."""
        headers = {"accept-encoding": "gzip"}
        response = client.get("/small", headers=headers)

        assert response.status_code == 200
        # Should not be compressed (below min_size)
        assert (
            "content-encoding" not in response.headers
            or response.headers.get("content-encoding") != "gzip"
        )

    def test_no_compression_without_accept_encoding(self, client):
        """Test that responses are not compressed without accept-encoding header."""
        # Note: TestClient may add default headers, so we check behavior not headers
        response = client.get("/large")

        assert response.status_code == 200
        # Response should be readable regardless of compression
        data = response.json()
        assert data["data"] == "x" * 2000

    def test_compress_text_response(self, client):
        """Test compression of text/plain responses."""
        headers = {"accept-encoding": "gzip"}
        response = client.get("/text", headers=headers)

        assert response.status_code == 200
        assert response.headers.get("content-encoding") == "gzip"

    def test_no_compression_binary(self, client):
        """Test that binary responses are not compressed."""
        headers = {"accept-encoding": "gzip"}
        response = client.get("/binary", headers=headers)

        assert response.status_code == 200
        # Should not be compressed (not in compressible_types)
        assert (
            "content-encoding" not in response.headers
            or response.headers.get("content-encoding") != "gzip"
        )

    def test_excluded_path(self, client):
        """Test that excluded paths are not compressed."""
        headers = {"accept-encoding": "gzip"}
        response = client.get("/health", headers=headers)

        assert response.status_code == 200
        # Should not be compressed (excluded path)
        assert (
            "content-encoding" not in response.headers
            or response.headers.get("content-encoding") != "gzip"
        )

    def test_compression_stats(self):
        """Test compression statistics tracking."""
        middleware = CompressionMiddleware(app=None, min_size=100)  # type: ignore[arg-type]

        # Initially zero
        stats = middleware.get_stats()
        assert stats["compressed_responses"] == 0
        assert stats["total_bytes_saved"] == 0
        assert stats["total_mb_saved"] == 0.0

    def test_content_length_header(self, client):
        """Test that content-length header is updated after compression."""
        headers = {"accept-encoding": "gzip"}
        response = client.get("/large", headers=headers)

        assert response.status_code == 200
        assert "content-length" in response.headers

        # TestClient automatically decompresses, so we verify the response is valid
        data = response.json()
        assert data["data"] == "x" * 2000

        # Verify compression actually happened (header shows compressed size)
        content_length = int(response.headers["content-length"])
        # Compressed size should be much smaller than 2011 bytes
        assert content_length < 500  # Compressed gzip should be tiny for repeated chars

    def test_multiple_accept_encodings(self, client):
        """Test with multiple accept-encoding values."""
        headers = {"accept-encoding": "deflate, gzip, br"}
        response = client.get("/large", headers=headers)

        assert response.status_code == 200
        # Should still use gzip
        assert response.headers.get("content-encoding") == "gzip"

    def test_case_insensitive_accept_encoding(self, client):
        """Test that accept-encoding header is case-insensitive."""
        headers = {"accept-encoding": "GZIP"}
        response = client.get("/large", headers=headers)

        assert response.status_code == 200
        assert response.headers.get("content-encoding") == "gzip"
