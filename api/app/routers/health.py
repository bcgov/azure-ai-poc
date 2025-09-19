"""
Health check router for monitoring application and service health.

This router provides health check endpoints for:
- Basic application health
- Azure service health (Cosmos DB, OpenAI)
- Comprehensive health status reporting
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.services.cosmos_db_service import get_cosmos_db_service


class HealthStatus:
    """Health status constants."""

    UP = "up"
    DOWN = "down"


router = APIRouter(tags=["health"])


@router.get(
    "/",
    summary="Basic health check",
    description="Basic health check endpoint to verify the application is running",
    responses={
        200: {
            "description": "Application is healthy",
            "content": {
                "application/json": {
                    "example": {"status": "up", "timestamp": "2024-01-15T10:30:00Z"}
                }
            },
        }
    },
)
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint."""
    from datetime import UTC, datetime

    return {
        "status": HealthStatus.UP,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "service": "azure-ai-poc-api",
    }


@router.get(
    "/ready",
    summary="Readiness check",
    description="Readiness check that verifies all critical services are available",
    responses={
        200: {
            "description": "Application is ready",
            "content": {
                "application/json": {
                    "example": {
                        "status": "up",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "checks": {"cosmosdb": {"status": "up", "responseTime": "15ms"}},
                    }
                }
            },
        },
        503: {
            "description": "Application is not ready - some services are down",
            "content": {
                "application/json": {
                    "example": {
                        "status": "down",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "checks": {"cosmosdb": {"status": "down", "error": "Connection failed"}},
                    }
                }
            },
        },
    },
)
async def readiness_check(
    cosmos_db_service=Depends(get_cosmos_db_service),
) -> dict[str, Any]:
    """Readiness check that verifies all critical services are available."""
    import time
    from datetime import UTC, datetime

    checks = {}
    overall_status = HealthStatus.UP

    try:
        # Check Cosmos DB health
        cosmos_health = await cosmos_db_service.health_check()
        checks["cosmosdb"] = cosmos_health

        if cosmos_health["status"] != HealthStatus.UP:
            overall_status = HealthStatus.DOWN

    except Exception as error:
        logging.error(f"Cosmos DB health check failed: {error}")
        checks["cosmosdb"] = {
            "status": HealthStatus.DOWN,
            "error": str(error),
            "timestamp": time.time(),
        }
        overall_status = HealthStatus.DOWN

    response = {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "checks": checks,
    }

    if overall_status == HealthStatus.DOWN:
        raise HTTPException(status_code=503, detail=response)

    return response


@router.get(
    "/live",
    summary="Liveness check",
    description="Liveness check to verify the application is alive (for Kubernetes)",
    responses={
        200: {
            "description": "Application is alive",
            "content": {
                "application/json": {
                    "example": {"status": "up", "timestamp": "2024-01-15T10:30:00Z"}
                }
            },
        }
    },
)
async def liveness_check() -> dict[str, Any]:
    """Liveness check to verify the application is alive."""
    from datetime import UTC, datetime

    return {
        "status": HealthStatus.UP,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "service": "azure-ai-poc-api",
    }
