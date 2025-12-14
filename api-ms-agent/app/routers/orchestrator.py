"""
Orchestrator API Router

Provides endpoints for the multi-agent orchestrator that coordinates
OrgBook and Geocoder agents for BC government data queries.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user_from_request
from app.auth.models import KeycloakUser
from app.logger import get_logger
from app.services.cosmos_db_service import CosmosDbService, get_cosmos_db_service
from app.services.orchestrator_agent import get_orchestrator_agent
from app.services.session_utils import resolve_session_id

logger = get_logger(__name__)

router = APIRouter()

_ORCH_SESSION_PREFIX = "orch_"


class OrchestratorQueryRequest(BaseModel):
    """Request model for orchestrator queries."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language query about BC businesses or locations",
        examples=[
            "Find information about TELUS Communications Inc",
            "What is the address of 1234 Main Street Vancouver?",
            "Is ABC Company Ltd a registered business in BC?",
        ],
    )
    session_id: str | None = Field(
        None,
        description="Optional session ID for tracking conversation context",
    )
    model: str | None = Field(
        default=None,
        description="Model to use: 'gpt-4o-mini' (default) or 'gpt-41-nano'",
    )


class SourceInfo(BaseModel):
    """Source citation information."""

    source_type: str = Field(..., description="Type of source (api, llm_knowledge, document)")
    description: str = Field(..., description="Description of the source")
    confidence: str = Field(..., description="Confidence level (high, medium, low)")
    url: str | None = Field(None, description="Optional URL for the source")


class OrchestratorQueryResponse(BaseModel):
    """Response model for orchestrator queries."""

    response: str = Field(..., description="Synthesized response to the user's query")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    sources: list[SourceInfo] = Field(
        ..., min_length=1, description="List of sources used to generate the response"
    )
    has_sufficient_info: bool = Field(..., description="Whether sufficient information was found")
    key_findings: list[str] = Field(default_factory=list, description="Key findings from the query")


@router.post("/query", response_model=OrchestratorQueryResponse)
async def query_orchestrator(
    request: OrchestratorQueryRequest,
    cosmos: Annotated[CosmosDbService, Depends(get_cosmos_db_service)],
    current_user: Annotated[KeycloakUser, Depends(get_current_user_from_request)],
) -> OrchestratorQueryResponse:
    """
    Query the orchestrator agent to get information about BC businesses and locations.

    The orchestrator will:
    1. Analyze your query to determine which data sources to use
    2. Query OrgBook for business/organization information
    3. Query BC Geocoder for address/location information
    4. Synthesize results into a coherent response with citations

    **Examples:**
    - "Find information about TELUS Communications Inc"
    - "What is the registered address of ABC Company Ltd?"
    - "Geocode 1234 Main Street, Vancouver BC"
    - "Is XYZ Corporation an active business in BC?"
    """
    user_id = current_user.sub

    session_id, session_id_source = await resolve_session_id(
        cosmos=cosmos,
        user_id=user_id,
        requested_session_id=request.session_id,
        session_id_prefix=_ORCH_SESSION_PREFIX,
    )

    logger.info(
        "orchestrator_query_received",
        user_id=user_id,
        query=request.query[:100],  # Log first 100 chars
        session_id=session_id,
        session_id_source=session_id_source,
    )

    try:
        orchestrator = get_orchestrator_agent()

        # Load recent history for this user+session so the LLM can remain conversational.
        stored_messages = await cosmos.get_chat_history(session_id, user_id, limit=20)
        history = (
            [{"role": msg.role, "content": msg.content} for msg in stored_messages]
            if stored_messages
            else None
        )

        # Persist the user message first (even if downstream fails, we have an audit trail).
        await cosmos.save_message(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=request.query,
        )

        result = await orchestrator.process_query(
            query=request.query,
            session_id=session_id,
            user_id=user_id,
            history=history,
            model=request.model,
        )

        # Map sources to the response model
        sources = [
            SourceInfo(
                source_type=s.get("source_type", "unknown"),
                description=s.get("description", ""),
                confidence=s.get("confidence", "medium"),
                url=s.get("url"),
            )
            for s in result.get("sources", [])
        ]

        if not sources:
            raise HTTPException(
                status_code=500,
                detail="Citations are required but none were returned by the orchestrator",
            )

        response = OrchestratorQueryResponse(
            response=result.get("response", ""),
            session_id=session_id,
            sources=sources,
            has_sufficient_info=result.get("has_sufficient_info", False),
            key_findings=result.get("key_findings", []),
        )

        # Persist assistant response with citations for traceability.
        await cosmos.save_message(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=response.response,
            sources=[s for s in result.get("sources", []) if isinstance(s, dict)],
        )

        logger.info(
            "orchestrator_query_completed",
            user_id=user_id,
            source_count=len(sources),
            has_sufficient_info=response.has_sufficient_info,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "orchestrator_query_failed",
            user_id=user_id,
            error=str(e),
            query=request.query[:100],
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to process query",
        ) from e


@router.get("/health")
async def orchestrator_health():
    """Check health of the orchestrator and all MCP-wrapped APIs."""
    orchestrator = get_orchestrator_agent()
    return await orchestrator.health_check()
