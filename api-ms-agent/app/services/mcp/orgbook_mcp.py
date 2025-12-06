"""
BC OrgBook MCP Wrapper.

Provides MCP tools for querying BC OrgBook API for business/organization information.
API Documentation: https://orgbook.gov.bc.ca/api/
"""

from typing import Any

from app.config import settings
from app.logger import get_logger
from app.services.mcp.base import ConfidenceLevel, MCPTool, MCPToolResult, MCPWrapper

logger = get_logger(__name__)

# OrgBook API Base URL
ORGBOOK_BASE_URL = "https://orgbook.gov.bc.ca/api/v4"


class OrgBookMCP(MCPWrapper):
    """
    MCP wrapper for BC OrgBook API.

    Provides tools for:
    - Searching for organizations by name or registration number
    - Getting detailed organization information
    - Checking organization credentials and status
    """

    def __init__(self, base_url: str | None = None):
        """Initialize the OrgBook MCP wrapper."""
        configured_base = (
            base_url or getattr(settings, "orgbook_base_url", None) or ORGBOOK_BASE_URL
        )
        super().__init__(base_url=configured_base)
        logger.info("OrgBookMCP initialized")

    @property
    def tools(self) -> list[MCPTool]:
        """Return list of available OrgBook MCP tools."""
        return [
            MCPTool(
                name="orgbook_search",
                description=(
                    "Search for BC registered businesses and organizations by name or "
                    "registration number. Returns matching organizations with basic info."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Business name or registration number to search for",
                        },
                        "inactive": {
                            "type": "boolean",
                            "description": "Include inactive organizations",
                            "default": False,
                        },
                        "revoked": {
                            "type": "boolean",
                            "description": "Include revoked credentials",
                            "default": False,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["query"],
                },
            ),
            MCPTool(
                name="orgbook_get_topic",
                description=(
                    "Get detailed information about a specific organization by topic ID. "
                    "Returns full credentials, addresses, and registration details."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic_id": {
                            "type": "integer",
                            "description": "The topic ID of the organization",
                        },
                    },
                    "required": ["topic_id"],
                },
            ),
            MCPTool(
                name="orgbook_get_credentials",
                description=(
                    "Get all credentials for a specific organization. "
                    "Returns active registrations, licenses, and permits."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic_id": {
                            "type": "integer",
                            "description": "The topic ID of the organization",
                        },
                    },
                    "required": ["topic_id"],
                },
            ),
        ]

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Execute an OrgBook MCP tool."""
        logger.info(f"[OrgBookMCP] Executing tool: {tool_name}")

        # Validate arguments according to declared schema
        tool = self._get_tool_by_name(tool_name)
        if tool:
            ok, err = self.validate_arguments(tool, arguments)
            if not ok:
                return MCPToolResult(success=False, error=f"Invalid arguments: {err}")

        try:
            if tool_name == "orgbook_search":
                return await self._search_organizations(arguments)
            elif tool_name == "orgbook_get_topic":
                return await self._get_topic(arguments)
            elif tool_name == "orgbook_get_credentials":
                return await self._get_credentials(arguments)
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Unknown tool: {tool_name}",
                )
        except Exception as e:
            logger.error(f"[OrgBookMCP] Error executing {tool_name}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
            )

    async def _search_organizations(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Search for organizations by name or registration number."""
        query = arguments.get("query", "")
        inactive = arguments.get("inactive", False)
        revoked = arguments.get("revoked", False)
        limit = min(arguments.get("limit", 10), 50)

        params = {
            "q": query,
            "inactive": str(inactive).lower(),
            "revoked": str(revoked).lower(),
        }

        endpoint = "/search/topic"
        data = await self._request("GET", endpoint, params=params)

        # Process results
        results = []
        for item in data.get("results", [])[:limit]:
            org_info = {
                "topic_id": item.get("id"),
                "source_id": item.get("source_id"),
                "type": item.get("type"),
                "names": [n.get("text") for n in item.get("names", []) if n.get("text")],
                "addresses": [
                    {
                        "civic_address": addr.get("civic_address"),
                        "city": addr.get("city"),
                        "province": addr.get("province"),
                        "postal_code": addr.get("postal_code"),
                    }
                    for addr in item.get("addresses", [])
                ],
                "status": "active" if not item.get("inactive") else "inactive",
            }
            results.append(org_info)

        total_found = data.get("total", len(results))

        return MCPToolResult(
            success=True,
            data={
                "organizations": results,
                "total_found": total_found,
                "query": query,
            },
            source_info=self._build_source_info(
                endpoint=endpoint,
                params=params,
                description=(
                    f"BC OrgBook API - Search for '{query}' with filters: "
                    f"inactive={inactive}, revoked={revoked}. "
                    f"Found {total_found} total results, returning {len(results)}."
                ),
                confidence=ConfidenceLevel.HIGH,
            ),
        )

    async def _get_topic(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Get detailed topic information."""
        topic_id = arguments.get("topic_id")
        if not topic_id:
            return MCPToolResult(
                success=False,
                error="topic_id is required",
            )

        endpoint = f"/topic/{topic_id}"
        data = await self._request("GET", endpoint)

        return MCPToolResult(
            success=True,
            data=data,
            source_info=self._build_source_info(
                endpoint=endpoint,
                description=f"BC OrgBook API - Topic details for ID {topic_id}",
                confidence=ConfidenceLevel.HIGH,
            ),
        )

    async def _get_credentials(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Get credentials for an organization."""
        topic_id = arguments.get("topic_id")
        if not topic_id:
            return MCPToolResult(
                success=False,
                error="topic_id is required",
            )

        endpoint = f"/topic/{topic_id}/credential"
        data = await self._request("GET", endpoint)

        credentials = []
        for cred in data.get("results", []):
            credentials.append(
                {
                    "id": cred.get("id"),
                    "type": cred.get("credential_type", {}).get("description"),
                    "effective_date": cred.get("effective_date"),
                    "revoked": cred.get("revoked", False),
                    "inactive": cred.get("inactive", False),
                }
            )

        return MCPToolResult(
            success=True,
            data={
                "credentials": credentials,
                "total": len(credentials),
            },
            source_info=self._build_source_info(
                endpoint=endpoint,
                description=f"BC OrgBook API - Credentials for topic ID {topic_id}",
                confidence=ConfidenceLevel.HIGH,
            ),
        )

    async def health_check(self) -> bool:
        """Check if OrgBook API is healthy."""
        try:
            # Try a simple search to verify the API is working
            params = {"q": "test", "inactive": "false", "revoked": "false"}
            await self._request("GET", "/search/topic", params=params)
            return True
        except Exception as e:
            logger.warning(f"OrgBook health check failed: {e}")
            return False


# Singleton instance
_orgbook_instance: OrgBookMCP | None = None


def get_orgbook_mcp() -> OrgBookMCP:
    """Get or create the OrgBook MCP singleton."""
    global _orgbook_instance
    if _orgbook_instance is None:
        _orgbook_instance = OrgBookMCP()
    return _orgbook_instance
