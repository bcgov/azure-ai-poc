"""
FastAPI application for MS Agent API.

A simple chat agent API using Microsoft Agent Framework and Azure OpenAI.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logger import get_logger, setup_logging
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.security_middleware import SecurityMiddleware
from app.routers import api_router
from app.services import get_chat_agent_service, get_cosmos_db_service, get_embedding_service
from app.services.orchestrator_agent import shutdown_orchestrator
from app.services.research_agent import get_deep_research_service
from app.services.workflow_research_agent import get_workflow_research_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown."""
    logger = get_logger(__name__)
    logger.info("Starting up API MS Agent")

    # Startup: initialize services
    yield

    # Shutdown: cleanup
    logger.info("Shutting down API MS Agent")
    chat_service = get_chat_agent_service()
    await chat_service.close()
    research_service = get_deep_research_service()
    await research_service.close()
    workflow_research_service = get_workflow_research_service()
    await workflow_research_service.close()
    await shutdown_orchestrator()
    embedding_service = get_embedding_service()
    await embedding_service.close()
    cosmos_service = get_cosmos_db_service()
    cosmos_service.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        description="Agentic AI API using Microsoft Agent Framework",
        version="0.1.0",
        lifespan=lifespan,
    )
    # Security middleware (equivalent to helmet)
    app.add_middleware(SecurityMiddleware)

    # Authentication middleware - validates JWT for all non-excluded routes
    # Note: Middleware executes in reverse order, so this runs before SecurityMiddleware
    app.add_middleware(AuthMiddleware)

    # Root endpoints (excluded from auth)
    @app.get("/")
    async def root():
        """Root endpoint - service status."""
        return {"status": "running", "service": settings.app_name, "version": "0.1.0"}

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    # Include all routers with API prefix and versioning
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
