"""
Deep Research Agent Service with Human-in-the-Loop.

This service uses Microsoft Agent Framework SDK's ChatAgent with ai_function
approval_mode="always_require" for native human-in-the-loop support.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any
from uuid import uuid4

from agent_framework import (
    ChatAgent,
    ChatMessage,
    ai_function,
)
from openai import AsyncAzureOpenAI

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


# ==================== Data Models ====================


class ResearchPhase(str, Enum):
    """Current phase of the research workflow."""

    PLANNING = "planning"
    AWAITING_PLAN_APPROVAL = "awaiting_plan_approval"
    RESEARCHING = "researching"
    AWAITING_FINDINGS_APPROVAL = "awaiting_findings_approval"
    SYNTHESIZING = "synthesizing"
    AWAITING_REPORT_APPROVAL = "awaiting_report_approval"
    COMPLETED = "completed"


@dataclass
class ResearchPlan:
    """A research plan with subtopics and approach."""

    main_topic: str
    research_questions: list[str] = field(default_factory=list)
    subtopics: list[str] = field(default_factory=list)
    methodology: str = ""
    estimated_depth: str = "medium"
    sources_to_explore: list[str] = field(default_factory=list)


@dataclass
class ResearchFinding:
    """A single research finding."""

    subtopic: str
    content: str
    confidence: str = "medium"
    sources: list[str] = field(default_factory=list)


@dataclass
class ResearchState:
    """State passed through the workflow."""

    topic: str
    plan: ResearchPlan | None = None
    findings: list[ResearchFinding] = field(default_factory=list)
    synthesis: str = ""
    final_report: str = ""
    current_phase: ResearchPhase = ResearchPhase.PLANNING
    feedback_history: list[str] = field(default_factory=list)


# ==================== AI Functions with Human-in-the-Loop ====================


# Global state storage for simulating research process
_research_state_store: dict[str, ResearchState] = {}


@ai_function(approval_mode="always_require")
def approve_research_plan(
    plan_json: Annotated[str, "JSON string containing the research plan to approve"],
    topic: Annotated[str, "The research topic"],
) -> str:
    """
    Approve the research plan before proceeding with research.
    This function requires human approval before execution.
    """
    try:
        plan_data = json.loads(plan_json)
        # Store the approved plan
        state = ResearchState(
            topic=topic,
            plan=ResearchPlan(
                main_topic=topic,
                research_questions=plan_data.get("research_questions", []),
                subtopics=plan_data.get("subtopics", []),
                methodology=plan_data.get("methodology", ""),
                estimated_depth=plan_data.get("estimated_depth", "medium"),
                sources_to_explore=plan_data.get("sources_to_explore", []),
            ),
            current_phase=ResearchPhase.RESEARCHING,
        )
        _research_state_store[topic] = state
        return f"Research plan approved for topic: {topic}. Proceeding with research."
    except json.JSONDecodeError:
        return "Error: Invalid plan JSON format"


@ai_function(approval_mode="always_require")
def approve_research_findings(
    findings_json: Annotated[str, "JSON string containing the research findings to approve"],
    topic: Annotated[str, "The research topic"],
) -> str:
    """
    Approve the research findings before synthesis.
    This function requires human approval before execution.
    """
    try:
        findings_data = json.loads(findings_json)
        if topic in _research_state_store:
            state = _research_state_store[topic]
            state.findings = [
                ResearchFinding(
                    subtopic=f.get("subtopic", ""),
                    content=f.get("content", ""),
                    confidence=f.get("confidence", "medium"),
                )
                for f in findings_data
            ]
            state.current_phase = ResearchPhase.SYNTHESIZING
        return f"Research findings approved for topic: {topic}. Proceeding with synthesis."
    except json.JSONDecodeError:
        return "Error: Invalid findings JSON format"


@ai_function(approval_mode="always_require")
def approve_final_report(
    report: Annotated[str, "The final research report to approve"],
    topic: Annotated[str, "The research topic"],
) -> str:
    """
    Approve the final research report.
    This function requires human approval before execution.
    """
    if topic in _research_state_store:
        state = _research_state_store[topic]
        state.final_report = report
        state.current_phase = ResearchPhase.COMPLETED
    return f"Final report approved for topic: {topic}. Research complete."


# ==================== Main Service Class ====================


class DeepResearchAgentService:
    """
    Deep Research Agent using Microsoft Agent Framework SDK.

    Uses ChatAgent with ai_function approval_mode="always_require" for
    native human-in-the-loop support at key decision points.

    Workflow: Planning -> [Approval] -> Research -> [Approval] -> Synthesis -> [Approval] -> Complete
    """

    def __init__(self) -> None:
        """Initialize the deep research agent service."""
        self._client: AsyncAzureOpenAI | None = None
        self._active_runs: dict[str, Any] = {}  # Track active workflow runs
        logger.info("DeepResearchAgentService initialized with Agent Framework SDK")

    def _get_client(self) -> AsyncAzureOpenAI:
        """Get or create the Azure OpenAI client."""
        if self._client is None:
            self._client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
        return self._client

    def _create_research_agent(self) -> ChatAgent:
        """Create a ChatAgent configured for deep research with approval checkpoints."""
        from agent_framework.openai import OpenAIChatClient

        # Create OpenAI chat client pointing to Azure endpoint
        chat_client = OpenAIChatClient(
            openai_client=self._get_client(),
            model_id=settings.azure_openai_deployment,
        )

        return ChatAgent(
            name="DeepResearchAgent",
            instructions="""You are a thorough research assistant that helps users explore topics in depth.

Your workflow involves three key phases, each requiring human approval:

1. PLANNING PHASE:
   - Analyze the topic and create a comprehensive research plan
   - Generate research questions, subtopics to explore, and methodology
   - Call approve_research_plan() with the plan - this requires human approval

2. RESEARCH PHASE:
   - After plan approval, conduct detailed research on each subtopic
   - Gather findings with confidence levels
   - Call approve_research_findings() with findings - this requires human approval

3. SYNTHESIS PHASE:
   - After findings approval, synthesize everything into a final report
   - Include executive summary, key findings, conclusions, and recommendations
   - Call approve_final_report() with the report - this requires human approval

Always format plans, findings, and reports clearly. Wait for approval at each checkpoint.""",
            chat_client=chat_client,
            tools=[approve_research_plan, approve_research_findings, approve_final_report],
        )

    async def start_research(self, topic: str, user_id: str | None = None) -> dict:
        """
        Start a new research workflow.

        Args:
            topic: The topic to research.
            user_id: Optional user ID for tracking.

        Returns:
            Dictionary with run_id and initial status.
        """
        run_id = str(uuid4())
        initial_state = ResearchState(topic=topic)

        logger.info(
            "starting_research_workflow",
            run_id=run_id,
            topic=topic,
            user_id=user_id,
        )

        # Create a fresh agent for this run
        agent = self._create_research_agent()
        thread = agent.get_new_thread()

        # Store the agent, thread, and state for tracking
        self._active_runs[run_id] = {
            "agent": agent,
            "thread": thread,
            "state": initial_state,
            "user_id": user_id,
            "pending_approvals": [],
            "messages": [],
        }

        return {
            "run_id": run_id,
            "topic": topic,
            "status": "started",
            "current_phase": initial_state.current_phase.value,
        }

    async def run_workflow(self, run_id: str) -> dict:
        """
        Execute the workflow and handle approval requests.

        Args:
            run_id: The ID of the workflow run.

        Returns:
            Dictionary with results or pending approval information.
        """
        if run_id not in self._active_runs:
            raise ValueError(f"Run {run_id} not found")

        run_data = self._active_runs[run_id]
        agent: ChatAgent = run_data["agent"]
        thread = run_data["thread"]
        state: ResearchState = run_data["state"]

        logger.info("executing_workflow", run_id=run_id, phase=state.current_phase.value)

        try:
            # Run the agent with the research topic
            query = f"Please research this topic thoroughly: {state.topic}"
            result = await agent.run(query, thread=thread)

            # Check for approval requests
            if result.user_input_requests:
                # Store pending approvals
                run_data["pending_approvals"] = list(result.user_input_requests)

                approval_info = []
                for req in result.user_input_requests:
                    approval_info.append(
                        {
                            "request_id": req.id,
                            "function_name": req.function_call.name,
                            "arguments": req.function_call.arguments,
                        }
                    )

                # Update phase based on which approval is pending
                if any("plan" in req.function_call.name for req in result.user_input_requests):
                    state.current_phase = ResearchPhase.AWAITING_PLAN_APPROVAL
                elif any(
                    "findings" in req.function_call.name for req in result.user_input_requests
                ):
                    state.current_phase = ResearchPhase.AWAITING_FINDINGS_APPROVAL
                elif any("report" in req.function_call.name for req in result.user_input_requests):
                    state.current_phase = ResearchPhase.AWAITING_REPORT_APPROVAL

                return {
                    "run_id": run_id,
                    "status": "awaiting_approval",
                    "current_phase": state.current_phase.value,
                    "pending_approvals": approval_info,
                    "message": str(result),
                }

            # No approvals needed, workflow complete
            state.current_phase = ResearchPhase.COMPLETED
            return {
                "run_id": run_id,
                "status": "completed",
                "current_phase": state.current_phase.value,
                "message": str(result),
                "plan": {
                    "main_topic": state.plan.main_topic,
                    "research_questions": state.plan.research_questions,
                    "subtopics": state.plan.subtopics,
                    "methodology": state.plan.methodology,
                }
                if state.plan
                else None,
                "findings": [
                    {
                        "subtopic": f.subtopic,
                        "content": f.content,
                        "confidence": f.confidence,
                    }
                    for f in state.findings
                ],
                "final_report": state.final_report,
            }

        except Exception as e:
            logger.error(
                "workflow_execution_failed",
                run_id=run_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "run_id": run_id,
                "status": "failed",
                "error": str(e),
            }

    async def run_workflow_streaming(self, run_id: str):
        """
        Execute the workflow with streaming events.

        Yields events as they occur, including approval requests
        that pause the workflow for human input.

        Args:
            run_id: The ID of the workflow run.

        Yields:
            Event dictionaries as they occur.
        """
        if run_id not in self._active_runs:
            raise ValueError(f"Run {run_id} not found")

        run_data = self._active_runs[run_id]
        agent: ChatAgent = run_data["agent"]
        thread = run_data["thread"]
        state: ResearchState = run_data["state"]

        logger.info("executing_workflow_streaming", run_id=run_id, phase=state.current_phase.value)

        try:
            query = f"Please research this topic thoroughly: {state.topic}"

            async for chunk in agent.run_stream(query, thread=thread):
                event_dict = {
                    "run_id": run_id,
                    "event_type": "chunk",
                }

                # Stream text content
                if chunk.text:
                    event_dict["text"] = chunk.text
                    yield event_dict

                # Check for approval requests
                if chunk.user_input_requests:
                    run_data["pending_approvals"].extend(chunk.user_input_requests)

                    for req in chunk.user_input_requests:
                        # Update phase
                        if "plan" in req.function_call.name:
                            state.current_phase = ResearchPhase.AWAITING_PLAN_APPROVAL
                        elif "findings" in req.function_call.name:
                            state.current_phase = ResearchPhase.AWAITING_FINDINGS_APPROVAL
                        elif "report" in req.function_call.name:
                            state.current_phase = ResearchPhase.AWAITING_REPORT_APPROVAL

                        yield {
                            "run_id": run_id,
                            "event_type": "approval_request",
                            "requires_approval": True,
                            "request_id": req.id,
                            "function_name": req.function_call.name,
                            "arguments": req.function_call.arguments,
                            "current_phase": state.current_phase.value,
                        }

        except Exception as e:
            logger.error(
                "workflow_streaming_failed",
                run_id=run_id,
                error=str(e),
            )
            yield {
                "run_id": run_id,
                "event_type": "error",
                "error": str(e),
            }

    async def send_approval(
        self, run_id: str, request_id: str, approved: bool, feedback: str | None = None
    ) -> dict:
        """
        Send an approval response for a pending approval request.

        Args:
            run_id: The workflow run ID.
            request_id: The approval request ID.
            approved: Whether to approve the request.
            feedback: Optional feedback with the approval.

        Returns:
            Status of the approval submission.
        """
        if run_id not in self._active_runs:
            raise ValueError(f"Run {run_id} not found")

        run_data = self._active_runs[run_id]
        agent: ChatAgent = run_data["agent"]
        thread = run_data["thread"]
        state: ResearchState = run_data["state"]

        logger.info(
            "sending_approval",
            run_id=run_id,
            request_id=request_id,
            approved=approved,
        )

        # Find the pending approval request
        pending = [a for a in run_data["pending_approvals"] if a.id == request_id]
        if not pending:
            raise ValueError(f"Approval request {request_id} not found")

        approval_request = pending[0]
        run_data["pending_approvals"].remove(approval_request)

        # Add feedback to history if provided
        if feedback:
            state.feedback_history.append(feedback)

        # Create approval response using the SDK's native method
        approval_response = approval_request.create_response(approved=approved)

        # Send the approval response back to the agent
        result = await agent.run(
            ChatMessage(role="user", contents=[approval_response]),
            thread=thread,
        )

        # Check if there are more approval requests
        if result.user_input_requests:
            run_data["pending_approvals"] = list(result.user_input_requests)

            approval_info = []
            for req in result.user_input_requests:
                approval_info.append(
                    {
                        "request_id": req.id,
                        "function_name": req.function_call.name,
                        "arguments": req.function_call.arguments,
                    }
                )

                # Update phase
                if "plan" in req.function_call.name:
                    state.current_phase = ResearchPhase.AWAITING_PLAN_APPROVAL
                elif "findings" in req.function_call.name:
                    state.current_phase = ResearchPhase.AWAITING_FINDINGS_APPROVAL
                elif "report" in req.function_call.name:
                    state.current_phase = ResearchPhase.AWAITING_REPORT_APPROVAL

            return {
                "run_id": run_id,
                "request_id": request_id,
                "status": "approval_sent",
                "approved": approved,
                "next_approvals": approval_info,
                "current_phase": state.current_phase.value,
                "message": str(result),
            }

        # No more approvals, workflow continues or completes
        state.current_phase = ResearchPhase.COMPLETED

        return {
            "run_id": run_id,
            "request_id": request_id,
            "status": "approval_sent",
            "approved": approved,
            "current_phase": state.current_phase.value,
            "message": str(result),
        }

    def get_run_status(self, run_id: str) -> dict:
        """Get the current status of a workflow run."""
        if run_id not in self._active_runs:
            raise ValueError(f"Run {run_id} not found")

        run_data = self._active_runs[run_id]
        state: ResearchState = run_data["state"]

        return {
            "run_id": run_id,
            "current_phase": state.current_phase.value,
            "topic": state.topic,
            "has_plan": state.plan is not None,
            "findings_count": len(state.findings),
            "has_report": bool(state.final_report),
            "pending_approvals": len(run_data["pending_approvals"]),
        }

    async def close(self) -> None:
        """Clean up resources."""
        if self._client:
            await self._client.close()
        self._active_runs.clear()
        logger.info("DeepResearchAgentService closed")


# ==================== Global Service Instance ====================

_deep_research_service: DeepResearchAgentService | None = None


def get_deep_research_service() -> DeepResearchAgentService:
    """Get or create the global deep research service."""
    global _deep_research_service
    if _deep_research_service is None:
        _deep_research_service = DeepResearchAgentService()
    return _deep_research_service
