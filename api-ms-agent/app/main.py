"""
FastAPI application for MS Agent API.

A simple chat agent API using Microsoft Agent Framework and Azure OpenAI.
"""

import inspect
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psutil
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth.errors import AuthError
from app.config import settings
from app.devui import DevUIServer, start_devui_async
from app.http_client import close_http_client
from app.logger import get_logger, setup_logging
from app.middleware.access_log_middleware import AccessLogMiddleware
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.security_middleware import SecurityMiddleware
from app.routers import api_router
from app.services import (
    get_azure_search_service,
    get_chat_agent_service,
    get_cosmos_db_service,
    get_embedding_service,
)
from app.services.openai_clients import get_embedding_client, shutdown_clients
from app.services.orchestrator_agent import get_orchestrator_agent, shutdown_orchestrator
from app.services.research_agent import get_deep_research_service
from app.services.workflow_research_agent import get_workflow_research_service


def _format_bytes(num: float) -> str:
    """Return a human-friendly string for a byte count."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.2f} {unit}"
        num /= 1024
    return f"{num:.2f} PB"


def _collect_process_metrics() -> dict:
    """Gather CPU and memory metrics for the current Python process only."""
    proc = psutil.Process()

    cpu_percent = proc.cpu_percent(interval=0.05)
    mem_info = proc.memory_info()

    data = {
        "pid": proc.pid,
        "name": proc.name(),
        "cmdline": proc.cmdline(),
        "cpu_percent": cpu_percent,
        "num_threads": proc.num_threads(),
        "memory": {
            "rss_bytes": mem_info.rss,
            "rss_human": _format_bytes(mem_info.rss),
            "vms_bytes": mem_info.vms,
            "vms_human": _format_bytes(mem_info.vms),
            "private_bytes": getattr(mem_info, "private", None),
            "private_human": _format_bytes(mem_info.private)
            if hasattr(mem_info, "private")
            else None,
            "memory_percent": proc.memory_percent(),
        },
        "open_files": len(proc.open_files()),
        "num_handles": proc.num_handles() if hasattr(proc, "num_handles") else None,
    }

    return data


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown."""
    logger = get_logger(__name__)
    logger.info("Starting up API MS Agent")
    devui_server: DevUIServer | None = None

    async def _safe_init(name: str, func):
        """Run initializer safely and log warnings without failing startup."""
        try:
            result = func()
            if inspect.isawaitable(result):
                await result
            logger.info("service_initialized", service=name)
        except Exception as exc:  # noqa: BLE001 - we want to catch all during startup warmup
            logger.warning("service_init_failed", service=name, error=str(exc))

    # Startup: initialize core infrastructure services
    cosmos_service = get_cosmos_db_service()
    azure_search_service = get_azure_search_service()

    await _safe_init("cosmos_db", cosmos_service._initialize_client)
    await _safe_init("azure_search", azure_search_service._initialize_client)

    # Initialize Document Intelligence service (eagerly create client)
    from app.services.document_intelligence_service import (
        get_document_intelligence_service,
    )

    doc_intel_service = get_document_intelligence_service()
    await _safe_init("document_intelligence", doc_intel_service._get_client)

    # Warm up centralized OpenAI clients (singleton pattern - initializes once)
    await _safe_init("embedding_client", get_embedding_client)

    # Initialize agent services (they use centralized clients internally)
    chat_service = get_chat_agent_service()
    orchestrator_service = get_orchestrator_agent()

    await _safe_init("chat_agent", chat_service._get_agent)
    await _safe_init("orchestrator_agent", orchestrator_service._get_agent)

    # Initialize research services (they share centralized OpenAI clients)
    research_service = get_deep_research_service()
    workflow_research_service = get_workflow_research_service()
    embedding_service = get_embedding_service()

    logger.info("All services initialized successfully")

    if settings.devui_enabled:
        devui_server = start_devui_async(
            host=settings.devui_host,
            port=settings.devui_port,
            auto_open=settings.devui_auto_open,
            mode=settings.devui_mode,
            cors_origins=["*"],
        )

    yield

    # Shutdown: cleanup in reverse order of initialization
    logger.info("Shutting down API MS Agent")

    # Close agent services first
    await chat_service.close()
    await research_service.close()
    await workflow_research_service.close()
    await shutdown_orchestrator()

    # Close embedding service
    await embedding_service.close()

    # Close Document Intelligence service
    await doc_intel_service.close()

    # Close infrastructure services
    await cosmos_service.dispose()
    await azure_search_service.dispose()

    # Close shared HTTP client
    await close_http_client()

    # Close all centralized Azure OpenAI clients
    await shutdown_clients()

    if devui_server:
        devui_server.stop()

    logger.info("API MS Agent shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        description="Agentic AI API using Microsoft Agent Framework",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(AuthError)
    async def _auth_error_handler(_request: Request, exc: AuthError):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_payload(),
            headers=exc.headers,
        )

    # Access log middleware - logs requests with timing and content length
    # Note: This must be added first so it wraps all other middleware
    app.add_middleware(AccessLogMiddleware)

    # Security middleware (equivalent to helmet)
    app.add_middleware(SecurityMiddleware)

    # Authentication middleware - validates JWT for all non-excluded routes
    # Note: Middleware executes in reverse order, so this runs before SecurityMiddleware
    app.add_middleware(AuthMiddleware)

    # Root endpoints (excluded from auth)
    @app.get("/")
    async def root():
        """Root endpoint - service status."""
        return {
            "status": "running",
            "service": settings.app_name,
            "version": "0.1.0",
            "process": _collect_process_metrics(),
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "process": _collect_process_metrics()}

    @app.get("/api/health")
    async def api_health():
        """Health check endpoint."""
        return {"status": "healthy", "process": _collect_process_metrics()}

    # Include all routers with API prefix and versioning
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
