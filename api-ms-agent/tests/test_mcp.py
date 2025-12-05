"""Tests for MCP wrappers."""

import pytest

from app.services.mcp import GeocoderMCP, OrgBookMCP, ParksMCP
from app.services.mcp.base import ConfidenceLevel, MCPTool, MCPToolResult


class TestMCPBase:
    """Tests for MCP base classes."""

    def test_mcp_tool_result_success(self):
        """Test successful MCPToolResult."""
        result = MCPToolResult(
            success=True,
            data={"test": "data"},
            source_info={"source_type": "api", "description": "Test"},
        )
        assert result.success is True
        assert result.data == {"test": "data"}
        assert result.error is None
        assert result.source_info["source_type"] == "api"

    def test_mcp_tool_result_failure(self):
        """Test failed MCPToolResult."""
        result = MCPToolResult(
            success=False,
            error="Test error",
        )
        assert result.success is False
        assert result.error == "Test error"
        assert result.data is None

    def test_mcp_tool_result_to_dict(self):
        """Test MCPToolResult.to_dict()."""
        result = MCPToolResult(
            success=True,
            data={"key": "value"},
            source_info={"source_type": "api"},
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["data"] == {"key": "value"}
        assert d["source_info"] == {"source_type": "api"}

    def test_mcp_tool_to_dict(self):
        """Test MCPTool.to_dict()."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        )
        d = tool.to_dict()
        assert d["name"] == "test_tool"
        assert d["description"] == "A test tool"
        assert "inputSchema" in d

    def test_confidence_level_enum(self):
        """Test ConfidenceLevel enum values."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"


class TestOrgBookMCP:
    """Tests for OrgBook MCP wrapper."""

    def test_orgbook_initialization(self):
        """Test OrgBookMCP initialization."""
        mcp = OrgBookMCP()
        assert mcp.base_url == "https://orgbook.gov.bc.ca/api/v4"
        assert mcp.name == "orgbook"

    def test_orgbook_tools(self):
        """Test OrgBookMCP tools are defined."""
        mcp = OrgBookMCP()
        tools = mcp.tools
        assert len(tools) >= 3
        tool_names = [t.name for t in tools]
        assert "orgbook_search" in tool_names
        assert "orgbook_get_topic" in tool_names
        assert "orgbook_get_credentials" in tool_names

    @pytest.mark.asyncio
    async def test_orgbook_unknown_tool(self):
        """Test OrgBookMCP with unknown tool."""
        mcp = OrgBookMCP()
        result = await mcp.execute_tool("unknown_tool", {})
        assert result.success is False
        assert "Unknown tool" in (result.error or "")


class TestGeocoderMCP:
    """Tests for Geocoder MCP wrapper."""

    def test_geocoder_initialization(self):
        """Test GeocoderMCP initialization."""
        mcp = GeocoderMCP()
        assert mcp.base_url == "https://geocoder.api.gov.bc.ca"
        assert mcp.name == "geocoder"

    def test_geocoder_tools(self):
        """Test GeocoderMCP tools are defined."""
        mcp = GeocoderMCP()
        tools = mcp.tools
        assert len(tools) >= 4
        tool_names = [t.name for t in tools]
        assert "geocoder_geocode" in tool_names
        assert "geocoder_occupants" in tool_names
        assert "geocoder_nearest" in tool_names
        assert "geocoder_intersections" in tool_names

    @pytest.mark.asyncio
    async def test_geocoder_unknown_tool(self):
        """Test GeocoderMCP with unknown tool."""
        mcp = GeocoderMCP()
        result = await mcp.execute_tool("unknown_tool", {})
        assert result.success is False
        assert "Unknown tool" in (result.error or "")


class TestParksMCP:
    """Tests for Parks MCP wrapper."""

    def test_parks_initialization(self):
        """Test ParksMCP initialization."""
        mcp = ParksMCP()
        assert mcp.base_url == "https://bcparks.api.gov.bc.ca/api"
        assert mcp.name == "parks"

    def test_parks_tools(self):
        """Test ParksMCP tools are defined."""
        mcp = ParksMCP()
        tools = mcp.tools
        assert len(tools) >= 6
        tool_names = [t.name for t in tools]
        assert "parks_search" in tool_names
        assert "parks_list" in tool_names
        assert "parks_get_details" in tool_names
        assert "parks_activities" in tool_names
        assert "parks_facilities" in tool_names
        assert "parks_by_activity" in tool_names

    @pytest.mark.asyncio
    async def test_parks_unknown_tool(self):
        """Test ParksMCP with unknown tool."""
        mcp = ParksMCP()
        result = await mcp.execute_tool("unknown_tool", {})
        assert result.success is False
        assert "Unknown tool" in (result.error or "")
