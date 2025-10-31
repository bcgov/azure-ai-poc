"""Main API router."""

from fastapi import APIRouter

# Import all routers
from app.routers.agent_lightning_analytics import (
    router as agent_lightning_analytics_router,
)
from app.routers.agent_lightning_multi_agent import (
    router as agent_lightning_multi_agent_router,
)
from app.routers.agent_lightning_observability import (
    router as agent_lightning_router,
)
from app.routers.agent_metrics import router as agent_metrics_router
from app.routers.chat import router as chat_router
from app.routers.document import router as document_router
from app.routers.health import router as health_router
from app.routers.metrics import router as metrics_router
from app.routers.tenants import router as tenants_router

# Create main API router
api_router = APIRouter()

# Include all routers
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(document_router, prefix="/documents", tags=["documents"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
api_router.include_router(tenants_router, tags=["tenants"])
api_router.include_router(agent_metrics_router)
api_router.include_router(
    agent_lightning_router, prefix="/agent-lightning", tags=["agent-lightning"]
)
api_router.include_router(
    agent_lightning_analytics_router,
    prefix="/agent-lightning-analytics",
    tags=["agent-lightning-analytics"],
)
api_router.include_router(
    agent_lightning_multi_agent_router,
    tags=["agent-lightning-multi-agent"],
)
