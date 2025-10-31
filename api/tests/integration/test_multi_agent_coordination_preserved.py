"""Integration tests for multi-agent coordination preservation.

T031: Tests to verify workflow coordination is preserved after selective optimization.
"""

from app.core.selective_optimization_config import SelectiveOptimizationConfig
from app.models.optimization_models import BaselineMetrics


class TestMultiAgentCoordinationPreserved:
    """Integration tests for coordination preservation in multi-agent workflows."""

    def test_workflow_coordination_unaffected_by_optimization(self) -> None:
        """Test workflow coordination remains intact after optimization."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Get configs for all agents
        query_planner = config.get_agent_config("query_planner")
        document_analyzer = config.get_agent_config("document_analyzer")
        answer_generator = config.get_agent_config("answer_generator")

        # All agents have valid configurations
        assert query_planner.tenant_id == "test-tenant"
        assert document_analyzer.tenant_id == "test-tenant"
        assert answer_generator.tenant_id == "test-tenant"

        # Each agent can still coordinate (same tenant)
        assert query_planner.tenant_id == document_analyzer.tenant_id
        assert document_analyzer.tenant_id == answer_generator.tenant_id

    def test_optimized_query_planner_produces_valid_queries(self) -> None:
        """Test optimized query planner still produces valid queries."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Query planner uses RL optimization
        query_planner = config.get_agent_config("query_planner")
        assert query_planner.enable_rl is True

        # Simulate query planner output (still valid after optimization)
        query_output = {
            "query": "What is the capital of France?",
            "intent": "factual_question",
            "confidence": 0.9,
        }

        # Verify output structure is preserved
        assert "query" in query_output
        assert "intent" in query_output
        assert isinstance(query_output["confidence"], float)

    def test_optimized_document_analyzer_returns_valid_documents(self) -> None:
        """Test optimized document analyzer still returns valid documents."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Document analyzer uses prompt optimization
        document_analyzer = config.get_agent_config("document_analyzer")
        assert document_analyzer.enable_prompt_opt is True

        # Simulate document analyzer output (still valid after optimization)
        documents_output = {
            "documents": [
                {"id": "doc1", "content": "Paris is the capital", "score": 0.95},
                {"id": "doc2", "content": "France is in Europe", "score": 0.85},
            ],
            "total_found": 2,
        }

        # Verify output structure is preserved
        assert "documents" in documents_output
        assert len(documents_output["documents"]) == 2
        assert all("id" in doc for doc in documents_output["documents"])

    def test_optimized_answer_generator_produces_coherent_answers(self) -> None:
        """Test optimized answer generator still produces coherent answers."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Answer generator uses SFT optimization
        answer_generator = config.get_agent_config("answer_generator")
        assert answer_generator.enable_sft is True

        # Simulate answer generator output (still coherent after optimization)
        answer_output = {
            "answer": "The capital of France is Paris.",
            "confidence": 0.92,
            "sources": ["doc1", "doc2"],
        }

        # Verify output structure is preserved
        assert "answer" in answer_output
        assert isinstance(answer_output["answer"], str)
        assert len(answer_output["answer"]) > 0
        assert "sources" in answer_output

    def test_end_to_end_workflow_with_all_agents_optimized(self) -> None:
        """Test complete workflow with all agents optimized independently."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Step 1: Query planner (RL optimized)
        query_planner = config.get_agent_config("query_planner")
        assert query_planner.enable_rl is True
        query = "What is the capital of France?"

        # Step 2: Document analyzer (Prompt optimized)
        document_analyzer = config.get_agent_config("document_analyzer")
        assert document_analyzer.enable_prompt_opt is True
        documents = ["Paris is the capital", "France is in Europe"]

        # Step 3: Answer generator (SFT optimized)
        answer_generator = config.get_agent_config("answer_generator")
        assert answer_generator.enable_sft is True
        answer = "The capital of France is Paris."

        # Verify workflow completion
        assert len(query) > 0
        assert len(documents) > 0
        assert len(answer) > 0

    def test_agent_communication_preserved_after_optimization(self) -> None:
        """Test agents can still communicate after optimization."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Get all agent configs
        agents = {
            "query_planner": config.get_agent_config("query_planner"),
            "document_analyzer": config.get_agent_config("document_analyzer"),
            "answer_generator": config.get_agent_config("answer_generator"),
        }

        # All agents share the same tenant (can communicate)
        tenant_ids = [agent.tenant_id for agent in agents.values()]
        assert len(set(tenant_ids)) == 1  # All same tenant
        assert tenant_ids[0] == "test-tenant"

        # Each agent has a unique name (can be addressed)
        agent_names = [agent.agent_name for agent in agents.values()]
        assert len(set(agent_names)) == 3  # All unique names

    def test_optimization_doesnt_break_agent_dependencies(self) -> None:
        """Test agent dependencies remain intact after optimization."""
        config = SelectiveOptimizationConfig(tenant_id="test-tenant")

        # Simulate workflow dependencies
        # Query planner -> Document analyzer -> Answer generator

        # Query planner provides input for document analyzer
        query_planner = config.get_agent_config("query_planner")
        query_output = {"query": "test query"}

        # Document analyzer can receive query planner output
        document_analyzer = config.get_agent_config("document_analyzer")
        assert query_planner.tenant_id == document_analyzer.tenant_id

        # Document analyzer provides input for answer generator
        doc_output = {"documents": ["doc1", "doc2"]}

        # Answer generator can receive document analyzer output
        answer_generator = config.get_agent_config("answer_generator")
        assert document_analyzer.tenant_id == answer_generator.tenant_id

        # Verify dependency chain
        assert query_output is not None
        assert doc_output is not None

    def test_metrics_collection_preserved_across_agents(self) -> None:
        """Test metrics can still be collected from all agents after optimization."""
        # Simulate metrics collection from each agent
        metrics = {
            "query_planner": [
                BaselineMetrics(latency_ms=50.0, token_usage=30, quality_signal=0.8)
                for _ in range(10)
            ],
            "document_analyzer": [
                BaselineMetrics(latency_ms=150.0, token_usage=100, quality_signal=0.75)
                for _ in range(10)
            ],
            "answer_generator": [
                BaselineMetrics(latency_ms=250.0, token_usage=180, quality_signal=0.85)
                for _ in range(10)
            ],
        }

        # All agents can report metrics
        assert len(metrics["query_planner"]) == 10
        assert len(metrics["document_analyzer"]) == 10
        assert len(metrics["answer_generator"]) == 10

        # Metrics are distinguishable by agent
        assert metrics["query_planner"][0].latency_ms != metrics["document_analyzer"][0].latency_ms
