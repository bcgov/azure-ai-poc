"""
Tests for the Deep Research Agent using Agent Framework SDK.

Tests the workflow-based implementation with WorkflowBuilder and Executors.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.research import get_research_service
from app.services.research_agent import (
    DeepResearchAgentService,
    ResearchPhase,
    ResearchState,
    ResearchPlan,
    ResearchFinding,
)


# Note: mock_auth_service and auth_headers fixtures are provided by conftest.py


@pytest.fixture
def mock_research_service() -> MagicMock:
    """Create a mock research service."""
    service = MagicMock(spec=DeepResearchAgentService)
    return service


@pytest.fixture
def client(mock_auth_service, mock_research_service: MagicMock) -> TestClient:
    """Create a test client with mocked research service and auth."""
    app.dependency_overrides[get_research_service] = lambda: mock_research_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_state() -> ResearchState:
    """Create a sample research state."""
    return ResearchState(
        topic="Impact of AI on software development",
        plan=ResearchPlan(
            main_topic="Impact of AI on software development",
            research_questions=[
                "How is AI changing developer workflows?",
                "What are the productivity gains from AI tools?",
            ],
            subtopics=["Code generation", "Testing automation", "Documentation"],
            methodology="Literature review and analysis",
            estimated_depth="medium",
            sources_to_explore=["Academic papers", "Industry reports"],
        ),
        current_phase=ResearchPhase.PLANNING,
    )


class TestStartResearch:
    """Tests for starting a research workflow."""

    def test_start_research_success(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test successful research workflow creation."""
        mock_research_service.start_research = AsyncMock(
            return_value={
                "run_id": "test-run-123",
                "topic": "Impact of AI on software development",
                "status": "started",
                "current_phase": "planning",
            }
        )

        response = client.post(
            "/api/v1/research/start",
            json={"topic": "Impact of AI on software development", "user_id": "user-1"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["run_id"] == "test-run-123"
        assert data["topic"] == "Impact of AI on software development"
        assert data["status"] == "started"
        assert data["current_phase"] == "planning"

    def test_start_research_short_topic(self, client: TestClient, auth_headers: dict) -> None:
        """Test validation for short topic."""
        response = client.post(
            "/api/v1/research/start",
            json={"topic": "AI"},
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    def test_start_research_error(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test error handling during research start."""
        mock_research_service.start_research = AsyncMock(side_effect=Exception("LLM error"))

        response = client.post(
            "/api/v1/research/start",
            json={"topic": "Impact of AI on software development"},
            headers=auth_headers,
        )

        assert response.status_code == 500
        assert "Failed to start research" in response.json()["detail"]


class TestRunWorkflow:
    """Tests for running a workflow."""

    def test_run_workflow_success(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test successful workflow execution."""
        mock_research_service.run_workflow = AsyncMock(
            return_value={
                "run_id": "test-run-123",
                "status": "completed",
                "current_phase": "completed",
                "plan": {
                    "main_topic": "AI Impact",
                    "research_questions": ["Q1", "Q2"],
                    "subtopics": ["Topic1"],
                    "methodology": "Analysis",
                },
                "findings": [{"subtopic": "Topic1", "content": "Finding 1", "confidence": "high"}],
                "final_report": "# Final Report\n\nThis is the report.",
                "workflow_state": "IDLE",
            }
        )

        response = client.post("/api/v1/research/run/test-run-123", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "test-run-123"
        assert data["status"] == "completed"
        assert data["final_report"] is not None

    def test_run_workflow_not_found(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test running a non-existent workflow."""
        mock_research_service.run_workflow = AsyncMock(
            side_effect=ValueError("Run non-existent not found")
        )

        response = client.post("/api/v1/research/run/non-existent", headers=auth_headers)

        assert response.status_code == 404

    def test_run_workflow_error(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test error during workflow execution."""
        mock_research_service.run_workflow = AsyncMock(side_effect=Exception("Workflow error"))

        response = client.post("/api/v1/research/run/test-run-123", headers=auth_headers)

        assert response.status_code == 500
        assert "Failed to run workflow" in response.json()["detail"]


class TestGetRunStatus:
    """Tests for getting workflow run status."""

    def test_get_run_status_success(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test getting status of a workflow run."""
        mock_research_service.get_run_status.return_value = {
            "run_id": "test-run-123",
            "current_phase": "researching",
            "topic": "AI Impact",
            "has_plan": True,
            "findings_count": 2,
            "has_report": False,
            "pending_approvals": 1,
        }

        response = client.get("/api/v1/research/run/test-run-123/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "test-run-123"
        assert data["current_phase"] == "researching"
        assert data["has_plan"] is True
        assert data["pending_approvals"] == 1

    def test_get_run_status_not_found(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test getting status of non-existent run."""
        mock_research_service.get_run_status.side_effect = ValueError("Run not found")

        response = client.get("/api/v1/research/run/non-existent/status", headers=auth_headers)

        assert response.status_code == 404


class TestSendApproval:
    """Tests for sending approval."""

    def test_send_approval_success(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test sending an approval."""
        mock_research_service.send_approval = AsyncMock(
            return_value={
                "run_id": "test-run-123",
                "request_id": "req-456",
                "status": "approval_sent",
                "approved": True,
            }
        )

        response = client.post(
            "/api/v1/research/run/test-run-123/approve",
            json={"request_id": "req-456", "approved": True, "feedback": "Looks good!"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "test-run-123"
        assert data["approved"] is True
        assert data["status"] == "approval_sent"

    def test_send_approval_rejected(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test rejecting an approval."""
        mock_research_service.send_approval = AsyncMock(
            return_value={
                "run_id": "test-run-123",
                "request_id": "req-456",
                "status": "approval_sent",
                "approved": False,
            }
        )

        response = client.post(
            "/api/v1/research/run/test-run-123/approve",
            json={"request_id": "req-456", "approved": False, "feedback": "Needs more detail"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is False

    def test_send_approval_not_found(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test sending approval for non-existent request."""
        mock_research_service.send_approval = AsyncMock(side_effect=ValueError("Request not found"))

        response = client.post(
            "/api/v1/research/run/test-run-123/approve",
            json={"request_id": "non-existent", "approved": True},
            headers=auth_headers,
        )

        assert response.status_code == 400


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check returns healthy status."""
        # Health endpoint is excluded from auth
        response = client.get("/api/v1/research/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "deep-research-agent-framework"


class TestResearchStateDataclass:
    """Tests for the ResearchState dataclass."""

    def test_research_state_creation(self) -> None:
        """Test creating a ResearchState."""
        state = ResearchState(topic="Test Topic")

        assert state.topic == "Test Topic"
        assert state.current_phase == ResearchPhase.PLANNING
        assert state.plan is None
        assert state.findings == []
        assert state.final_report == ""

    def test_research_state_with_plan(self, sample_state: ResearchState) -> None:
        """Test ResearchState with a plan."""
        assert sample_state.plan is not None
        assert sample_state.plan.main_topic == "Impact of AI on software development"
        assert len(sample_state.plan.research_questions) == 2
        assert len(sample_state.plan.subtopics) == 3


class TestResearchPlanDataclass:
    """Tests for the ResearchPlan dataclass."""

    def test_research_plan_creation(self) -> None:
        """Test creating a ResearchPlan."""
        plan = ResearchPlan(
            main_topic="Test Topic",
            research_questions=["Q1", "Q2"],
            subtopics=["S1", "S2"],
        )

        assert plan.main_topic == "Test Topic"
        assert len(plan.research_questions) == 2
        assert plan.estimated_depth == "medium"  # default

    def test_research_plan_defaults(self) -> None:
        """Test ResearchPlan default values."""
        plan = ResearchPlan(main_topic="Test")

        assert plan.research_questions == []
        assert plan.subtopics == []
        assert plan.methodology == ""
        assert plan.estimated_depth == "medium"
        assert plan.sources_to_explore == []


class TestResearchFindingDataclass:
    """Tests for the ResearchFinding dataclass."""

    def test_research_finding_creation(self) -> None:
        """Test creating a ResearchFinding."""
        finding = ResearchFinding(
            subtopic="Code Generation",
            content="AI code generation tools have increased productivity by 40%.",
            confidence="high",
            sources=["GitHub Survey 2024"],
        )

        assert finding.subtopic == "Code Generation"
        assert "productivity" in finding.content
        assert finding.confidence == "high"
        assert len(finding.sources) == 1

    def test_research_finding_defaults(self) -> None:
        """Test ResearchFinding default values."""
        finding = ResearchFinding(subtopic="Test", content="Test content")

        assert finding.confidence == "medium"
        assert finding.sources == []


class TestResearchPhaseEnum:
    """Tests for ResearchPhase enum."""

    def test_phase_values(self) -> None:
        """Test ResearchPhase enum values."""
        assert ResearchPhase.PLANNING.value == "planning"
        assert ResearchPhase.RESEARCHING.value == "researching"
        assert ResearchPhase.SYNTHESIZING.value == "synthesizing"
        assert ResearchPhase.COMPLETED.value == "completed"

    def test_phase_from_string(self) -> None:
        """Test creating ResearchPhase from string."""
        phase = ResearchPhase("planning")
        assert phase == ResearchPhase.PLANNING
