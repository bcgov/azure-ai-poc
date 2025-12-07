"""
Test orchestrator agent reasoning and tool usage patterns.

These tests validate that the orchestrator agent:
1. Uses tools appropriately based on query context
2. Produces proper source citations
3. Handles out-of-scope queries gracefully
4. Follows Microsoft Agent Framework best practices
"""

import pytest

from app.services.orchestrator_agent import (
    SYSTEM_INSTRUCTIONS,
    ORCHESTRATOR_TOOLS,
    OrchestratorAgentService,
)


class TestOrchestratorInstructions:
    """Test that system instructions follow MAF best practices."""

    def test_instructions_include_reasoning_guidance(self):
        """Verify instructions provide step-by-step reasoning guidance."""
        assert "Analyze the Query" in SYSTEM_INSTRUCTIONS
        assert "Plan Your Tool Usage" in SYSTEM_INSTRUCTIONS
        assert "Execute Efficiently" in SYSTEM_INSTRUCTIONS
        assert "Synthesize Response" in SYSTEM_INSTRUCTIONS

    def test_instructions_include_tool_descriptions(self):
        """Verify instructions describe available tools."""
        assert "BC Parks Tools" in SYSTEM_INSTRUCTIONS
        assert "BC Geocoder Tools" in SYSTEM_INSTRUCTIONS
        assert "BC OrgBook Tools" in SYSTEM_INSTRUCTIONS

    def test_instructions_include_when_to_use_tools(self):
        """Verify instructions clarify when to use tools."""
        assert "WHEN TO USE TOOLS" in SYSTEM_INSTRUCTIONS
        assert "ALWAYS attempt to use tools first" in SYSTEM_INSTRUCTIONS

    def test_instructions_include_efficiency_guidance(self):
        """Verify instructions promote efficient tool usage."""
        assert "Call each tool only ONCE" in SYSTEM_INSTRUCTIONS
        assert "Avoid redundant calls" in SYSTEM_INSTRUCTIONS

    def test_instructions_include_source_attribution_requirement(self):
        """Verify instructions mandate source attribution."""
        assert "SOURCE ATTRIBUTION" in SYSTEM_INSTRUCTIONS
        assert "traceability" in SYSTEM_INSTRUCTIONS.lower()


class TestOrchestratorTools:
    """Test that tools are properly configured."""

    def test_all_tools_registered(self):
        """Verify all expected tools are registered."""
        # AIFunction objects have name attribute
        tool_names = [t.name for t in ORCHESTRATOR_TOOLS]

        # Geocoder tools
        assert "geocoder_geocode" in tool_names
        assert "geocoder_occupants" in tool_names

        # Parks tools
        assert "parks_search" in tool_names
        assert "parks_get_details" in tool_names
        assert "parks_by_activity" in tool_names

        # OrgBook tools
        assert "orgbook_search" in tool_names
        assert "orgbook_get_topic" in tool_names

    def test_tool_count(self):
        """Verify expected number of tools are registered."""
        assert len(ORCHESTRATOR_TOOLS) == 7


class TestOrchestratorService:
    """Test orchestrator service configuration."""

    def test_service_initialization(self):
        """Verify service initializes without errors."""
        service = OrchestratorAgentService()
        assert service is not None
        assert service._agent is None  # Lazy initialization
        assert service._client is None

    def test_service_follows_maf_patterns(self):
        """Verify service uses MAF built-in ChatAgent."""
        service = OrchestratorAgentService()
        agent = service._get_agent()

        # Verify it's using ChatAgent (has expected attributes)
        assert hasattr(agent, "run")
        assert hasattr(agent, "chat_client")

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Verify health check works."""
        service = OrchestratorAgentService()
        health = await service.health_check()

        assert "status" in health
        assert "services" in health
        assert "orchestrator" in health["services"]
        assert "orgbook_api" in health["services"]
        assert "geocoder_api" in health["services"]
        assert "parks_api" in health["services"]


class TestSourceAttribution:
    """Test source attribution patterns."""

    def test_source_info_dataclass(self):
        """Verify SourceInfo follows best practices."""
        from app.services.orchestrator_agent import SourceInfo

        # Test API source with full details
        source = SourceInfo(
            source_type="api",
            description="Test API call",
            url="https://example.com/api?q=test",
            api_endpoint="/api",
            api_params={"q": "test"},
            confidence="high",
        )

        source_dict = source.to_dict()
        assert source_dict["source_type"] == "api"
        assert source_dict["description"] == "Test API call"
        assert source_dict["url"] == "https://example.com/api?q=test"
        assert source_dict["api_endpoint"] == "/api"
        assert source_dict["api_params"] == {"q": "test"}
        assert source_dict["confidence"] == "high"

    def test_llm_knowledge_source(self):
        """Verify LLM knowledge sources are properly structured."""
        from app.services.orchestrator_agent import SourceInfo

        source = SourceInfo(
            source_type="llm_knowledge",
            description="Response based on LLM reasoning",
            confidence="medium",
        )

        source_dict = source.to_dict()
        assert source_dict["source_type"] == "llm_knowledge"
        assert source_dict["confidence"] == "medium"


@pytest.mark.integration
class TestOrchestratorIntegration:
    """Integration tests for orchestrator (requires live services)."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires live Azure OpenAI and BC APIs")
    async def test_parks_query_with_tools(self):
        """Test that parks queries use appropriate tools."""
        service = OrchestratorAgentService()

        result = await service.process_query("Find parks near Victoria BC", session_id="test-123")

        assert "response" in result
        assert "sources" in result
        assert len(result["sources"]) > 0
        assert result["has_sufficient_info"] is True

        # Should have used geocoder and parks tools
        source_types = [s["source_type"] for s in result["sources"]]
        assert "api" in source_types

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires live Azure OpenAI")
    async def test_out_of_scope_query(self):
        """Test that out-of-scope queries are handled gracefully."""
        service = OrchestratorAgentService()

        result = await service.process_query("What's the weather in Tokyo?", session_id="test-456")

        assert "response" in result
        assert "sources" in result
        assert len(result["sources"]) > 0

        # Should have LLM knowledge source
        assert result["sources"][0]["source_type"] == "llm_knowledge"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires live Azure OpenAI")
    async def test_conversational_query(self):
        """Test that greetings don't force tool usage."""
        service = OrchestratorAgentService()

        result = await service.process_query("Hello, how are you?", session_id="test-789")

        assert "response" in result
        assert "sources" in result

        # May have LLM knowledge source
        if result["sources"]:
            assert result["sources"][0]["source_type"] == "llm_knowledge"
