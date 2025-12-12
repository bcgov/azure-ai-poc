"""Models router for exposing available AI models."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter()


class ModelInfo(BaseModel):
    """Information about an available AI model."""

    id: str
    deployment: str
    display_name: str
    description: str
    is_default: bool


class ModelsResponse(BaseModel):
    """Response containing available models."""

    models: list[ModelInfo]


@router.get("/", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """
    List available AI models.

    Returns the configured models that can be used for chat and research.
    This is the source of truth for frontend model selection dropdowns.
    """
    models = settings.get_available_models()
    return ModelsResponse(models=[ModelInfo(**m) for m in models])


@router.get("/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str) -> ModelInfo:
    """
    Get details for a specific model.

    Args:
        model_id: The model identifier (e.g., 'gpt-4o-mini', 'gpt-41-nano')

    Returns:
        Model information or 404 if not found.
    """
    from fastapi import HTTPException

    models = settings.get_available_models()
    for model in models:
        if model["id"] == model_id:
            return ModelInfo(**model)

    raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
