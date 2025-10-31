"""
LangGraph agent service for orchestrated AI workflows.

This service provides LangGraph-based agent workflows with:
- Multi-node agent architecture
- State management across workflow steps
- Tool calling and routing logic
- Integration with existing LangChain services
"""

import time
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from app.core.logger import get_logger
from app.services.azure_search_service import get_azure_search_service
from app.services.langchain_service import LangChainAIService
from app.services.mcp_tools import get_mcp_tools

logger = get_logger(__name__)


class AgentState(BaseModel):
    """Enhanced state object for the LangGraph agent workflow with advanced capabilities."""

    # Messages in the conversation
    messages: Annotated[list[BaseMessage], add_messages]

    # Current user information
    user_id: str | None = None
    session_id: str | None = None

    # Document context for focused search
    selected_document_ids: list[str] | None = None
    search_all_documents: bool = True

    # Workflow metadata
    workflow_id: str | None = None
    step_count: int = 0
    max_steps: int = 10  # Prevent infinite loops

    # Context and results
    context: str | None = None
    search_results: list[dict[str, Any]] | None = None
    document_sources: list[dict[str, Any]] | None = None
    final_answer: str | None = None

    # Advanced reasoning capabilities
    reasoning_steps: list[dict[str, Any]] = []
    current_objective: str | None = None
    sub_objectives: list[str] = []
    completed_objectives: list[str] = []

    # Tool chaining and memory
    tool_results: dict[str, Any] = {}
    tool_call_history: list[dict[str, Any]] = []
    working_memory: dict[str, Any] = {}

    # Decision making
    decision_points: list[dict[str, Any]] = []
    confidence_scores: dict[str, float] = {}

    # Multi-step planning
    execution_plan: list[dict[str, Any]] = []
    current_plan_step: int = 0

    # Error handling and recovery
    error: str | None = None
    retry_count: int = 0
    recovery_attempts: list[dict[str, Any]] = []

    # Conditional logic state
    conditions_met: dict[str, bool] = {}
    pending_conditions: list[dict[str, Any]] = []


# Enhanced tools for the agent with document search capabilities
@tool
def search_documents_with_sources(
    query: str, user_id: str, document_ids: list[str] | None = None
) -> str:
    """
    Search through user documents with source citation support.

    Args:
        query: Search query string
        user_id: User ID for partitioning
        document_ids: Optional list of specific document IDs to search, if None searches all

    Returns:
        JSON string with search results and source citations
    """
    import json

    try:
        from app.services.azure_search_service import get_azure_search_service

        azure_search = get_azure_search_service()
        partition_key = user_id or "default"

        logger.info(
            f"Starting document search: query='{query}', user_id='{user_id}', document_ids={document_ids}"
        )

        # Perform document search
        if document_ids:
            # Search specific documents
            results = []
            for doc_id in document_ids:
                logger.info(f"Searching in document: {doc_id}")
                doc_results = azure_search.search_documents(
                    query=query, partition_key=partition_key, document_id=doc_id, top=5
                )
                logger.info(f"Found {len(doc_results)} results in document {doc_id}")
                results.extend(doc_results)
        else:
            # Search all user documents
            logger.info("Searching all user documents")
            results = azure_search.search_documents(
                query=query, partition_key=partition_key, top=10
            )

        logger.info(f"Total search results found: {len(results)}")

        if not results:
            return json.dumps(
                {
                    "message": "No relevant documents found for your query.",
                    "query": query,
                    "sources": [],
                    "has_results": False,
                }
            )

        # Extract and format results with source citations
        formatted_results = []
        sources = []

        for result in results:
            # Extract content and metadata
            content = result.get("content", "")
            title = result.get("title", "Unknown Document")
            page_number = result.get("page_number", "Unknown")
            document_id = result.get("document_id", "")
            score = result.get("@search.score", 0)

            logger.info(
                f"Search result: title='{title}', page='{page_number}', "
                f"score={score}, content_preview='{content[:100]}...'"
            )

            # Include results with lower threshold and log more details
            if score > 0.1:  # Lowered threshold from 0.7 to 0.1
                formatted_results.append(
                    {
                        "content": content[:500] + "..." if len(content) > 500 else content,
                        "relevance_score": score,
                    }
                )

                sources.append(
                    {
                        "document_title": title,
                        "page_number": str(page_number),
                        "document_id": document_id,
                        "relevance_score": score,
                    }
                )

        if not formatted_results:
            return json.dumps(
                {
                    "message": "No sufficiently relevant documents found for your query.",
                    "query": query,
                    "sources": [],
                    "has_results": False,
                }
            )

        return json.dumps(
            {
                "message": f"Found {len(formatted_results)} relevant document sections.",
                "query": query,
                "results": formatted_results,
                "sources": sources,
                "has_results": True,
            }
        )

    except Exception as e:
        return json.dumps(
            {
                "error": f"Document search failed: {str(e)}",
                "query": query,
                "sources": [],
                "has_results": False,
            }
        )


@tool
def search_documents(query: str) -> dict[str, Any]:
    """Search for documents related to the query (legacy - use search_documents_with_sources)."""
    # Placeholder for document search - will be implemented in later steps
    return {
        "query": query,
        "results": [],
        "message": "Document search not yet implemented - will be added in step 8",
    }


@tool
def get_weather(location: str) -> dict[str, str]:
    """Get current weather information for a location."""
    # Simple placeholder tool for demonstration
    return {
        "location": location,
        "weather": "sunny",
        "temperature": "22°C",
        "message": f"Weather in {location} is sunny and 22°C (placeholder data)",
    }


class LangGraphAgentService:
    """
    LangGraph-based agent service for complex AI workflows.

    This service orchestrates multi-step AI interactions using LangGraph's
    state machine capabilities, integrating with existing LangChain services.
    """

    def __init__(self, langchain_service: LangChainAIService):
        """
        Initialize the LangGraph agent service.

        Args:
            langchain_service: LangChain service for AI completions
        """
        self.langchain_service = langchain_service
        self.logger = get_logger(__name__)

        # Available MCP tools wrapped for LangChain plus document search tools
        self.tools = get_mcp_tools() + [search_documents_with_sources, get_weather]
        self.tool_node = ToolNode(self.tools)

        # Build the agent workflow
        self.graph = self._build_agent_graph()

        # Wrap agent with Agent Lightning for optimization (zero-code-change pattern)
        self.graph = self._wrap_with_agent_lightning(self.graph)

        self.logger.info(
            "LangGraph agent service initialized with document search capabilities "
            "and Agent Lightning optimization"
        )

    def _build_agent_graph(self) -> StateGraph:
        """Build the agent workflow graph."""
        # Create the state graph
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", self.tool_node)
        graph.add_node("final_response", self._final_response_node)

        # Add edges
        graph.add_edge(START, "agent")
        graph.add_conditional_edges(
            "agent", self._should_continue, {"continue": "tools", "end": "final_response"}
        )
        graph.add_edge("tools", "agent")
        graph.add_edge("final_response", END)

        # Compile the graph
        return graph.compile()

    def _wrap_with_agent_lightning(self, agent: Any) -> Any:
        """
        Wrap the LangGraph agent with Agent Lightning for optimization.

        This implements the zero-code-change pattern: the wrapper preserves
        the agent's API while adding optimization capabilities.

        Args:
            agent: The compiled LangGraph agent to wrap

        Returns:
            Wrapped agent (or original if Agent Lightning unavailable/disabled)
        """
        try:
            from app.core.agent_lightning_config import (
                create_optimization_config,
                is_agent_lightning_available,
            )
            from app.services.agent_wrapper_service import wrap

            # Check if Agent Lightning is available and enabled
            if not is_agent_lightning_available():
                self.logger.info(
                    "Agent Lightning not available or disabled - using unwrapped agent"
                )
                return agent

            # Create optimization config for document QA agent
            # Note: tenant_id here is a fallback default. The wrapper extracts
            # the actual user_id from each request's AgentState dynamically
            config = create_optimization_config(
                agent_name="langgraph_document_qa",
                tenant_id="default",  # Fallback only - wrapper uses user_id from request
                enable_rl=True,
                enable_prompt_opt=False,  # Can enable after baseline established
                enable_sft=False,  # Can enable after training data collected
            )

            # Wrap the agent (preserves API, adds per-request tenant_id extraction)
            wrapped = wrap(agent, config)

            self.logger.info(
                "LangGraph agent wrapped with Agent Lightning",
                agent_name="langgraph_document_qa",
                optimization_algorithms=["rl"],
            )

            return wrapped

        except ImportError as e:
            self.logger.warning(f"Agent Lightning not installed ({e}) - using unwrapped agent")
            return agent
        except Exception as e:
            self.logger.error(
                f"Failed to wrap agent with Agent Lightning: {e} - using unwrapped agent"
            )
            return agent

    async def _collect_execution_metrics(
        self,
        query: str,
        response: str,
        latency_ms: float,
        user_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        """
        Collect execution metrics for Agent Lightning optimization.

        This method is non-blocking and failures don't affect agent execution.

        Args:
            query: User query
            response: Agent response
            latency_ms: Execution latency in milliseconds
            user_id: User identifier (used as tenant_id)
            metadata: Additional metadata from agent execution
        """
        try:
            from app.models.optimization_models import OptimizationConfig
            from app.services.optimization_service import OptimizationDataCollector

            # Extract token usage from metadata if available
            token_usage = 0
            if "search_results" in metadata:
                # Estimate tokens based on response length (rough approximation)
                token_usage = len(response.split()) + len(query.split())

            # Calculate quality signal (confidence score based on response characteristics)
            quality_signal = self._calculate_quality_signal(response, metadata)

            # Use user_id as tenant_id for per-user metrics isolation
            # If no user_id provided, fall back to "default" for backwards compatibility
            tenant_id = user_id or "default"

            # Create optimization config with proper tenant_id
            config = OptimizationConfig(
                tenant_id=tenant_id,
                agent_name="langgraph_document_qa",
            )

            collector = OptimizationDataCollector(config=config)

            # Prepare agent metadata
            agent_metadata = {
                "latency_ms": latency_ms,
                "tokens": token_usage,
                **metadata,
            }

            collector.collect_metrics(
                query={"input": query},
                response={"output": response},
                agent_metadata=agent_metadata,
                quality_signal=quality_signal,
            )

            self.logger.info(
                "Metrics collected for Agent Lightning",
                tenant_id=tenant_id,
                latency_ms=latency_ms,
                token_usage=token_usage,
                quality_signal=quality_signal,
            )

        except Exception as e:
            # Don't let metrics collection failures affect agent execution
            self.logger.warning(
                f"Failed to collect metrics for Agent Lightning: {e}",
                exc_info=True,
            )

    def _calculate_quality_signal(self, response: str, metadata: dict[str, Any]) -> float:
        """
        Calculate quality signal (confidence score) for the response.

        Args:
            response: Agent response text
            metadata: Execution metadata

        Returns:
            Quality signal between 0.0 and 1.0
        """
        # Base quality score
        quality = 0.5

        # Boost if response contains citations (indicates document-grounded answer)
        if "Source:" in response or "Page" in response:
            quality += 0.2

        # Boost if we have search results
        if metadata.get("search_results"):
            quality += 0.15

        # Boost if response is substantive (not an error message)
        if len(response) > 50 and "error" not in response.lower():
            quality += 0.15

        # Ensure between 0.0 and 1.0
        return min(max(quality, 0.0), 1.0)

    async def _agent_node(self, state: AgentState) -> dict[str, Any]:
        """
        Main agent reasoning node with enhanced document search capabilities.

        This node decides what to do next based on the current state and handles
        document-based queries with fact verification and source citations.
        """
        try:
            # Increment step count
            state.step_count += 1

            # Get the latest human message
            human_messages = [msg for msg in state.messages if isinstance(msg, HumanMessage)]
            if not human_messages:
                return {"error": "No human message found"}

            latest_message = human_messages[-1].content
            user_id = state.user_id or "default"

            # Always perform document search to provide sources and citations for every response
            logger.info(f"Starting document search for query: '{latest_message}'")

            try:
                # Use the enhanced document search with source citations
                import json

                search_result_str = search_documents_with_sources.invoke(
                    {
                        "query": latest_message,
                        "user_id": user_id,
                        "document_ids": state.selected_document_ids,
                    }
                )

                search_result = json.loads(search_result_str)

                if search_result.get("has_results", False):
                    # Found relevant documents - generate a fact-based response
                    results = search_result.get("results", [])
                    sources = search_result.get("sources", [])

                    # Combine relevant content for context
                    context_content = "\n\n".join(
                        [
                            f"From {src.get('document_title', 'Unknown')} (Page {src.get('page_number', 'Unknown')}): {result.get('content', '')}"
                            for result, src in zip(results, sources, strict=True)
                        ]
                    )

                    # Generate response using LangChain with document context
                    system_prompt = """You are a helpful AI assistant that provides accurate information based strictly on the provided document content.

Guidelines:
- Only use information that is explicitly stated in the provided documents
- Do not make assumptions or add information not found in the documents
- ALWAYS include inline citations in your response using the format: (Source: Document Title, Page X)
- After each factual statement, cite the specific document and page where you found that information
- If the documents don't contain enough information to answer the question, state this clearly
- Be concise but comprehensive in your response
- Use the exact document titles and page numbers provided in the document excerpts"""

                    user_prompt = f"""Based on the following document excerpts, please answer this question: {latest_message}

Document Content:
{context_content}

Please provide a response that:
1. Answers the question using only the information from these documents
2. Includes inline citations after each fact using the format: (Source: Document Title, Page X)
3. States if the documents don't contain sufficient information to fully answer the question

Remember to cite your sources inline throughout your response, not just at the end."""

                    # Use LangChain service to generate the response
                    ai_response = await self.langchain_service.chat_completion(
                        message=user_prompt,
                        context=system_prompt,
                        user_id=user_id,
                        session_id=state.session_id,
                    )

                    # Format the final response with citations
                    citations_text = "\n\n**Sources:**\n" + "\n".join(
                        [
                            f"- {src.get('document_title', 'Unknown Document')}, Page {src.get('page_number', 'Unknown')}"
                            for src in sources
                        ]
                    )

                    final_response = ai_response + citations_text

                    # Store document sources in state
                    state.document_sources = sources

                    ai_message = AIMessage(content=final_response)
                    return {
                        "messages": [ai_message],
                        "final_answer": final_response,
                        "document_sources": sources,
                    }

                else:
                    # No relevant documents found - still try to provide a helpful response with LangChain
                    # but note that no sources were found
                    no_docs_message = search_result.get(
                        "message", "No relevant documents found for your query."
                    )

                    # Use LangChain service but indicate no document sources
                    no_docs_context = (
                        "You are a helpful AI assistant. Please provide a helpful response "
                        "to the user's question. Note that no relevant documents were found "
                        "in the user's document collection for this query."
                    )
                    response = await self.langchain_service.chat_completion(
                        message=latest_message,
                        context=no_docs_context,
                        user_id=user_id,
                        session_id=state.session_id,
                    )

                    # Add note about no sources found
                    if state.selected_document_ids:
                        source_note = (
                            f"\n\n*Note: I searched through the selected documents but "
                            f"{no_docs_message.lower()}*"
                        )
                    else:
                        source_note = (
                            f"\n\n*Note: I searched through all your documents but "
                            f"{no_docs_message.lower()}*"
                        )

                    final_response = response + source_note
                    ai_message = AIMessage(content=final_response)
                    return {"messages": [ai_message], "final_answer": final_response}

            except Exception as doc_error:
                logger.error(f"Document search error: {doc_error}")
                # Fall back to regular LangChain response if document search fails
                try:
                    fallback_context = (
                        "You are a helpful AI assistant. Please provide a helpful response "
                        "to the user's question."
                    )
                    response = await self.langchain_service.chat_completion(
                        message=latest_message,
                        context=fallback_context,
                        user_id=user_id,
                        session_id=state.session_id,
                    )
                    error_note = (
                        "\n\n*Note: There was an error searching documents, so this response "
                        "is not based on your document collection.*"
                    )
                    final_response = response + error_note
                    ai_message = AIMessage(content=final_response)
                    return {"messages": [ai_message], "final_answer": final_response}
                except Exception as fallback_error:
                    logger.error(f"Fallback response error: {fallback_error}")
                    error_response = (
                        "I encountered an error while processing your request. "
                        "Please try rephrasing your question."
                    )
                    ai_message = AIMessage(content=error_response)
                    return {"messages": [ai_message], "final_answer": error_response}

        except Exception as e:
            self.logger.error(f"Error in agent node: {e}")
            return {"error": str(e), "retry_count": state.retry_count + 1}

    def _should_use_tool(self, user_message: str, ai_response: str) -> bool:
        """Determine if tools should be used based on the message content."""
        # Simple keyword-based detection
        tool_keywords = {
            "weather": ["weather", "temperature", "forecast", "climate"],
            "search": ["search", "find", "document", "documents", "look up"],
        }

        user_lower = user_message.lower()
        for _tool_type, keywords in tool_keywords.items():
            if any(keyword in user_lower for keyword in keywords):
                return True

        return False

    def _extract_tool_call(self, message: str) -> tuple[str | None, dict[str, Any]]:
        """Extract tool name and arguments from message."""
        message_lower = message.lower()

        # Weather tool detection
        if any(word in message_lower for word in ["weather", "temperature", "forecast"]):
            # Extract location - simple approach
            location = "Vancouver"  # Default location
            if "in " in message_lower:
                parts = message_lower.split("in ")
                if len(parts) > 1:
                    location = parts[1].split()[0].strip()

            return "get_weather", {"location": location}

        # Document search detection
        if any(word in message_lower for word in ["search", "find", "document"]):
            return "search_documents", {"query": message}

        return None, {}

    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to continue with tools or end the workflow."""
        last_message = state.messages[-1] if state.messages else None

        # If there's an error and retries are exhausted, end
        if state.error and state.retry_count >= 3:
            return "end"

        # Prevent infinite loops - limit to 5 steps
        if state.step_count >= 5:
            return "end"

        # If the last message is from AI and has tool calls, continue with tools
        if (
            isinstance(last_message, AIMessage)
            and hasattr(last_message, "tool_calls")
            and last_message.tool_calls
            and len(last_message.tool_calls) > 0
        ):
            return "continue"

        # If we have a final answer, end
        if state.final_answer:
            return "end"

        # Default to ending
        return "end"

    async def _final_response_node(self, state: AgentState) -> dict[str, Any]:
        """Generate the final response to the user."""
        try:
            # If we already have a final answer, use it
            if state.final_answer:
                return {"final_answer": state.final_answer}

            # If there was an error, provide an error response
            if state.error:
                error_response = (
                    "I apologize, but I encountered an error while processing your request. "
                    "Please try again or contact support if the issue persists."
                )
                return {"final_answer": error_response}

            # Get the last AI message as the final response
            ai_messages = [msg for msg in state.messages if isinstance(msg, AIMessage)]
            if ai_messages:
                return {"final_answer": ai_messages[-1].content}

            # Fallback response
            fallback_response = (
                "I'm here to help with your questions about BC Government services. "
                "How can I assist you today?"
            )
            return {"final_answer": fallback_response}

        except Exception as e:
            self.logger.error(f"Error in final response node: {e}")
            error_response = (
                "I apologize, but I encountered an error while generating my response. "
                "Please try again."
            )
            return {"final_answer": error_response}

    async def process_message(
        self,
        message: str,
        user_id: str | None = None,
        session_id: str | None = None,
        context: str | None = None,
        selected_document_ids: list[str] | None = None,
    ) -> str:
        """
        Process a user message through the LangGraph agent workflow with document support.

        Args:
            message: User's message
            user_id: User identifier for memory
            session_id: Session identifier for memory
            context: Optional context for the conversation
            selected_document_ids: Optional list of document IDs to search, if None searches all

        Returns:
            Final agent response with document citations if applicable
        """
        start_time = time.time()

        try:
            # Create initial state with document context
            initial_state = AgentState(
                messages=[HumanMessage(content=message)],
                user_id=user_id,
                session_id=session_id,
                workflow_id=str(uuid.uuid4()),
                context=context,
                selected_document_ids=selected_document_ids,
                search_all_documents=selected_document_ids is None,
            )

            search_scope = (
                "all documents"
                if selected_document_ids is None
                else f"{len(selected_document_ids)} selected documents"
            )
            self.logger.info(
                f"Starting LangGraph workflow for message: {message[:100]}... "
                f"(searching {search_scope})"
            )

            # Run the workflow
            result = await self.graph.ainvoke(initial_state)

            # Extract final answer
            final_answer = result.get("final_answer", "I'm sorry, I couldn't process your request.")

            # Calculate execution time
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            self.logger.info(
                f"LangGraph workflow completed in {result.get('step_count', 0)} steps "
                f"({latency_ms:.2f}ms)"
            )

            # Collect metrics for Agent Lightning optimization (non-blocking)
            await self._collect_execution_metrics(
                query=message,
                response=final_answer,
                latency_ms=latency_ms,
                user_id=user_id,
                metadata=result,
            )

            return final_answer

        except Exception as e:
            self.logger.error(f"Error in LangGraph workflow: {e}")
            return (
                "I apologize, but I encountered an error while processing your request. "
                "Please try again or contact support if the issue persists."
            )

    async def stream_message(
        self,
        message: str,
        user_id: str | None = None,
        session_id: str | None = None,
        context: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream an agent conversation through the LangGraph workflow.

        Args:
            message: User message to process
            user_id: User identifier for personalization
            session_id: Session identifier for conversation history
            context: Additional context for the conversation

        Yields:
            Dictionary containing streaming updates with workflow progress
        """
        try:
            # Create initial state
            initial_state = AgentState(
                messages=[HumanMessage(content=message)],
                user_id=user_id,
                session_id=session_id,
                workflow_id=str(uuid.uuid4()),
                context=context,
            )

            self.logger.info(f"Starting streaming agent workflow for message: {message[:100]}")

            # Yield initial status
            yield {
                "event": "workflow_start",
                "node": None,
                "data": {
                    "workflow_id": initial_state.workflow_id,
                    "status": "Starting agent processing...",
                },
                "timestamp": time.time(),
            }

            # Stream the workflow using LangGraph's astream
            current_node = None

            async for update in self.graph.astream(initial_state):
                # LangGraph astream yields node updates
                for node_name, node_output in update.items():
                    if node_name != current_node:
                        # Node started
                        if current_node:
                            yield {
                                "event": "node_end",
                                "node": current_node,
                                "data": {},
                                "timestamp": time.time(),
                            }

                        current_node = node_name
                        yield {
                            "event": "node_start",
                            "node": node_name,
                            "data": self._get_agent_node_status(node_name),
                            "timestamp": time.time(),
                        }

                    # Check for streaming content in agent response
                    if node_name == "agent" and hasattr(node_output, "get"):
                        # If this is a streaming response, yield chunks
                        if "streaming_content" in node_output:
                            async for chunk in node_output["streaming_content"]:
                                yield {
                                    "event": "streaming_content",
                                    "node": node_name,
                                    "data": {"chunk": chunk},
                                    "timestamp": time.time(),
                                }

            # Final node completion
            if current_node:
                yield {
                    "event": "node_end",
                    "node": current_node,
                    "data": {},
                    "timestamp": time.time(),
                }

            # Get final result
            final_result = await self.graph.ainvoke(initial_state)
            final_answer = final_result.get("final_answer", "Unable to generate response")

            # Yield completion
            yield {
                "event": "workflow_complete",
                "node": None,
                "data": {
                    "final_answer": final_answer,
                    "status": "Agent processing completed successfully",
                    "step_count": final_result.get("step_count", 0),
                },
                "timestamp": time.time(),
            }

            self.logger.info("Streaming agent workflow completed")

        except Exception as e:
            self.logger.error(f"Error in streaming agent workflow: {e}")

            yield {
                "event": "error",
                "node": None,
                "data": {
                    "error": str(e),
                    "status": "An error occurred while processing your request",
                },
                "timestamp": time.time(),
            }

    def _get_agent_node_status(self, node_name: str) -> dict[str, str]:
        """Get user-friendly status message for each agent node."""
        status_messages = {
            "agent": {"status": "Processing your request..."},
            "tools": {"status": "Using tools to help answer your question..."},
            "final_response": {"status": "Preparing final response..."},
        }
        return status_messages.get(node_name, {"status": f"Processing {node_name}..."})


# Global service instance
_langgraph_agent_service: LangGraphAgentService | None = None


def get_langgraph_agent_service() -> LangGraphAgentService:
    """Get the global LangGraph agent service instance."""
    global _langgraph_agent_service
    if _langgraph_agent_service is None:
        from app.services.langchain_service import get_langchain_ai_service

        langchain_service = get_langchain_ai_service()
        _langgraph_agent_service = LangGraphAgentService(langchain_service)
    return _langgraph_agent_service
