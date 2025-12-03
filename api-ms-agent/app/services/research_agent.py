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
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
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
class ResearchSource:
    """A source citation."""

    source_type: str  # 'llm_knowledge', 'document', 'web', 'api'
    description: str
    confidence: str = "medium"  # 'high', 'medium', 'low'
    url: str | None = None


@dataclass
class ResearchState:
    """State passed through the workflow."""

    topic: str
    plan: ResearchPlan | None = None
    findings: list[ResearchFinding] = field(default_factory=list)
    synthesis: str = ""
    final_report: str = ""
    sources: list[ResearchSource] = field(default_factory=list)
    current_phase: ResearchPhase = ResearchPhase.PLANNING
    feedback_history: list[str] = field(default_factory=list)


# ==================== AI Functions for Research Workflow ====================


# Global state storage for simulating research process
_research_state_store: dict[str, ResearchState] = {}


@ai_function()
def save_research_plan(
    plan_json: Annotated[str, "JSON string containing the research plan"],
    topic: Annotated[str, "The research topic"],
) -> str:
    """
    Save the research plan and proceed with research.
    """
    try:
        plan_data = json.loads(plan_json)
        # Store the plan
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
        logger.info(
            "research_plan_saved",
            topic=topic,
            questions_count=len(state.plan.research_questions),
        )
        return f"Research plan saved for topic: {topic}. Proceeding to research."
    except json.JSONDecodeError as e:
        logger.error("plan_json_decode_error", topic=topic, error=str(e))
        return "Error: Invalid plan JSON format"


@ai_function()
def save_research_findings(
    findings_json: Annotated[str, "JSON string containing the research findings"],
    topic: Annotated[str, "The research topic"],
) -> str:
    """
    Save the research findings and proceed with synthesis.
    """
    try:
        findings_data = json.loads(findings_json)
        if topic in _research_state_store:
            state = _research_state_store[topic]
        else:
            # Try partial match
            state = None
            for key in _research_state_store:
                if topic.lower() in key.lower() or key.lower() in topic.lower():
                    state = _research_state_store[key]
                    break
            if not state:
                state = ResearchState(topic=topic)
                _research_state_store[topic] = state

        state.findings = [
            ResearchFinding(
                subtopic=f.get("subtopic", ""),
                content=f.get("content", ""),
                confidence=f.get("confidence", "medium"),
                sources=f.get("sources", []),
            )
            for f in findings_data
        ]
        state.current_phase = ResearchPhase.SYNTHESIZING
        logger.info("research_findings_saved", topic=topic, findings_count=len(state.findings))
        return f"Research findings saved for topic: {topic}. Proceeding with synthesis phase."
    except json.JSONDecodeError as e:
        logger.error("findings_json_decode_error", topic=topic, error=str(e))
        return "Error: Invalid findings JSON format"


@ai_function()
def save_final_report(
    report: Annotated[str, "The final research report with inline citations"],
    topic: Annotated[str, "The research topic"],
    sources_json: Annotated[
        str,
        "JSON array of sources with source_type, description, confidence, url",
    ] = "[]",
) -> str:
    """
    Save the final research report with sources. This completes the research.
    Sources must include: source_type, description, confidence, url (optional).
    """
    logger.info("save_final_report_called", topic=topic, report_length=len(report))

    # Parse sources
    try:
        sources_data = json.loads(sources_json) if sources_json else []
    except json.JSONDecodeError:
        sources_data = []

    sources = [
        ResearchSource(
            source_type=s.get("source_type", "llm_knowledge"),
            description=s.get("description", ""),
            confidence=s.get("confidence", "medium"),
            url=s.get("url"),
        )
        for s in sources_data
    ]

    if topic in _research_state_store:
        state = _research_state_store[topic]
        state.final_report = report
        state.sources = sources
        state.current_phase = ResearchPhase.COMPLETED
        logger.info("final_report_saved", topic=topic, sources_count=len(sources))
    else:
        # Try to find by partial match
        for key in _research_state_store:
            if topic.lower() in key.lower() or key.lower() in topic.lower():
                state = _research_state_store[key]
                state.final_report = report
                state.sources = sources
                state.current_phase = ResearchPhase.COMPLETED
                logger.info(
                    "final_report_saved_partial_match",
                    topic=topic,
                    matched_key=key,
                    sources_count=len(sources),
                )
                break
        else:
            # Store with new key
            _research_state_store[topic] = ResearchState(
                topic=topic,
                final_report=report,
                sources=sources,
                current_phase=ResearchPhase.COMPLETED,
            )
            logger.info(
                "final_report_saved_new_key",
                topic=topic,
                sources_count=len(sources),
            )
    return f"Final report saved for topic: {topic}. {len(sources)} sources."


# ==================== Main Service Class ====================


class DeepResearchAgentService:
    """
    Deep Research Agent using Microsoft Agent Framework SDK.

    Uses ChatAgent with ai_function for tool-based research workflow.

    Workflow: Planning -> Research -> Synthesis -> Complete
    """

    def __init__(self) -> None:
        """Initialize the deep research agent service."""
        self._client: AsyncAzureOpenAI | None = None
        self._credential: DefaultAzureCredential | None = None
        self._active_runs: dict[str, Any] = {}  # Track active workflow runs
        logger.info("DeepResearchAgentService initialized with Agent Framework SDK")

    def _get_client(self) -> AsyncAzureOpenAI:
        """Get or create the Azure OpenAI client with managed identity or API key."""
        if self._client is None:
            if settings.use_managed_identity:
                self._credential = DefaultAzureCredential()
                token_provider = get_bearer_token_provider(
                    self._credential, "https://cognitiveservices.azure.com/.default"
                )
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=settings.azure_openai_endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=settings.azure_openai_api_version,
                )
                logger.info("Using managed identity for Azure OpenAI")
            else:
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=settings.azure_openai_endpoint,
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_openai_api_version,
                )
                logger.info("Using API key for Azure OpenAI")
        return self._client

    def _create_research_agent(self) -> ChatAgent:
        """Create a ChatAgent configured for deep research with approval checkpoints."""
        from agent_framework.openai import OpenAIChatClient

        # Create OpenAI chat client using the Azure OpenAI async client
        chat_client = OpenAIChatClient(
            async_client=self._get_client(),
            model_id=settings.azure_openai_deployment,
        )

        return ChatAgent(
            name="DeepResearchAgent",
            instructions="""You are a thorough research assistant. You MUST complete all three phases using the provided tools.

IMPORTANT: You MUST call the tool functions to save your work at each phase. Do not just describe what you would do - actually call the functions.

CITATION REQUIREMENT: Every piece of information MUST include a source citation. For each fact or claim, you must track:
- source_type: "llm_knowledge", "document", "web", or "api"
- description: What the source is (e.g., "General AI knowledge about machine learning concepts")
- confidence: "high", "medium", or "low"
- url: If available, provide a URL (use null if not available)

## PHASE 1: PLANNING
Create a research plan, then call save_research_plan() with:
- plan_json: A JSON string like {"research_questions": ["q1", "q2"], "subtopics": ["s1", "s2"], "methodology": "description"}
- topic: The exact research topic

## PHASE 2: RESEARCH  
Research each subtopic WITH CITATIONS, then call save_research_findings() with:
- findings_json: A JSON string like:
  [{"subtopic": "name", "content": "detailed findings...", "confidence": "high", "sources": [{"source_type": "llm_knowledge", "description": "AI training knowledge on topic X", "confidence": "high", "url": null}]}]
- topic: The exact research topic

CRITICAL: Each finding MUST include a "sources" array with at least one source citation.

## PHASE 3: SYNTHESIS
Write a comprehensive final report (2000+ words with sections), then call save_final_report() with:
- report: The complete markdown report including Executive Summary, Key Findings, Analysis, Conclusions, and Recommendations
- sources_json: A JSON string with ALL sources used: [{"source_type": "llm_knowledge", "description": "...", "confidence": "high", "url": null}]
- topic: The exact research topic

CRITICAL: The sources_json MUST include ALL sources cited throughout the research. Every claim in the final report must be traceable to a source.

After calling save_final_report(), provide a brief summary to the user.

YOU MUST CALL ALL THREE FUNCTIONS IN ORDER. The report in save_final_report() should be the detailed, complete research report with full source attribution.""",
            chat_client=chat_client,
            tools=[save_research_plan, save_research_findings, save_final_report],
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
            # Run the agent with the research topic - it will complete all phases
            query = f"""Please research this topic thoroughly: {state.topic}

Complete all three phases of the research workflow:
1. First, create a research plan and call save_research_plan()
2. Then, conduct research and call save_research_findings()
3. Finally, synthesize a report and call save_final_report()

Provide comprehensive, detailed responses at each phase."""

            result = await agent.run(query, thread=thread)

            # Log the result for debugging
            logger.info(
                "agent_run_result",
                run_id=run_id,
                result_type=type(result).__name__,
                result_str=str(result)[:500],
            )

            # Get stored state from global store if available
            # Try exact match first, then partial match
            stored_state = _research_state_store.get(state.topic)
            if not stored_state:
                # Try partial match
                for key in _research_state_store:
                    if state.topic.lower() in key.lower() or key.lower() in state.topic.lower():
                        stored_state = _research_state_store[key]
                        logger.info("found_state_partial_match", topic=state.topic, matched_key=key)
                        break

            if stored_state:
                state.plan = stored_state.plan
                state.findings = stored_state.findings
                state.final_report = stored_state.final_report
                state.sources = stored_state.sources
                logger.info(
                    "retrieved_stored_state",
                    has_plan=state.plan is not None,
                    findings_count=len(state.findings),
                    has_final_report=bool(state.final_report),
                    final_report_length=len(state.final_report) if state.final_report else 0,
                    sources_count=len(state.sources),
                )
            else:
                logger.warning(
                    "no_stored_state_found",
                    topic=state.topic,
                    store_keys=list(_research_state_store.keys()),
                )

            # Workflow complete
            state.current_phase = ResearchPhase.COMPLETED
            final_message = str(result)

            return {
                "run_id": run_id,
                "status": "completed",
                "current_phase": state.current_phase.value,
                "message": final_message,
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
                "final_report": state.final_report or final_message,
                "sources": [
                    {
                        "source_type": s.source_type,
                        "description": s.description,
                        "confidence": s.confidence,
                        "url": s.url,
                    }
                    for s in state.sources
                ],
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
