"""Main API router."""

from fastapi import APIRouter

from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.metrics import router as metrics_router
from app.routers.models import router as models_router
from app.routers.orchestrator import router as orchestrator_router
from app.routers.research import router as research_router
from app.routers.speech import router as speech_router
from app.routers.workflow_research import router as workflow_research_router

api_router = APIRouter()
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(models_router, prefix="/models", tags=["models"])
api_router.include_router(orchestrator_router, prefix="/orchestrator", tags=["orchestrator"])
api_router.include_router(research_router, prefix="/research", tags=["research"])
api_router.include_router(speech_router, prefix="/speech", tags=["speech"])
api_router.include_router(metrics_router, prefix="/auth", tags=["auth"])
api_router.include_router(
    workflow_research_router, prefix="/workflow-research", tags=["workflow_research"]
)
