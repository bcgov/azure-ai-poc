"""
Tests for the Workflow-based Deep Research Agent.

Tests the explicit WorkflowBuilder implementation with Executors.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.workflow_research import get_research_service
from app.services.workflow_research_agent import (
    WorkflowResearchAgentService,
    WorkflowPhase,
    WorkflowState,
    ResearchPlan,
    ResearchFinding,
)


# Note: mock_auth_service and auth_headers fixtures are provided by conftest.py


@pytest.fixture
def mock_research_service() -> MagicMock:
    """Create a mock research service."""
    service = MagicMock(spec=WorkflowResearchAgentService)
    return service


@pytest.fixture
def client(mock_auth_service, mock_research_service: MagicMock) -> TestClient:
    """Create a test client with mocked research service and auth."""
    app.dependency_overrides[get_research_service] = lambda: mock_research_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_state() -> WorkflowState:
    """Create a sample workflow state."""
    return WorkflowState(
        topic="Impact of AI on healthcare",
        require_approval=False,
        plan=ResearchPlan(
            main_topic="Impact of AI on healthcare",
            research_questions=[
                "How is AI improving diagnosis?",
                "What are the ethical concerns?",
            ],
            subtopics=["Diagnosis AI", "Treatment Planning", "Ethics"],
            methodology="Literature review and case studies",
            estimated_depth="medium",
        ),
        findings=[
            ResearchFinding(
                subtopic="Diagnosis AI",
                content="AI has improved diagnostic accuracy by 30%",
                confidence="high",
                key_points=["Radiology", "Pathology", "Early detection"],
            )
        ],
        current_phase=WorkflowPhase.COMPLETED,
    )


class TestStartWorkflowResearch:
    """Tests for starting a workflow research."""

    def test_start_research_no_approval(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test starting research without approval requirement."""
        mock_research_service.start_research = AsyncMock(
            return_value={
                "run_id": "test-run-123",
                "topic": "Impact of AI on healthcare",
                "status": "started",
                "current_phase": "pending",
                "require_approval": False,
            }
        )

        response = client.post(
            "/api/v1/workflow-research/start",
            json={"topic": "Impact of AI on healthcare"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["run_id"] == "test-run-123"
        assert data["require_approval"] is False

    def test_start_research_with_approval_keyword(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test starting research with approval keyword in topic."""
        mock_research_service.start_research = AsyncMock(
            return_value={
                "run_id": "test-run-456",
                "topic": "Research AI ethics with approval before finalizing",
                "status": "started",
                "current_phase": "pending",
                "require_approval": True,
            }
        )

        response = client.post(
            "/api/v1/workflow-research/start",
            json={"topic": "Research AI ethics with approval before finalizing"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["require_approval"] is True

    def test_start_research_explicit_approval(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test starting research with explicit approval flag."""
        mock_research_service.start_research = AsyncMock(
            return_value={
                "run_id": "test-run-789",
                "topic": "Simple topic",
                "status": "started",
                "current_phase": "pending",
                "require_approval": True,
            }
        )

        response = client.post(
            "/api/v1/workflow-research/start",
            json={"topic": "Simple topic", "require_approval": True},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["require_approval"] is True

    def test_start_research_short_topic(self, client: TestClient, auth_headers: dict) -> None:
        """Test validation for short topic."""
        response = client.post(
            "/api/v1/workflow-research/start",
            json={"topic": "AI"},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestRunWorkflow:
    """Tests for running the workflow."""

    def test_run_workflow_complete(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test running workflow to completion."""
        mock_research_service.run_workflow = AsyncMock(
            return_value={
                "run_id": "test-run-123",
                "status": "completed",
                "current_phase": "completed",
                "topic": "AI Impact",
                "plan": {
                    "main_topic": "AI Impact",
                    "research_questions": ["Q1", "Q2"],
                    "subtopics": ["Topic1"],
                    "methodology": "Analysis",
                },
                "findings": [
                    {
                        "subtopic": "Topic1",
                        "content": "Finding 1",
                        "confidence": "high",
                        "key_points": ["Point1"],
                    }
                ],
                "final_report": "# Final Report\n\nContent here.",
            }
        )

        response = client.post("/api/v1/workflow-research/run/test-run-123", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["final_report"] is not None

    def test_run_workflow_awaiting_approval(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test workflow pausing for approval."""
        mock_research_service.run_workflow = AsyncMock(
            return_value={
                "run_id": "test-run-456",
                "status": "awaiting_approval",
                "current_phase": "awaiting_approval",
                "topic": "AI Ethics",
                "message": "Research complete. Awaiting your approval before finalizing.",
                "report_preview": "# Report Preview...",
            }
        )

        response = client.post("/api/v1/workflow-research/run/test-run-456", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "awaiting_approval"
        assert "message" in data

    def test_run_workflow_not_found(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test running non-existent workflow."""
        mock_research_service.run_workflow = AsyncMock(
            side_effect=ValueError("Run non-existent not found")
        )

        response = client.post("/api/v1/workflow-research/run/non-existent", headers=auth_headers)
        assert response.status_code == 404


class TestGetRunStatus:
    """Tests for getting workflow status."""

    def test_get_run_status_success(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test getting workflow status."""
        mock_research_service.get_run_status.return_value = {
            "run_id": "test-run-123",
            "current_phase": "researching",
            "topic": "AI Impact",
            "require_approval": False,
            "has_plan": True,
            "findings_count": 2,
            "has_report": False,
            "error": None,
        }

        response = client.get(
            "/api/v1/workflow-research/run/test-run-123/status", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["current_phase"] == "researching"
        assert data["require_approval"] is False

    def test_get_run_status_not_found(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test getting status of non-existent run."""
        mock_research_service.get_run_status.side_effect = ValueError("Run not found")

        response = client.get(
            "/api/v1/workflow-research/run/non-existent/status", headers=auth_headers
        )
        assert response.status_code == 404


class TestSendApproval:
    """Tests for sending approval."""

    def test_send_approval_approved(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test approving the report."""
        mock_research_service.send_approval = AsyncMock(
            return_value={
                "run_id": "test-run-123",
                "status": "completed",
                "approved": True,
                "current_phase": "completed",
                "final_report": "# Final Report",
                "plan": {"main_topic": "Test"},
                "findings": [],
            }
        )

        response = client.post(
            "/api/v1/workflow-research/run/test-run-123/approve",
            json={"approved": True, "feedback": "Looks good!"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is True
        assert data["status"] == "completed"

    def test_send_approval_rejected(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test rejecting the report."""
        mock_research_service.send_approval = AsyncMock(
            return_value={
                "run_id": "test-run-123",
                "status": "rejected",
                "approved": False,
                "current_phase": "failed",
                "feedback": "Needs more detail",
            }
        )

        response = client.post(
            "/api/v1/workflow-research/run/test-run-123/approve",
            json={"approved": False, "feedback": "Needs more detail"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is False
        assert data["status"] == "rejected"

    def test_send_approval_not_awaiting(
        self, client: TestClient, mock_research_service: MagicMock, auth_headers: dict
    ) -> None:
        """Test sending approval when not awaiting."""
        mock_research_service.send_approval = AsyncMock(
            side_effect=ValueError("Run is not awaiting approval")
        )

        response = client.post(
            "/api/v1/workflow-research/run/test-run-123/approve",
            json={"approved": True},
            headers=auth_headers,
        )
        assert response.status_code == 400


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check returns healthy status."""
        # Health endpoint is excluded from auth
        response = client.get("/api/v1/workflow-research/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "workflow-research-agent"
        assert "explicit-workflow-builder" in data["features"]


class TestWorkflowStateDataclass:
    """Tests for WorkflowState dataclass."""

    def test_workflow_state_creation(self) -> None:
        """Test creating a WorkflowState."""
        state = WorkflowState(topic="Test Topic")

        assert state.topic == "Test Topic"
        assert state.current_phase == WorkflowPhase.PENDING
        assert state.require_approval is False
        assert state.plan is None
        assert state.findings == []

    def test_workflow_state_with_approval(self) -> None:
        """Test WorkflowState with approval flag."""
        state = WorkflowState(topic="Test", require_approval=True)
        assert state.require_approval is True


class TestWorkflowPhaseEnum:
    """Tests for WorkflowPhase enum."""

    def test_phase_values(self) -> None:
        """Test WorkflowPhase enum values."""
        assert WorkflowPhase.PENDING.value == "pending"
        assert WorkflowPhase.PLANNING.value == "planning"
        assert WorkflowPhase.RESEARCHING.value == "researching"
        assert WorkflowPhase.SYNTHESIZING.value == "synthesizing"
        assert WorkflowPhase.AWAITING_APPROVAL.value == "awaiting_approval"
        assert WorkflowPhase.COMPLETED.value == "completed"
        assert WorkflowPhase.FAILED.value == "failed"


class TestApprovalDetection:
    """Tests for approval detection logic."""

    def test_detect_approval_keywords(self) -> None:
        """Test that approval keywords are detected."""
        service = WorkflowResearchAgentService()

        # Should detect approval
        assert service._detect_approval_request("Research X with approval") is True
        assert service._detect_approval_request("Review this topic") is True
        assert service._detect_approval_request("Confirm before finalizing") is True
        assert service._detect_approval_request("human review needed") is True

        # Should not detect approval
        assert service._detect_approval_request("Research AI impact") is False
        assert service._detect_approval_request("Simple topic") is False
