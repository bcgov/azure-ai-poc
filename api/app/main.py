"""FastAPI application bootstrap and configuration."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logger import setup_logging
from app.core.telemetry import instrument_fastapi_app, setup_telemetry
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.rate_limit_middleware import limiter
from app.middleware.security_middleware import SecurityMiddleware
from app.routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    setup_logging()
    setup_telemetry()

    # Add any startup tasks here (database connections, etc.)

    yield

    # Shutdown
    # Add any cleanup tasks here


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Azure AI POC API",
        description=(
            "API for Azure AI POC with document management and chat functionality.\n\n"
            f"Rate Limiting: This API implements rate limiting to ensure fair usage. "
            f"Default limits: {settings.RATE_LIMIT_MAX_REQUESTS} requests per "
            f"{settings.RATE_LIMIT_TTL // 1000} seconds.\n"
            "Health check endpoints are excluded from rate limiting."
        ),
        version=os.getenv("IMAGE_TAG", "latest"),
        openapi_tags=[
            {"name": "app", "description": "Basic application endpoints"},
            {"name": "documents", "description": "Document management endpoints"},
            {"name": "chat", "description": "Chat functionality endpoints"},
            {
                "name": "health",
                "description": "Health check endpoints (no rate limiting)",
            },
            {"name": "mcp", "description": "Model Context Protocol endpoints"},
            {"name": "metrics", "description": "Prometheus metrics endpoints"},
        ],
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Add SlowAPI rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Security middleware (equivalent to helmet)
    app.add_middleware(SecurityMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware (trust proxy)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

    # Metrics middleware
    app.add_middleware(MetricsMiddleware)

    # Logging middleware
    app.add_middleware(LoggingMiddleware)

    # OpenTelemetry instrumentation
    instrument_fastapi_app(app)

    # Include all routers with API prefix and versioning
    app.include_router(api_router, prefix="/api/v1")

    return app


# Create the application instance
app = create_app()
