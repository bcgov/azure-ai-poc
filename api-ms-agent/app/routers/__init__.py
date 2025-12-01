"""Main API router."""

from fastapi import APIRouter

from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.research import router as research_router
from app.routers.workflow_research import router as workflow_research_router

api_router = APIRouter()
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(research_router, prefix="/research", tags=["research"])
api_router.include_router(
    workflow_research_router, prefix="/workflow-research", tags=["workflow_research"]
)
