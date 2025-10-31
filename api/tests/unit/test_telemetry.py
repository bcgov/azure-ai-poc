"""Unit tests for telemetry module."""

import os
from unittest.mock import MagicMock, patch

from opentelemetry.sdk.trace import TracerProvider

from app.core.telemetry import (
    _configure_span_processors,
    _get_otlp_headers,
    _instrument_libraries,
    setup_telemetry,
)


class TestTelemetry:
    """Tests for telemetry module."""

    @patch("app.core.telemetry.trace.set_tracer_provider")
    @patch("app.core.telemetry._instrument_libraries")
    @patch("app.core.telemetry._configure_span_processors")
    def test_setup_telemetry(self, mock_configure_processors, mock_instrument, mock_set_provider):
        """Test setup_telemetry configures everything correctly."""
        setup_telemetry()

        # Verify tracer provider was set
        mock_set_provider.assert_called_once()

        # Verify processors were configured
        mock_configure_processors.assert_called_once()

        # Verify libraries were instrumented
        mock_instrument.assert_called_once()

    @patch("app.core.telemetry.settings")
    def test_configure_span_processors_development(self, mock_settings):
        """Test span processor configuration in development."""
        mock_settings.ENVIRONMENT = "development"

        tracer_provider = TracerProvider()

        with patch.object(tracer_provider, "add_span_processor") as mock_add:
            _configure_span_processors(tracer_provider)

            # Should add console exporter in development
            assert mock_add.call_count >= 1

    @patch("app.core.telemetry.settings")
    @patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"})
    def test_configure_span_processors_with_otlp(self, mock_settings):
        """Test span processor configuration with OTLP endpoint."""
        mock_settings.ENVIRONMENT = "production"

        tracer_provider = TracerProvider()

        with patch.object(tracer_provider, "add_span_processor") as mock_add:
            _configure_span_processors(tracer_provider)

            # Should add OTLP exporter when endpoint is configured
            assert mock_add.call_count >= 1

    def test_get_otlp_headers_with_no_env_var(self):
        """Test _get_otlp_headers when no env var is set."""
        with patch.dict(os.environ, {}, clear=True):
            headers = _get_otlp_headers()

            assert headers is None

    def test_get_otlp_headers_with_single_header(self):
        """Test _get_otlp_headers with single header."""
        with patch.dict(
            os.environ, {"OTEL_EXPORTER_OTLP_HEADERS": "api-key=secret123"}, clear=True
        ):
            headers = _get_otlp_headers()

            assert headers == {"api-key": "secret123"}

    def test_get_otlp_headers_with_multiple_headers(self):
        """Test _get_otlp_headers with multiple headers."""
        with patch.dict(
            os.environ,
            {"OTEL_EXPORTER_OTLP_HEADERS": "api-key=secret123,x-tenant=tenant1"},
            clear=True,
        ):
            headers = _get_otlp_headers()

            assert headers == {"api-key": "secret123", "x-tenant": "tenant1"}

    def test_get_otlp_headers_with_spaces(self):
        """Test _get_otlp_headers handles spaces correctly."""
        with patch.dict(
            os.environ,
            {"OTEL_EXPORTER_OTLP_HEADERS": "api-key = secret123 , x-tenant = tenant1"},
            clear=True,
        ):
            headers = _get_otlp_headers()

            assert headers == {"api-key": "secret123", "x-tenant": "tenant1"}

    def test_get_otlp_headers_ignores_invalid_entries(self):
        """Test _get_otlp_headers ignores entries without '='."""
        with patch.dict(
            os.environ,
            {"OTEL_EXPORTER_OTLP_HEADERS": "api-key=secret123,invalid,x-tenant=tenant1"},
            clear=True,
        ):
            headers = _get_otlp_headers()

            # Invalid entry should be ignored
            assert headers == {"api-key": "secret123", "x-tenant": "tenant1"}

    @patch("app.core.telemetry.HTTPXClientInstrumentor")
    def test_instrument_libraries(self, mock_httpx_instrumentor):
        """Test _instrument_libraries instruments HTTP clients."""
        mock_instrumentor_instance = MagicMock()
        mock_httpx_instrumentor.return_value = mock_instrumentor_instance

        _instrument_libraries()

        # Verify HTTPXClientInstrumentor was called
        mock_httpx_instrumentor.assert_called_once()
        mock_instrumentor_instance.instrument.assert_called_once()

    @patch("app.core.telemetry.settings")
    @patch.dict(os.environ, {}, clear=True)
    def test_configure_span_processors_no_otlp(self, mock_settings):
        """Test span processor configuration without OTLP endpoint."""
        mock_settings.ENVIRONMENT = "production"

        tracer_provider = TracerProvider()

        with patch.object(tracer_provider, "add_span_processor") as mock_add:
            _configure_span_processors(tracer_provider)

            # Should not add any processors in production without OTLP
            assert mock_add.call_count == 0
