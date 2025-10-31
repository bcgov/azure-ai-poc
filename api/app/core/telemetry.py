"""OpenTelemetry configuration and instrumentation setup."""

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import settings


def setup_telemetry() -> None:
    """Setup OpenTelemetry tracing and instrumentation."""

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": "azure-ai-poc-api",
            "service.version": settings.API_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    )

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Configure span processors
    _configure_span_processors(tracer_provider)

    # Instrument libraries
    _instrument_libraries()


def _configure_span_processors(tracer_provider: TracerProvider) -> None:
    """Configure span processors for different environments."""

    # Always add console exporter for development
    if settings.ENVIRONMENT == "development":
        console_exporter = ConsoleSpanExporter()
        console_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(console_processor)

    # Add OTLP exporter if endpoint is configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=_get_otlp_headers(),
        )
        otlp_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(otlp_processor)


def _get_otlp_headers() -> dict[str, str] | None:
    """Get OTLP headers from environment variables."""
    headers_str = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    if not headers_str:
        return None

    headers = {}
    for header in headers_str.split(","):
        if "=" in header:
            key, value = header.split("=", 1)
            headers[key.strip()] = value.strip()

    return headers


def _instrument_libraries() -> None:
    """Instrument HTTP libraries for automatic tracing."""

    # Instrument HTTP clients
    HTTPXClientInstrumentor().instrument()
    # RequestsInstrumentor().instrument()  # Commented out until dependency is available


def instrument_fastapi_app(app) -> None:
    """Instrument FastAPI application for automatic request tracing."""
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health,metrics,docs,redoc,openapi.json",
        server_request_hook=_server_request_hook,
        client_request_hook=_client_request_hook,
    )


def _server_request_hook(span, scope: dict) -> None:
    """Custom server request hook to add additional span attributes."""
    if span and span.is_recording():
        # Add custom attributes
        path = scope.get("path", "")
        method = scope.get("method", "")

        span.set_attribute("http.route", path)
        span.set_attribute("http.method", method)

        # Add user information if available
        if "user" in scope.get("state", {}):
            user = scope["state"]["user"]
            if hasattr(user, "id"):
                span.set_attribute("user.id", str(user.id))
            if hasattr(user, "email"):
                span.set_attribute("user.email", user.email)


def _client_request_hook(span, request) -> None:
    """Custom client request hook to add additional span attributes."""
    if span and span.is_recording():
        # Add Azure service information
        if "openai" in str(request.url):
            span.set_attribute("azure.service", "openai")
        elif "cosmos" in str(request.url):
            span.set_attribute("azure.service", "cosmos")
        elif "documents.azure.com" in str(request.url):
            span.set_attribute("azure.service", "cosmos")


def get_tracer(name: str):
    """Get a tracer instance for manual instrumentation."""
    return trace.get_tracer(name)


# Export main functions
__all__ = ["setup_telemetry", "instrument_fastapi_app", "get_tracer"]
