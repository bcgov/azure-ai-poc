"""Observability endpoints.

Currently exposes auth-specific metrics in Prometheus text format.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.observability.auth_metrics import get_auth_metrics

router = APIRouter()


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Auth metrics (Prometheus)",
)
async def auth_metrics() -> PlainTextResponse:
    metrics_text = get_auth_metrics().render_prometheus()
    # Prometheus text format.
    return PlainTextResponse(content=metrics_text, media_type="text/plain; version=0.0.4")
