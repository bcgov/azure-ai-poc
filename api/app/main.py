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
from app.core.logger import get_logger, setup_logging
from app.core.telemetry import instrument_fastapi_app, setup_telemetry
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.rate_limit_middleware import limiter
from app.middleware.security_middleware import SecurityMiddleware
from app.routers import api_router
from app.services.azure_openai_service import get_azure_openai_service
from app.services.cosmos_db_service import get_cosmos_db_service
from app.services.azure_search_service import get_azure_search_service

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info("Starting application initialization...")
    setup_logging()
    setup_telemetry()

    try:
        # Initialize Azure OpenAI service
        logger.info("Initializing Azure OpenAI service...")
        azure_openai_service = get_azure_openai_service()
        await azure_openai_service.initialize_clients()

        # Initialize Cosmos DB service
        logger.info("Initializing Cosmos DB service...")
        cosmos_db_service = get_cosmos_db_service()
        await cosmos_db_service.health_check()
        # initializing Azure AI Search service
        get_azure_search_service()
        logger.info("All services initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Starting application shutdown...")
    try:
        # Get services and cleanup if needed
        cosmos_db_service = get_cosmos_db_service()
        if hasattr(cosmos_db_service, "cleanup"):
            await cosmos_db_service.cleanup()

        azure_openai_service = get_azure_openai_service()
        if hasattr(azure_openai_service, "cleanup"):
            await azure_openai_service.cleanup()

        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


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

    # Backward compatibility: redirect legacy /docs to /api/docs if tests/reference expect it
    from fastapi.responses import RedirectResponse

    @app.get("/docs", include_in_schema=False)
    async def legacy_docs_redirect():  # pragma: no cover - simple redirect
        return RedirectResponse(url="/api/docs")

    return app


# Create the application instance
app = create_app()
