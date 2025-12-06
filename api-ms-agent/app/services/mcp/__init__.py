"""
MCP (Model Context Protocol) Wrappers for BC Government APIs.

This module provides standardized MCP tool wrappers for:
- BC OrgBook API (business/organization information)
- BC Geocoder API (address/location information)
- BC Parks API (parks, activities, facilities information)

All wrappers follow the MCP specification for tool definitions,
providing consistent interfaces for AI agents to query BC government data.
"""

from app.services.mcp.base import MCPTool, MCPToolResult, MCPWrapper
from app.services.mcp.geocoder_mcp import GeocoderMCP
from app.services.mcp.orgbook_mcp import OrgBookMCP
from app.services.mcp.parks_mcp import ParksMCP

__all__ = [
    "MCPWrapper",
    "MCPTool",
    "MCPToolResult",
    "OrgBookMCP",
    "GeocoderMCP",
    "ParksMCP",
]
