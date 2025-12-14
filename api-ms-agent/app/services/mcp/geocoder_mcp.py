"""
BC Geocoder MCP Wrapper.

Provides MCP tools for querying BC Geocoder API for address/location information.
API Documentation: https://www2.gov.bc.ca/gov/content?id=118DD57CD9674D57BDBD511C2E78DC0D
"""

from typing import Any

from app.config import settings
from app.logger import get_logger
from app.services.mcp.base import ConfidenceLevel, MCPTool, MCPToolResult, MCPWrapper

logger = get_logger(__name__)

# Geocoder API Base URL
GEOCODER_BASE_URL = "https://geocoder.api.gov.bc.ca"


class GeocoderMCP(MCPWrapper):
    """
    MCP wrapper for BC Geocoder API.

    Provides tools for:
    - Geocoding addresses to coordinates
    - Searching for occupants at addresses
    - Finding nearest sites to coordinates
    - Reverse geocoding from coordinates
    """

    def __init__(self, base_url: str | None = None):
        """Initialize the Geocoder MCP wrapper."""
        configured_base = (
            base_url or getattr(settings, "geocoder_base_url", None) or GEOCODER_BASE_URL
        )
        super().__init__(base_url=configured_base)
        logger.info("GeocoderMCP initialized")

    @property
    def tools(self) -> list[MCPTool]:
        """Return list of available Geocoder MCP tools."""
        return [
            MCPTool(
                name="geocoder_geocode",
                description=(
                    "Convert a BC address to geographic coordinates. "
                    "Returns matching addresses with lat/long coordinates."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": (
                                "The address to geocode (e.g., '1234 Main St, Vancouver BC')"
                            ),
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                        },
                    },
                    "required": ["address"],
                },
            ),
            MCPTool(
                name="geocoder_occupants",
                description=(
                    "Search for occupants (businesses, services) at BC addresses. "
                    "Returns occupant names and their addresses."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Occupant name or address to search for",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["query"],
                },
            ),
            MCPTool(
                name="geocoder_nearest",
                description=(
                    "Find the nearest site to given coordinates in BC. "
                    "Useful for reverse geocoding or finding nearby locations."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "longitude": {
                            "type": "number",
                            "description": "Longitude coordinate",
                        },
                        "latitude": {
                            "type": "number",
                            "description": "Latitude coordinate",
                        },
                        "max_distance": {
                            "type": "integer",
                            "description": "Maximum distance in meters",
                            "default": 1000,
                        },
                    },
                    "required": ["longitude", "latitude"],
                },
            ),
            MCPTool(
                name="geocoder_intersections",
                description=(
                    "Find street intersections in BC. "
                    "Returns intersection locations and coordinates."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "intersection": {
                            "type": "string",
                            "description": (
                                "Intersection to search (e.g., 'Main St and Broadway, Vancouver')"
                            ),
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 5,
                        },
                    },
                    "required": ["intersection"],
                },
            ),
        ]

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Execute a Geocoder MCP tool."""
        logger.info(f"[GeocoderMCP] Executing tool: {tool_name}")
        # Validate arguments according to declared tool schema
        tool = self._get_tool_by_name(tool_name)
        if tool:
            ok, err = self.validate_arguments(tool, arguments)
            if not ok:
                return MCPToolResult(success=False, error=f"Invalid arguments: {err}")
        try:
            if tool_name == "geocoder_geocode":
                return await self._geocode_address(arguments)
            elif tool_name == "geocoder_occupants":
                return await self._search_occupants(arguments)
            elif tool_name == "geocoder_nearest":
                return await self._find_nearest(arguments)
            elif tool_name == "geocoder_intersections":
                return await self._search_intersections(arguments)
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Unknown tool: {tool_name}",
                )
        except Exception as e:
            logger.error(f"[GeocoderMCP] Error executing {tool_name}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
            )

    async def _geocode_address(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Geocode an address to coordinates."""
        address = arguments.get("address", "")
        max_results = min(arguments.get("max_results", 5), 20)

        params = {
            "addressString": address,
            "maxResults": max_results,
            "outputSRS": 4326,
        }

        endpoint = "/addresses.json"
        data = await self._request("GET", endpoint, params=params)

        results = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [])

            results.append(
                {
                    "full_address": props.get("fullAddress"),
                    "score": props.get("score"),
                    "match_precision": props.get("matchPrecision"),
                    "locality": props.get("localityName"),
                    "province": props.get("provinceCode"),
                    "coordinates": {
                        "longitude": coords[0] if len(coords) > 0 else None,
                        "latitude": coords[1] if len(coords) > 1 else None,
                    },
                }
            )

        return MCPToolResult(
            success=True,
            data={
                "addresses": results,
                "count": len(results),
                "query": address,
            },
            source_info=self._build_source_info(
                endpoint=endpoint,
                params=params,
                description=(
                    f"BC Geocoder API - Address lookup for '{address}'. "
                    f"Found {len(results)} matching addresses."
                ),
                confidence=ConfidenceLevel.HIGH,
                extra={
                    "documentation": "https://www2.gov.bc.ca/gov/content?id=118DD57CD9674D57BDBD511C2E78DC0D"
                },
            ),
        )

    async def _search_occupants(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Search for occupants at addresses."""
        query = arguments.get("query", "")
        max_results = min(arguments.get("max_results", 10), 50)

        params = {
            "addressString": query,
            "maxResults": max_results,
            "outputSRS": 4326,
        }

        endpoint = "/occupants/addresses.json"
        data = await self._request("GET", endpoint, params=params)

        results = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [])

            results.append(
                {
                    "occupant_name": props.get("occupantName"),
                    "full_address": props.get("fullAddress"),
                    "locality": props.get("localityName"),
                    "occupant_type": props.get("occupantType"),
                    "coordinates": {
                        "longitude": coords[0] if len(coords) > 0 else None,
                        "latitude": coords[1] if len(coords) > 1 else None,
                    },
                }
            )

        return MCPToolResult(
            success=True,
            data={
                "occupants": results,
                "count": len(results),
                "query": query,
            },
            source_info=self._build_source_info(
                endpoint=endpoint,
                params=params,
                description=(
                    f"BC Geocoder API - Occupant search for '{query}'. "
                    f"Found {len(results)} occupants."
                ),
                confidence=ConfidenceLevel.HIGH,
                extra={
                    "documentation": "https://www2.gov.bc.ca/gov/content?id=118DD57CD9674D57BDBD511C2E78DC0D"
                },
            ),
        )

    async def _find_nearest(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Find nearest site to coordinates."""
        longitude = arguments.get("longitude")
        latitude = arguments.get("latitude")
        max_distance = arguments.get("max_distance", 1000)

        if longitude is None or latitude is None:
            return MCPToolResult(
                success=False,
                error="Both longitude and latitude are required",
            )

        params = {
            "point": f"{longitude},{latitude}",
            "maxDistance": max_distance,
            "outputSRS": 4326,
        }

        endpoint = "/sites/nearest.json"
        data = await self._request("GET", endpoint, params=params)

        result = None
        if "properties" in data:
            props = data["properties"]
            geom = data.get("geometry", {})
            coords = geom.get("coordinates", [])

            result = {
                "full_address": props.get("fullAddress"),
                "locality": props.get("localityName"),
                "site_id": props.get("siteID"),
                "coordinates": {
                    "longitude": coords[0] if len(coords) > 0 else None,
                    "latitude": coords[1] if len(coords) > 1 else None,
                },
            }

        return MCPToolResult(
            success=True,
            data={
                "nearest_site": result,
                "search_point": {"longitude": longitude, "latitude": latitude},
                "max_distance_meters": max_distance,
            },
            source_info=self._build_source_info(
                endpoint=endpoint,
                params=params,
                description=(
                    f"BC Geocoder API - Nearest site search at ({latitude}, {longitude}) "
                    f"within {max_distance}m."
                ),
                confidence=ConfidenceLevel.HIGH if result else ConfidenceLevel.LOW,
                extra={
                    "documentation": "https://www2.gov.bc.ca/gov/content?id=118DD57CD9674D57BDBD511C2E78DC0D"
                },
            ),
        )

    async def _search_intersections(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Search for street intersections."""
        intersection = arguments.get("intersection", "")
        max_results = min(arguments.get("max_results", 5), 20)

        params = {
            "addressString": intersection,
            "maxResults": max_results,
            "outputSRS": 4326,
        }

        endpoint = "/intersections.json"
        data = await self._request("GET", endpoint, params=params)

        results = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [])

            results.append(
                {
                    "intersection_name": props.get("fullAddress"),
                    "locality": props.get("localityName"),
                    "score": props.get("score"),
                    "coordinates": {
                        "longitude": coords[0] if len(coords) > 0 else None,
                        "latitude": coords[1] if len(coords) > 1 else None,
                    },
                }
            )

        return MCPToolResult(
            success=True,
            data={
                "intersections": results,
                "count": len(results),
                "query": intersection,
            },
            source_info=self._build_source_info(
                endpoint=endpoint,
                params=params,
                description=(
                    f"BC Geocoder API - Intersection search for '{intersection}'. "
                    f"Found {len(results)} intersections."
                ),
                confidence=ConfidenceLevel.HIGH,
            ),
        )

    async def health_check(self) -> bool:
        """Check if Geocoder API is healthy."""
        try:
            params = {
                "addressString": "victoria",
                "maxResults": 1,
                "outputSRS": 4326,
            }
            await self._request("GET", "/addresses.json", params=params)
            return True
        except Exception as e:
            logger.warning(f"Geocoder health check failed: {e}")
            return False
