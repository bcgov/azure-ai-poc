"""Main API router."""

from fastapi import APIRouter

# Import all routers
from app.routers.chat import router as chat_router
from app.routers.document import router as document_router
from app.routers.health import router as health_router
from app.routers.metrics import router as metrics_router

# Create main API router
api_router = APIRouter()

# Include all routers
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(document_router, prefix="/documents", tags=["documents"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
