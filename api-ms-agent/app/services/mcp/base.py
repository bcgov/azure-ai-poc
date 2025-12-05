"""
MCP Base Classes.

This module provides base classes and data structures for implementing
MCP (Model Context Protocol) tool wrappers for external APIs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

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
    """

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)

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
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.headers,
            )
        return self._client

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
        response = await client.request(
            method=method,
            url=path,
            params=params,
            json=json_data,
        )
        response.raise_for_status()
        return response.json()

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
        # Build full URL with params
        full_url = f"{self.base_url}{endpoint}"
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in params.items())
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
