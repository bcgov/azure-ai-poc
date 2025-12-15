"""
MCP Base Classes.

This module provides base classes and data structures for implementing
MCP (Model Context Protocol) tool wrappers for external APIs.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlencode

import httpx
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as jsonschema_validate

from app.http_client import cached_get_json, create_scoped_client
from app.logger import get_logger

logger = get_logger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level for MCP tool results."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class MCPToolResult:
    """
    Result from an MCP tool execution.

    Attributes:
        success: Whether the tool executed successfully
        data: The result data from the tool
        error: Error message if execution failed
        source_info: Source attribution for the data
    """

    success: bool
    data: Any = None
    error: str | None = None
    source_info: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "data": self.data,
        }
        if self.error:
            result["error"] = self.error
        if self.source_info:
            result["source_info"] = self.source_info
        return result


@dataclass
class MCPTool:
    """
    Definition of an MCP tool.

    Attributes:
        name: Unique tool name
        description: Human-readable description
        input_schema: JSON Schema for tool inputs
        _compiled_validator: Pre-compiled JSON schema validator (performance optimization)
    """

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    _compiled_validator: Any = field(default=None, repr=False)

    def __post_init__(self):
        """Pre-compile the JSON schema validator for performance."""
        if self.input_schema:
            try:
                from jsonschema import Draft7Validator

                self._compiled_validator = Draft7Validator(self.input_schema)
            except Exception:
                pass  # Fall back to dynamic validation

    def to_dict(self) -> dict[str, Any]:
        """Convert to MCP tool specification format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class MCPWrapper(ABC):
    """
    Abstract base class for MCP API wrappers.

    Provides a standardized interface for wrapping external APIs
    as MCP tools that can be used by AI agents.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        max_connections: int = 10,
        max_keepalive_connections: int = 5,
    ):
        """
        Initialize the MCP wrapper.

        Args:
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            headers: Optional headers for all requests
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._client_limits = httpx.Limits(
            max_connections=max_connections, max_keepalive_connections=max_keepalive_connections
        )

    @property
    def name(self) -> str:
        """Return the name of this MCP wrapper."""
        return self.__class__.__name__.replace("MCP", "").lower()

    @property
    @abstractmethod
    def tools(self) -> list[MCPTool]:
        """Return list of available MCP tools."""
        ...

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """
        Execute an MCP tool.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments for the tool

        Returns:
            MCPToolResult with the execution result
        """
        ...

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client using centralized connection pooling."""
        if self._client is None or getattr(self._client, "is_closed", False):
            self._client = create_scoped_client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.headers,
                max_connections=self._client_limits.max_connections,
                max_keepalive_connections=self._client_limits.max_keepalive_connections,
            )
        return self._client

    def _get_tool_by_name(self, name: str) -> MCPTool | None:
        """Return the MCPTool for a name if declared by the wrapper."""
        for t in self.tools:
            if t.name == name:
                return t
        return None

    def validate_arguments(
        self, tool: MCPTool, arguments: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """Validate arguments against a tool's `input_schema` using jsonschema.

        Uses pre-compiled validator when available for better performance.

        Returns:
            (True, None) if validation passes, otherwise (False, error_message)
        """
        if not tool or not getattr(tool, "input_schema", None):
            return True, None

        try:
            # Use pre-compiled validator if available (faster)
            if tool._compiled_validator:
                errors = list(tool._compiled_validator.iter_errors(arguments or {}))
                if errors:
                    return False, str(errors[0])
                return True, None

            # Fall back to dynamic validation
            jsonschema_validate(instance=arguments or {}, schema=tool.input_schema)
            return True, None
        except JsonSchemaValidationError as e:
            return False, str(e)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            params: Query parameters
            json_data: JSON body for POST requests

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPError: If the request fails
        """
        client = await self._get_client()

        if method.upper() == "GET" and json_data is None:
            # Use shared GET caching for idempotent tool calls.
            return await cached_get_json(client, path, params=params)

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json_data,
                )
                # Retry on 5xx and 429
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait = (
                        int(retry_after)
                        if retry_after and retry_after.isdigit()
                        else self._backoff_factor * (2 ** (attempt - 1))
                    )
                    await asyncio.sleep(wait)
                    last_exc = httpx.HTTPStatusError(
                        "Too many requests", request=response.request, response=response
                    )
                    continue
                if 500 <= response.status_code < 600:
                    await asyncio.sleep(self._backoff_factor * (2 ** (attempt - 1)))
                    last_exc = httpx.HTTPStatusError(
                        "Server error", request=response.request, response=response
                    )
                    continue

                response.raise_for_status()

                # Try to parse JSON defensively
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type or "json" in content_type:
                    try:
                        return response.json()
                    except Exception:
                        # Fallback to text as a dict with message
                        return {"raw_text": response.text}
                # If not JSON, return text as dict
                return {"raw_text": response.text}
            except httpx.HTTPError as e:
                last_exc = e
                # Last attempt -> re-raise
                if attempt == self._max_retries:
                    raise
                await asyncio.sleep(self._backoff_factor * (2 ** (attempt - 1)))
        if last_exc:
            raise last_exc

    def _build_source_info(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        description: str = "",
        confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Build standardized source information for citations.

        Args:
            endpoint: API endpoint used
            params: Query parameters used
            description: Human-readable description
            confidence: Confidence level of the result
            extra: Additional metadata

        Returns:
            Source info dictionary
        """
        # Build full URL with params (safely encoded)
        full_url = f"{self.base_url}{endpoint}"
        if params:
            param_str = urlencode(params, doseq=True)
            full_url = f"{full_url}?{param_str}"

        source = {
            "source_type": "api",
            "description": description,
            "confidence": confidence.value,
            "url": full_url,
            "api_endpoint": endpoint,
        }

        if params:
            source["api_params"] = params

        if extra:
            source.update(extra)

        return source

    async def health_check(self) -> bool:
        """
        Check if the API is healthy.

        Returns:
            True if API is reachable and responding
        """
        try:
            client = await self._get_client()
            # Most APIs respond to a simple GET on their base
            response = await client.get("/")
            return response.status_code < 500
        except Exception as e:
            logger.warning(f"{self.name} health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(base_url={self.base_url!r})"
