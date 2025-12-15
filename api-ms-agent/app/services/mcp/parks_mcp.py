"""
BC Parks MCP Wrapper.

Provides MCP tools for querying BC Parks API for parks, activities, and facilities.
API Base: https://bcparks.api.gov.bc.ca/api
"""

import asyncio
import math
import re
import time
from typing import Any

from app.config import settings
from app.logger import get_logger
from app.services.mcp.base import ConfidenceLevel, MCPTool, MCPToolResult, MCPWrapper

logger = get_logger(__name__)

# BC Parks API Base URL
PARKS_BASE_URL = "https://bcparks.api.gov.bc.ca/api"


class ParksMCP(MCPWrapper):
    """
    MCP wrapper for BC Parks API.

    Provides tools for:
    - Searching for BC provincial parks
    - Getting park details including facilities and activities
    - Finding parks by activity type
    - Getting campsite/reservation information
    """

    def __init__(self, base_url: str | None = None, cache_ttl_seconds: int = 43200):
        """Initialize the Parks MCP wrapper."""
        configured_base = base_url or getattr(settings, "parks_base_url", None) or PARKS_BASE_URL
        super().__init__(base_url=configured_base)
        self._cache_ttl_seconds = cache_ttl_seconds
        self._parks_cache: dict[str, Any] = {"timestamp": 0, "parks": []}
        self._parks_cache_lock = asyncio.Lock()
        self._parks_cache_refresh_lock = asyncio.Lock()
        logger.info("ParksMCP initialized")

    @property
    def tools(self) -> list[MCPTool]:
        """Return list of available Parks MCP tools."""
        return [
            MCPTool(
                name="parks_search",
                description=(
                    "Search for BC provincial parks by name, region, or keyword. "
                    "Returns matching parks with basic information."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Park name or keyword to search for",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                        "latitude": {
                            "type": "number",
                            "description": "Optional: Latitude for proximity search",
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Optional: Longitude for proximity search",
                        },
                        "radius_km": {
                            "type": "number",
                            "description": "Optional: Search radius (km) for proximity search",
                            "default": 100,
                            "minimum": 0,
                            "maximum": 500,
                        },
                    },
                    "required": ["query"],
                },
            ),
            MCPTool(
                name="parks_list",
                description=(
                    "List all BC provincial parks. Optionally filter by type or status. "
                    "Returns paginated list of parks."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 25,
                            "minimum": 1,
                            "maximum": 100,
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Offset for pagination",
                            "default": 0,
                        },
                    },
                    "required": [],
                },
            ),
            MCPTool(
                name="parks_get_details",
                description=(
                    "Get detailed information about a specific BC park by its ORCS number or slug. "
                    "Returns full park details including description, location, and amenities."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "park_id": {
                            "type": "string",
                            "description": "Park ORCS number or URL slug",
                        },
                    },
                    "required": ["park_id"],
                },
            ),
            MCPTool(
                name="parks_activities",
                description=(
                    "Get list of activities available at BC parks. "
                    "Can filter to show activities at a specific park."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "park_id": {
                            "type": "string",
                            "description": "Optional: Park ORCS number to filter activities",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 50,
                        },
                    },
                    "required": [],
                },
            ),
            MCPTool(
                name="parks_facilities",
                description=(
                    "Get list of facilities at BC parks. "
                    "Includes campgrounds, day-use areas, trails, etc."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "park_id": {
                            "type": "string",
                            "description": "Optional: Park ORCS number to filter facilities",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 50,
                        },
                    },
                    "required": [],
                },
            ),
            MCPTool(
                name="parks_by_activity",
                description=(
                    "Find BC parks that offer a specific activity. "
                    "E.g., find parks with hiking, camping, fishing, etc."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "activity": {
                            "type": "string",
                            "description": (
                                "Activity to search for (e.g., 'hiking', 'camping', 'fishing')"
                            ),
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 20,
                        },
                    },
                    "required": ["activity"],
                },
            ),
        ]

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Execute a Parks MCP tool."""
        logger.info(f"[ParksMCP] Executing tool: {tool_name}")

        # Validate arguments
        tool = self._get_tool_by_name(tool_name)
        if tool:
            ok, err = self.validate_arguments(tool, arguments)
            if not ok:
                return MCPToolResult(success=False, error=f"Invalid arguments: {err}")

        try:
            if tool_name == "parks_search":
                return await self._search_parks(arguments)
            elif tool_name == "parks_list":
                return await self._list_parks(arguments)
            elif tool_name == "parks_get_details":
                return await self._get_park_details(arguments)
            elif tool_name == "parks_activities":
                return await self._get_activities(arguments)
            elif tool_name == "parks_facilities":
                return await self._get_facilities(arguments)
            elif tool_name == "parks_by_activity":
                return await self._find_parks_by_activity(arguments)
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Unknown tool: {tool_name}",
                )
        except Exception as e:
            logger.error(f"[ParksMCP] Error executing {tool_name}: {e}")
            return MCPToolResult(
                success=False,
                error=str(e),
            )

    async def _search_parks(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Search for parks by name, location, or keyword."""
        query = arguments.get("query", "").lower()
        limit = min(arguments.get("limit", 15), 50)
        # Optional coordinates for proximity search
        latitude = arguments.get("latitude")
        longitude = arguments.get("longitude")
        radius_km = arguments.get("radius_km", 100)  # Default 100km radius

        endpoint = "/protected-areas"

        all_parks = await self._get_all_parks_cached(endpoint=endpoint)
        logger.info(f"[ParksMCP] Loaded {len(all_parks)} total parks")

        results = []

        # If coordinates provided, do proximity search
        if latitude is not None and longitude is not None:
            for park in all_parks:
                attrs = park.get("attributes", park)
                park_lat = attrs.get("latitude")
                park_lon = attrs.get("longitude")

                if park_lat is not None and park_lon is not None:
                    distance = self._haversine_distance(latitude, longitude, park_lat, park_lon)
                    if distance <= radius_km:
                        park_info = self._extract_park_info_full(park)
                        park_info["distance_km"] = round(distance, 1)
                        results.append(park_info)

            # Sort by distance
            results.sort(key=lambda x: x.get("distance_km", 999))
            results = results[:limit]

            return MCPToolResult(
                success=True,
                data={
                    "parks": results,
                    "count": len(results),
                    "query": query,
                    "search_type": "proximity",
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius_km": radius_km,
                },
                source_info=self._build_source_info(
                    endpoint=endpoint,
                    params={"lat": latitude, "lon": longitude, "radius": radius_km},
                    description=(
                        f"BC Parks API - Parks within {radius_km}km of coordinates. "
                        f"Found {len(results)} parks."
                    ),
                    confidence=ConfidenceLevel.HIGH if results else ConfidenceLevel.MEDIUM,
                ),
            )

        # Text-based search across multiple fields
        for park in all_parks:
            attrs = park.get("attributes", park)
            park_name = attrs.get("protectedAreaName", attrs.get("name", ""))
            description = attrs.get("description", "") or ""
            location_notes = attrs.get("locationNotes", "") or ""
            search_terms = attrs.get("searchTerms", "") or ""

            # Search across multiple fields
            searchable = f"{park_name} {description} {location_notes} {search_terms}".lower()

            if query in searchable:
                park_info = self._extract_park_info_full(park)
                results.append(park_info)
                if len(results) >= limit:
                    break

        return MCPToolResult(
            success=True,
            data={
                "parks": results,
                "count": len(results),
                "query": query,
                "search_type": "text",
            },
            source_info=self._build_source_info(
                endpoint=endpoint,
                params={"query": query, "limit": limit},
                description=(
                    f"BC Parks API - Search for '{query}'. Found {len(results)} matching parks."
                ),
                confidence=ConfidenceLevel.HIGH if results else ConfidenceLevel.MEDIUM,
            ),
        )

    async def _resolve_park_id(self, park_id: str) -> str | None:
        """Resolve a park_id to an ORCS number.

        The BC Parks API expects /protected-areas/{orcs} where orcs is numeric.
        If park_id is already numeric, return it. Otherwise, search the cached
        parks list by name and return the matching ORCS number.
        """
        # If it looks like an ORCS number (digits only), use it directly
        if park_id.isdigit():
            return park_id

        # Search the cached parks list for a matching name
        all_parks = await self._get_all_parks_cached(endpoint="/protected-areas")
        park_id_lower = park_id.lower().strip()

        for park in all_parks:
            attrs = park.get("attributes", park) if isinstance(park, dict) else {}
            name = (attrs.get("protectedAreaName") or attrs.get("name") or "").lower()
            orcs = attrs.get("orcs")

            # Check for exact match or close match
            if name == park_id_lower or park_id_lower in name or name in park_id_lower:
                if orcs:
                    logger.debug(f"Resolved park name '{park_id}' to ORCS '{orcs}'")
                    return str(orcs)
                # Fallback to park id if orcs not available
                pid = park.get("id")
                if pid:
                    logger.debug(f"Resolved park name '{park_id}' to id '{pid}'")
                    return str(pid)

        # Could not resolve
        return None

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers using Haversine formula."""
        R = 6371  # Earth's radius in kilometers

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    async def _get_all_parks_cached(self, endpoint: str) -> list[dict[str, Any]]:
        """Return the full parks list, using a TTL cache.

        - Concurrency-safe: cache reads/writes are locked.
        - Thundering-herd safe: only one refresh runs at a time.
        """
        now = time.time()
        async with self._parks_cache_lock:
            cached_parks = self._parks_cache.get("parks") or []
            cached_ts = float(self._parks_cache.get("timestamp") or 0)
            if cached_parks and now - cached_ts < self._cache_ttl_seconds:
                logger.debug(f"[ParksMCP] Using cached parks list ({len(cached_parks)})")
                return cached_parks

        async with self._parks_cache_refresh_lock:
            # Re-check after acquiring refresh lock in case another coroutine refreshed.
            now = time.time()
            async with self._parks_cache_lock:
                cached_parks = self._parks_cache.get("parks") or []
                cached_ts = float(self._parks_cache.get("timestamp") or 0)
                if cached_parks and now - cached_ts < self._cache_ttl_seconds:
                    logger.debug(f"[ParksMCP] Using cached parks list ({len(cached_parks)})")
                    return cached_parks

            parks = await self._fetch_all_parks_paginated(endpoint=endpoint)
            async with self._parks_cache_lock:
                self._parks_cache["parks"] = parks
                self._parks_cache["timestamp"] = now
            return parks

    async def _fetch_all_parks_paginated(self, endpoint: str) -> list[dict[str, Any]]:
        """Fetch the full parks list using Strapi pagination.

        Uses bounded parallelism to reduce cold-cache latency.
        """
        page_size = 100
        max_pages = 50  # Hard safety cap

        first_params = {"pagination[page]": 1, "pagination[pageSize]": page_size}
        first = await self._request("GET", endpoint, params=first_params)
        parks = list(first.get("data", []) or [])
        meta = first.get("meta", {}).get("pagination", {})
        page_count = int(meta.get("pageCount", 1) or 1)
        page_count = max(1, min(page_count, max_pages))

        if page_count <= 1:
            return parks

        semaphore = asyncio.Semaphore(5)

        async def fetch_page(p: int) -> list[dict[str, Any]]:
            async with semaphore:
                params = {"pagination[page]": p, "pagination[pageSize]": page_size}
                try:
                    data = await self._request("GET", endpoint, params=params)
                    return list(data.get("data", []) or [])
                except Exception as e:
                    logger.warning(f"[ParksMCP] Pagination error at page {p}: {e}")
                    return []

        remaining_pages = await asyncio.gather(*(fetch_page(p) for p in range(2, page_count + 1)))
        for page_items in remaining_pages:
            parks.extend(page_items)
        return parks

    async def _list_parks(self, arguments: dict[str, Any]) -> MCPToolResult:
        """List all parks with pagination."""
        limit = min(arguments.get("limit", 25), 100)
        offset = arguments.get("offset", 0)

        params = {
            "_limit": limit,
            "_start": offset,
        }
        endpoint = "/protected-areas"

        try:
            data = await self._request("GET", endpoint, params=params)
        except Exception:
            # Fallback without params
            data = await self._request("GET", endpoint)

        # Handle both array and object response formats
        parks_list = data if isinstance(data, list) else data.get("data", data)
        if not isinstance(parks_list, list):
            parks_list = []

        results = [self._extract_park_info_full(park) for park in parks_list[:limit]]

        return MCPToolResult(
            success=True,
            data={
                "parks": results,
                "count": len(results),
                "offset": offset,
                "limit": limit,
            },
            source_info=self._build_source_info(
                endpoint=endpoint,
                params=params,
                description=(
                    f"BC Parks API - List parks (offset={offset}, limit={limit}). "
                    f"Returned {len(results)} parks."
                ),
                confidence=ConfidenceLevel.HIGH,
            ),
        )

    async def _get_park_details(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Get detailed information about a specific park."""
        park_id = arguments.get("park_id", "")

        if not park_id:
            return MCPToolResult(
                success=False,
                error="park_id is required",
            )

        # Resolve park_id to an ORCS number if it looks like a park name.
        # The API expects /protected-areas/{orcs} where orcs is numeric.
        resolved_id = await self._resolve_park_id(park_id)
        if resolved_id is None:
            # Could not resolve; fall back to search
            logger.info(f"Could not resolve park_id '{park_id}', using search fallback")
            return await self._search_parks({"query": park_id, "limit": 1})

        endpoint = f"/protected-areas/{resolved_id}"

        try:
            data = await self._request("GET", endpoint)
        except Exception as e:
            # Fall back to search if direct lookup fails
            logger.info(f"Direct lookup failed for '{resolved_id}', trying search: {e}")
            return await self._search_parks({"query": park_id, "limit": 1})

        # Handle nested data structure
        park_data = data.get("data", data) if isinstance(data, dict) else data
        attrs = park_data.get("attributes", park_data) if isinstance(park_data, dict) else {}

        park_info = {
            "id": park_data.get("id"),
            "orcs": attrs.get("orcs"),
            "name": attrs.get("protectedAreaName", attrs.get("name", "")),
            "description": attrs.get("description", ""),
            "url": attrs.get("url"),
            "latitude": attrs.get("latitude"),
            "longitude": attrs.get("longitude"),
            "established_date": attrs.get("establishedDate"),
            "total_area": attrs.get("totalArea"),
            "management_area": attrs.get("managementArea", {}).get("managementAreaName")
            if isinstance(attrs.get("managementArea"), dict)
            else None,
            "type": attrs.get("type", {}).get("type")
            if isinstance(attrs.get("type"), dict)
            else attrs.get("typeCode"),
            "status": attrs.get("status"),
        }

        # Extract activities if present
        activities = attrs.get("parkActivities", [])
        if activities:
            park_info["activities"] = [
                {
                    "name": act.get("activityType", {}).get("activityName", "")
                    if isinstance(act.get("activityType"), dict)
                    else act.get("name", ""),
                    "description": act.get("description", ""),
                }
                for act in activities[:20]
            ]

        # Extract facilities if present
        facilities = attrs.get("parkFacilities", [])
        if facilities:
            park_info["facilities"] = [
                {
                    "name": fac.get("facilityType", {}).get("facilityName", "")
                    if isinstance(fac.get("facilityType"), dict)
                    else fac.get("name", ""),
                    "description": fac.get("description", ""),
                }
                for fac in facilities[:20]
            ]

        return MCPToolResult(
            success=True,
            data=park_info,
            source_info=self._build_source_info(
                endpoint=endpoint,
                description=f"BC Parks API - Details for park '{park_info.get('name', park_id)}'.",
                confidence=ConfidenceLevel.HIGH,
            ),
        )

    async def _get_activities(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Get activities available at parks."""
        park_id = arguments.get("park_id")
        limit = min(arguments.get("limit", 50), 100)

        if park_id:
            endpoint = f"/protected-areas/{park_id}"
            try:
                data = await self._request("GET", endpoint)
                park_data = data.get("data", data) if isinstance(data, dict) else data
                if isinstance(park_data, dict):
                    attrs = park_data.get("attributes", park_data)
                else:
                    attrs = {}
                activities_raw = attrs.get("parkActivities", [])
            except Exception as e:
                logger.warning(f"Failed to get park activities: {e}")
                activities_raw = []
        else:
            # Get all activity types
            endpoint = "/park-activities"
            try:
                data = await self._request("GET", endpoint, params={"_limit": limit})
            except Exception:
                data = await self._request("GET", endpoint)
            activities_raw = data if isinstance(data, list) else data.get("data", [])

        activities = []
        for act in activities_raw[:limit]:
            attrs = act.get("attributes", act) if isinstance(act, dict) else {}
            act_type = attrs.get("activityType", {})

            activities.append(
                {
                    "id": act.get("id"),
                    "name": act_type.get("activityName", "")
                    if isinstance(act_type, dict)
                    else attrs.get("activityName", attrs.get("name", "")),
                    "description": attrs.get("description", ""),
                    "is_active": attrs.get("isActive", True),
                }
            )

        return MCPToolResult(
            success=True,
            data={
                "activities": activities,
                "count": len(activities),
                "park_id": park_id,
            },
            source_info=self._build_source_info(
                endpoint=endpoint,
                description=(
                    "BC Parks API - Activities"
                    + (f" for park {park_id}" if park_id else "")
                    + f". Found {len(activities)} activities."
                ),
                confidence=ConfidenceLevel.HIGH,
            ),
        )

    async def _get_facilities(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Get facilities at parks."""
        park_id = arguments.get("park_id")
        limit = min(arguments.get("limit", 50), 100)

        if park_id:
            endpoint = f"/protected-areas/{park_id}"
            try:
                data = await self._request("GET", endpoint)
                park_data = data.get("data", data) if isinstance(data, dict) else data
                if isinstance(park_data, dict):
                    attrs = park_data.get("attributes", park_data)
                else:
                    attrs = {}
                facilities_raw = attrs.get("parkFacilities", [])
            except Exception as e:
                logger.warning(f"Failed to get park facilities: {e}")
                facilities_raw = []
        else:
            # Get all facility types
            endpoint = "/park-facilities"
            try:
                data = await self._request("GET", endpoint, params={"_limit": limit})
            except Exception:
                data = await self._request("GET", endpoint)
            facilities_raw = data if isinstance(data, list) else data.get("data", [])

        facilities = []
        for fac in facilities_raw[:limit]:
            attrs = fac.get("attributes", fac) if isinstance(fac, dict) else {}
            fac_type = attrs.get("facilityType", {})

            facilities.append(
                {
                    "id": fac.get("id"),
                    "name": fac_type.get("facilityName", "")
                    if isinstance(fac_type, dict)
                    else attrs.get("facilityName", attrs.get("name", "")),
                    "description": attrs.get("description", ""),
                    "is_active": attrs.get("isActive", True),
                }
            )

        return MCPToolResult(
            success=True,
            data={
                "facilities": facilities,
                "count": len(facilities),
                "park_id": park_id,
            },
            source_info=self._build_source_info(
                endpoint=endpoint,
                description=(
                    "BC Parks API - Facilities"
                    + (f" for park {park_id}" if park_id else "")
                    + f". Found {len(facilities)} facilities."
                ),
                confidence=ConfidenceLevel.HIGH,
            ),
        )

    async def _find_parks_by_activity(self, arguments: dict[str, Any]) -> MCPToolResult:
        """Find parks that offer a specific activity."""
        activity = arguments.get("activity", "").lower()
        limit = min(arguments.get("limit", 20), 50)

        if not activity:
            return MCPToolResult(
                success=False,
                error="activity is required",
            )

        # Get all parks and filter by activity
        endpoint = "/protected-areas"
        try:
            data = await self._request("GET", endpoint, params={"_limit": 100})
        except Exception:
            data = await self._request("GET", endpoint)

        parks_list = data if isinstance(data, list) else data.get("data", [])

        matching_parks = []
        for park in parks_list:
            attrs = park.get("attributes", park) if isinstance(park, dict) else {}
            activities = attrs.get("parkActivities", [])

            for act in activities:
                act_attrs = act.get("attributes", act) if isinstance(act, dict) else {}
                act_type = act_attrs.get("activityType", {})
                act_name = (
                    act_type.get("activityName", "")
                    if isinstance(act_type, dict)
                    else act_attrs.get("activityName", "")
                ).lower()

                if activity in act_name:
                    park_info = self._extract_park_info_full(park)
                    park_info["matched_activity"] = act_name
                    matching_parks.append(park_info)
                    break

            if len(matching_parks) >= limit:
                break

        return MCPToolResult(
            success=True,
            data={
                "parks": matching_parks,
                "count": len(matching_parks),
                "activity": activity,
            },
            source_info=self._build_source_info(
                endpoint=endpoint,
                params={"activity_filter": activity},
                description=(
                    f"BC Parks API - Parks with '{activity}' activity. "
                    f"Found {len(matching_parks)} parks."
                ),
                confidence=ConfidenceLevel.HIGH if matching_parks else ConfidenceLevel.MEDIUM,
            ),
        )

    def _extract_park_info_full(self, park: dict[str, Any]) -> dict[str, Any]:
        """Extract full park info including facilities and activities."""
        attrs = park.get("attributes", park) if isinstance(park, dict) else {}

        # Clean up HTML from description
        description = attrs.get("description", "") or ""
        # Remove HTML tags for cleaner output
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()

        park_info = {
            "id": park.get("id"),
            "orcs": attrs.get("orcs"),
            "name": attrs.get("protectedAreaName", attrs.get("name", "")),
            "description": description[:800] if description else "",
            "url": attrs.get("url"),
            "latitude": attrs.get("latitude"),
            "longitude": attrs.get("longitude"),
            "location_notes": attrs.get("locationNotes", ""),
            "type": attrs.get("type", {}).get("type")
            if isinstance(attrs.get("type"), dict)
            else attrs.get("typeCode", attrs.get("type", "")),
            "status": attrs.get("status"),
        }

        # Extract activities if present
        activities = attrs.get("parkActivities", [])
        if activities:
            park_info["activities"] = []
            for act in activities[:15]:
                act_attrs = act.get("attributes", act) if isinstance(act, dict) else {}
                act_type = act_attrs.get("activityType", {})
                act_name = (
                    act_type.get("activityName", "")
                    if isinstance(act_type, dict)
                    else act_attrs.get("activityName", act_attrs.get("name", ""))
                )
                if act_name:
                    park_info["activities"].append(act_name)

        # Extract facilities if present
        facilities = attrs.get("parkFacilities", [])
        if facilities:
            park_info["facilities"] = []
            for fac in facilities[:15]:
                fac_attrs = fac.get("attributes", fac) if isinstance(fac, dict) else {}
                fac_type = fac_attrs.get("facilityType", {})
                fac_name = (
                    fac_type.get("facilityName", "")
                    if isinstance(fac_type, dict)
                    else fac_attrs.get("facilityName", fac_attrs.get("name", ""))
                )
                fac_desc = fac_attrs.get("description", "")
                if fac_name:
                    fac_entry = fac_name
                    if fac_desc:
                        # Clean HTML from facility description
                        fac_desc = re.sub(r"<[^>]+>", " ", fac_desc)
                        fac_desc = re.sub(r"\s+", " ", fac_desc).strip()
                        if len(fac_desc) > 200:
                            fac_desc = fac_desc[:200] + "..."
                        fac_entry = f"{fac_name}: {fac_desc}"
                    park_info["facilities"].append(fac_entry)

        return park_info

    def _extract_park_info(self, park: dict[str, Any]) -> dict[str, Any]:
        """Extract standardized park info from API response."""
        attrs = park.get("attributes", park) if isinstance(park, dict) else {}

        return {
            "id": park.get("id"),
            "orcs": attrs.get("orcs"),
            "name": attrs.get("protectedAreaName", attrs.get("name", "")),
            "description": (attrs.get("description", "") or "")[:500],  # Truncate long descriptions
            "url": attrs.get("url"),
            "latitude": attrs.get("latitude"),
            "longitude": attrs.get("longitude"),
            "type": attrs.get("type", {}).get("type")
            if isinstance(attrs.get("type"), dict)
            else attrs.get("typeCode"),
            "status": attrs.get("status"),
        }

    async def health_check(self) -> bool:
        """Check if Parks API is healthy."""
        try:
            # Try to get the protected-areas endpoint
            await self._request("GET", "/protected-areas", params={"_limit": 1})
            return True
        except Exception as e:
            logger.warning(f"Parks API health check failed: {e}")
            return False
