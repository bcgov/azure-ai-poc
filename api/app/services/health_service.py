"""Comprehensive health check service."""

import asyncio
import time
from enum import Enum
from typing import Any

from azure.cosmos import exceptions as cosmos_exceptions
from pydantic import BaseModel

from app.core.config import settings
from app.services.azure_openai_service import get_azure_openai_service
from app.services.cosmos_db_service import get_cosmos_db_service


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status for a single component."""

    name: str
    status: HealthStatus
    message: str
    response_time_ms: float | None = None
    details: dict[str, Any] | None = None


class SystemHealth(BaseModel):
    """Overall system health status."""

    status: HealthStatus
    timestamp: str
    version: str
    uptime_seconds: float
    components: list[ComponentHealth]
    summary: dict[str, int]


class HealthCheckService:
    """Service for performing comprehensive health checks."""

    def __init__(self):
        self.start_time = time.time()

    async def get_system_health(self, detailed: bool = False) -> SystemHealth:
        """Get comprehensive system health status."""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        uptime = time.time() - self.start_time

        # Run all health checks concurrently
        health_checks = [
            self._check_application_health(),
            self._check_cosmos_db_health(),
            self._check_azure_openai_health(),
        ]

        if detailed:
            health_checks.extend(
                [
                    self._check_memory_usage(),
                    self._check_disk_space(),
                ]
            )

        components = await asyncio.gather(*health_checks, return_exceptions=True)

        # Handle exceptions
        processed_components = []
        for component in components:
            if isinstance(component, Exception):
                processed_components.append(
                    ComponentHealth(
                        name="unknown",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Health check failed: {str(component)}",
                    )
                )
            else:
                processed_components.append(component)

        # Calculate overall status
        overall_status = self._calculate_overall_status(processed_components)

        # Create summary
        summary = {
            status.value: len([c for c in processed_components if c.status == status])
            for status in HealthStatus
        }

        return SystemHealth(
            status=overall_status,
            timestamp=timestamp,
            version=settings.API_VERSION,
            uptime_seconds=round(uptime, 2),
            components=processed_components,
            summary=summary,
        )

    async def _check_application_health(self) -> ComponentHealth:
        """Check basic application health."""
        start_time = time.time()

        try:
            # Basic application checks
            response_time = (time.time() - start_time) * 1000

            return ComponentHealth(
                name="application",
                status=HealthStatus.HEALTHY,
                message="Application is running normally",
                response_time_ms=round(response_time, 2),
                details={
                    "environment": settings.ENVIRONMENT,
                    "port": settings.PORT,
                },
            )
        except Exception as e:
            return ComponentHealth(
                name="application",
                status=HealthStatus.UNHEALTHY,
                message=f"Application health check failed: {str(e)}",
            )

    async def _check_cosmos_db_health(self) -> ComponentHealth:
        """Check Cosmos DB connectivity and health."""
        start_time = time.time()

        try:
            cosmos_service = get_cosmos_db_service()

            # Perform a lightweight health check query
            health_result = await cosmos_service.health_check()
            response_time = (time.time() - start_time) * 1000

            if health_result:
                return ComponentHealth(
                    name="cosmos_db",
                    status=HealthStatus.HEALTHY,
                    message="Cosmos DB is accessible and responding",
                    response_time_ms=round(response_time, 2),
                    details={
                        "endpoint": settings.COSMOS_DB_ENDPOINT,
                        "database": settings.COSMOS_DB_DATABASE_NAME,
                        "container": settings.COSMOS_DB_CONTAINER_NAME,
                    },
                )
            else:
                return ComponentHealth(
                    name="cosmos_db",
                    status=HealthStatus.DEGRADED,
                    message="Cosmos DB health check returned unexpected result",
                    response_time_ms=round(response_time, 2),
                )

        except cosmos_exceptions.CosmosHttpResponseError as e:
            return ComponentHealth(
                name="cosmos_db",
                status=HealthStatus.UNHEALTHY,
                message=f"Cosmos DB connection failed: {e.message}",
                details={"status_code": e.status_code},
            )
        except Exception as e:
            return ComponentHealth(
                name="cosmos_db",
                status=HealthStatus.UNHEALTHY,
                message=f"Cosmos DB health check failed: {str(e)}",
            )

    async def _check_azure_openai_health(self) -> ComponentHealth:
        """Check Azure OpenAI service health."""
        start_time = time.time()

        try:
            openai_service = get_azure_openai_service()

            # Perform a minimal API call to check connectivity
            # Using a very short completion request
            test_response = await openai_service.chat_completion(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                temperature=0,
            )

            response_time = (time.time() - start_time) * 1000

            if test_response and hasattr(test_response, "choices"):
                return ComponentHealth(
                    name="azure_openai",
                    status=HealthStatus.HEALTHY,
                    message="Azure OpenAI is accessible and responding",
                    response_time_ms=round(response_time, 2),
                    details={
                        "llm_endpoint": settings.AZURE_OPENAI_LLM_ENDPOINT,
                        "embedding_endpoint": settings.AZURE_OPENAI_EMBEDDING_ENDPOINT,
                        "deployment": settings.AZURE_OPENAI_LLM_DEPLOYMENT_NAME,
                    },
                )
            else:
                return ComponentHealth(
                    name="azure_openai",
                    status=HealthStatus.DEGRADED,
                    message="Azure OpenAI responded but with unexpected format",
                )

        except Exception as e:
            return ComponentHealth(
                name="azure_openai",
                status=HealthStatus.UNHEALTHY,
                message=f"Azure OpenAI health check failed: {str(e)}",
            )

    async def _check_memory_usage(self) -> ComponentHealth:
        """Check system memory usage."""
        try:
            import psutil

            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            if memory_percent < 80:
                status = HealthStatus.HEALTHY
                message = f"Memory usage is normal ({memory_percent:.1f}%)"
            elif memory_percent < 90:
                status = HealthStatus.DEGRADED
                message = f"Memory usage is high ({memory_percent:.1f}%)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Memory usage is critical ({memory_percent:.1f}%)"

            return ComponentHealth(
                name="memory",
                status=status,
                message=message,
                details={
                    "used_percent": round(memory_percent, 1),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                },
            )
        except ImportError:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.DEGRADED,
                message="Memory monitoring not available (psutil not installed)",
            )
        except Exception as e:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check failed: {str(e)}",
            )

    async def _check_disk_space(self) -> ComponentHealth:
        """Check disk space usage."""
        try:
            import psutil

            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100

            if disk_percent < 80:
                status = HealthStatus.HEALTHY
                message = f"Disk usage is normal ({disk_percent:.1f}%)"
            elif disk_percent < 90:
                status = HealthStatus.DEGRADED
                message = f"Disk usage is high ({disk_percent:.1f}%)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Disk usage is critical ({disk_percent:.1f}%)"

            return ComponentHealth(
                name="disk",
                status=status,
                message=message,
                details={
                    "used_percent": round(disk_percent, 1),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                },
            )
        except ImportError:
            return ComponentHealth(
                name="disk",
                status=HealthStatus.DEGRADED,
                message="Disk monitoring not available (psutil not installed)",
            )
        except Exception as e:
            return ComponentHealth(
                name="disk",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk check failed: {str(e)}",
            )

    def _calculate_overall_status(
        self, components: list[ComponentHealth]
    ) -> HealthStatus:
        """Calculate overall system status based on component statuses."""
        if not components:
            return HealthStatus.UNHEALTHY

        statuses = [component.status for component in components]

        # If any component is unhealthy, system is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY

        # If any component is degraded, system is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED

        # All components healthy
        return HealthStatus.HEALTHY


# Global health check service instance
health_service = HealthCheckService()


def get_health_service() -> HealthCheckService:
    """Get the health check service instance."""
    return health_service
