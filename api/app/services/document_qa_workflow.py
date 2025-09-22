"""
LangGraph workflow service for document Q&A processing.
This service provides a sophisticated document Q&A workflow using LangGraph with:
- Document retrieval and validation nodes
- Context analysis and filtering
- Response generation with citations
- Error handling and fallbacks
"""

import time
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from app.core.logger import get_logger
from app.services.azure_search_service import get_azure_search_service
from app.services.langchain_service import LangChainAIService


class DocumentQAState(BaseModel):
    """State object for the Document Q&A workflow."""

    # Input parameters
    document_id: str | None = None
    question: str | None = None
    user_id: str | None = None
    # Workflow metadata
    workflow_id: str | None = None
    step_count: int = 0
    # Document retrieval results
    document_metadata: dict[str, Any] | None = None
    document_chunks: list[dict[str, Any]] | None = None
    # Context analysis results
    relevant_context: str | None = None
    context_score: float = 0.0
    selected_chunks: list[dict[str, Any]] | None = None
    # Response generation
    messages: Annotated[list[BaseMessage], add_messages]
    final_answer: str | None = None
    citations: list[dict[str, str]] | None = None
    # Error handling
    error: str | None = None
    retry_count: int = 0
    fallback_used: bool = False


class DocumentQAWorkflowService:
    """
    LangGraph-based document Q&A workflow service.
    This service orchestrates complex document-based question answering using
    LangGraph's state machine capabilities with specialized nodes for each step.
    """

    def __init__(self, langchain_service: LangChainAIService):
        """
        Initialize the Document Q&A workflow service.
        Args:
            langchain_service: LangChain service for AI completions
        """
        self.langchain_service = langchain_service
        self.azure_search_service = get_azure_search_service()
        self.logger = get_logger(__name__)

        # Import observability service here to avoid circular imports
        from app.services.workflow_observability import get_workflow_observability_service

        self.observability = get_workflow_observability_service()

        # Build the document Q&A workflow
        self.graph = self._build_workflow_graph()
        self.logger.info("DocumentQAWorkflowService initialized")

    def _build_workflow_graph(self) -> StateGraph:
        """Build the document Q&A workflow graph."""
        # Create the state graph
        graph = StateGraph(DocumentQAState)
        # Add workflow nodes
        graph.add_node("retrieve_document", self._retrieve_document_node)
        graph.add_node("analyze_context", self._analyze_context_node)
        graph.add_node("generate_response", self._generate_response_node)
        graph.add_node("handle_error", self._handle_error_node)
        # Add edges
        graph.add_edge(START, "retrieve_document")
        graph.add_conditional_edges(
            "retrieve_document",
            self._should_continue_after_retrieval,
            {
                "continue": "analyze_context",
                "error": "handle_error",
            },
        )
        graph.add_conditional_edges(
            "analyze_context",
            self._should_continue_after_analysis,
            {
                "continue": "generate_response",
                "error": "handle_error",
            },
        )
        graph.add_edge("generate_response", END)
        graph.add_edge("handle_error", END)
        # Compile the graph
        return graph.compile()

    async def _retrieve_document_node(self, state: DocumentQAState) -> dict[str, Any]:
        """
        Document retrieval node.
        Retrieves document metadata and chunks from Azure AI Search and Cosmos DB.
        """
        execution_id = self.observability.start_node_execution(
            workflow_id=state.workflow_id,
            node_name="retrieve_document",
            input_data={"document_id": state.document_id, "user_id": state.user_id},
        )

        try:
            state.step_count += 1
            self.logger.info(f"Retrieving document: {state.document_id}")

            # Get document metadata from Azure AI Search
            partition_key = state.user_id or "default"
            document = self.azure_search_service.get_document(state.document_id, partition_key)

            if not document:
                error = ValueError("Document not found")
                self.observability.complete_node_execution(
                    workflow_id=state.workflow_id,
                    execution_id=execution_id,
                    error=error,
                )
                return {"error": "Document not found", "retry_count": state.retry_count + 1}

            # Get document chunks from Cosmos DB
            from app.services.document_service import get_document_service

            document_service = get_document_service()
            chunks = await document_service._get_document_chunks(state.document_id, partition_key)

            if not chunks:
                error = ValueError("No document chunks found")
                self.observability.complete_node_execution(
                    workflow_id=state.workflow_id,
                    execution_id=execution_id,
                    error=error,
                )
                return {"error": "No document chunks found", "retry_count": state.retry_count + 1}

            filename = document.get("filename", state.document_id)
            self.logger.info(f"Retrieved {len(chunks)} chunks for document: {filename}")

            result = {
                "document_metadata": document,
                "document_chunks": chunks,
            }

            self.observability.complete_node_execution(
                workflow_id=state.workflow_id,
                execution_id=execution_id,
                output_data={"chunks_count": len(chunks), "filename": filename},
            )

            return result

        except Exception as e:
            self.observability.complete_node_execution(
                workflow_id=state.workflow_id,
                execution_id=execution_id,
                error=e,
            )
            self.logger.error(f"Error in retrieve_document_node: {e}")
            return {"error": str(e), "retry_count": state.retry_count + 1}

    async def _analyze_context_node(self, state: DocumentQAState) -> dict[str, Any]:
        """
        Context analysis node.
        Analyzes document chunks to find the most relevant context for the question.
        """
        execution_id = self.observability.start_node_execution(
            workflow_id=state.workflow_id,
            node_name="analyze_context",
            input_data={
                "question": state.question[:100],
                "chunks_count": len(state.document_chunks) if state.document_chunks else 0,
            },
        )

        try:
            state.step_count += 1
            self.logger.info(f"Analyzing context for question: {state.question[:100]}...")
            chunks = state.document_chunks or []

            if not chunks:
                error = ValueError("No chunks available for analysis")
                self.observability.complete_node_execution(
                    workflow_id=state.workflow_id,
                    execution_id=execution_id,
                    error=error,
                )
                return {
                    "error": "No chunks available for analysis",
                    "retry_count": state.retry_count + 1,
                }

            # Use the document service's context finding logic
            from app.services.document_service import get_document_service

            document_service = get_document_service()

            # Find relevant context using vector search
            relevant_context = await document_service._find_relevant_context(
                state.question, chunks, top_k=3
            )

            if not relevant_context or len(relevant_context.strip()) < 50:
                # Fallback to using all chunks if vector search fails
                self.logger.warning("Vector search returned insufficient context, using fallback")
                relevant_context = "\n\n".join(chunk.get("content", "") for chunk in chunks[:5])
                fallback_used = True
            else:
                fallback_used = False

            # Calculate a simple context relevance score
            context_score = min(len(relevant_context) / 1000, 1.0)  # Simple heuristic

            # Extract citations from selected chunks
            citations = []
            for i, chunk in enumerate(chunks[:3]):  # Top 3 chunks for citations
                if chunk.get("content", "").strip():
                    citations.append(
                        {
                            "chunk_id": chunk.get("id", f"chunk_{i}"),
                            "page": str(chunk.get("page_number", i + 1)),
                            "content_preview": chunk.get("content", "")[:100] + "...",
                        }
                    )

            context_len = len(relevant_context)
            self.logger.info(
                f"Context analysis complete: {context_len} chars, score: {context_score:.2f}"
            )

            result = {
                "relevant_context": relevant_context,
                "context_score": context_score,
                "citations": citations,
                "fallback_used": fallback_used,
            }

            self.observability.complete_node_execution(
                workflow_id=state.workflow_id,
                execution_id=execution_id,
                output_data={
                    "context_length": context_len,
                    "relevance_score": context_score,
                    "citations_count": len(citations),
                    "fallback_used": fallback_used,
                },
            )

            return result

        except Exception as e:
            self.observability.complete_node_execution(
                workflow_id=state.workflow_id,
                execution_id=execution_id,
                error=e,
            )
            self.logger.error(f"Error in analyze_context_node: {e}")
            return {"error": str(e), "retry_count": state.retry_count + 1}

    async def _generate_response_node(self, state: DocumentQAState) -> dict[str, Any]:
        """
        Response generation node.
        Generates the final answer using the analyzed context and adds citations.
        """
        execution_id = self.observability.start_node_execution(
            workflow_id=state.workflow_id,
            node_name="generate_response",
            input_data={
                "question": state.question[:100],
                "context_length": len(state.relevant_context) if state.relevant_context else 0,
                "citations_count": len(state.citations) if state.citations else 0,
            },
        )

        try:
            state.step_count += 1
            self.logger.info("Generating response with LangChain")

            # Prepare the prompt with BC Government guidelines
            bc_gov_guidelines = """
You are an AI assistant for the BC Government's Natural Resource Ministries.
Follow these guidelines:
- Provide accurate, helpful, and professional responses
- Only provide information that can be found in the provided document content
- If information is not available in the document, clearly state
  "This information is not available in the provided document"
- Be concise but thorough in your explanations
- Maintain a professional and respectful tone
"""
            prompt = f"""{bc_gov_guidelines}
DOCUMENT CONTENT:
{state.relevant_context}

QUESTION: {state.question}

Please provide a response based solely on the document content above,
following the BC Government guidelines:"""

            # Generate response using LangChain service
            response = await self.langchain_service.chat_completion(
                message=prompt,
                context="Document Q&A workflow",
                session_id=state.workflow_id,
                user_id=state.user_id,
            )

            # Add citation information if available
            if state.citations:
                citation_text = "\n\n**Sources:**\n"
                for i, citation in enumerate(state.citations[:3], 1):
                    page = citation["page"]
                    preview = citation["content_preview"]
                    citation_text += f"{i}. Page {page}: {preview}\n"
                response += citation_text

            # Add fallback notice if used
            if state.fallback_used:
                response += "\n\n*Note: Limited context analysis was used for this response.*"

            self.logger.info("Response generation complete")

            result = {
                "final_answer": response,
                "messages": [AIMessage(content=response)],
            }

            self.observability.complete_node_execution(
                workflow_id=state.workflow_id,
                execution_id=execution_id,
                output_data={
                    "response_length": len(response),
                    "citations_added": len(state.citations) if state.citations else 0,
                    "fallback_notice_added": state.fallback_used,
                },
            )

            return result

        except Exception as e:
            self.observability.complete_node_execution(
                workflow_id=state.workflow_id,
                execution_id=execution_id,
                error=e,
            )
            self.logger.error(f"Error in generate_response_node: {e}")
            return {"error": str(e), "retry_count": state.retry_count + 1}

    async def _generate_streaming_response_node(self, state: DocumentQAState) -> dict[str, Any]:
        """
        Streaming response generation node.
        Generates streaming response using LangChain service for real-time output.
        """
        execution_id = self.observability.start_node_execution(
            workflow_id=state.workflow_id,
            node_name="generate_streaming_response",
            input_data={
                "question": state.question[:100],
                "context_length": len(state.relevant_context) if state.relevant_context else 0,
                "citations_count": len(state.citations) if state.citations else 0,
            },
        )

        try:
            state.step_count += 1
            self.logger.info("Generating streaming response with LangChain")

            # Prepare the prompt with BC Government guidelines
            bc_gov_guidelines = """
You are an AI assistant for the BC Government's Natural Resource Ministries.
Follow these guidelines:
- Provide accurate, helpful, and professional responses
- Only provide information that can be found in the provided document content
- If information is not available in the document, clearly state
  "This information is not available in the provided document"
- Be concise but thorough in your explanations
- Maintain a professional and respectful tone
"""
            prompt = f"""{bc_gov_guidelines}
DOCUMENT CONTENT:
{state.relevant_context}

QUESTION: {state.question}

Please provide a response based solely on the document content above,
following the BC Government guidelines:"""

            # Create an async generator for streaming content
            async def stream_content():
                try:
                    # Stream the AI response
                    async for chunk in self.langchain_service.stream_chat_completion(
                        message=prompt,
                        context="Document Q&A streaming workflow",
                        session_id=state.workflow_id,
                        user_id=state.user_id,
                    ):
                        yield chunk

                    # Add citation information if available
                    if state.citations:
                        yield "\n\n**Sources:**\n"
                        for i, citation in enumerate(state.citations[:3], 1):
                            page = citation["page"]
                            preview = citation["content_preview"]
                            yield f"{i}. Page {page}: {preview}\n"

                    # Add fallback notice if used
                    if state.fallback_used:
                        yield "\n\n*Note: Limited context analysis was used for this response.*"

                except Exception as e:
                    self.logger.error(f"Error in streaming response generation: {e}")
                    yield f"\n\nError generating response: {str(e)}"

            result = {
                "streaming_content": stream_content(),
                "messages": [AIMessage(content="[Streaming response]")],
            }

            self.observability.complete_node_execution(
                workflow_id=state.workflow_id,
                execution_id=execution_id,
                output_data={
                    "streaming_enabled": True,
                    "citations_count": len(state.citations) if state.citations else 0,
                    "fallback_notice_added": state.fallback_used,
                },
            )

            return result

        except Exception as e:
            self.observability.complete_node_execution(
                workflow_id=state.workflow_id,
                execution_id=execution_id,
                error=e,
            )
            self.logger.error(f"Error in generate_streaming_response_node: {e}")
            return {"error": str(e), "retry_count": state.retry_count + 1}

    async def _handle_error_node(self, state: DocumentQAState) -> dict[str, Any]:
        """
        Error handling node.
        Provides appropriate error responses and fallbacks.
        """
        execution_id = self.observability.start_node_execution(
            workflow_id=state.workflow_id,
            node_name="handle_error",
            input_data={
                "error": state.error,
                "retry_count": state.retry_count,
                "step_count": state.step_count,
            },
        )

        try:
            self.logger.warning(f"Handling error: {state.error}")

            # Determine error response based on error type
            if "Document not found" in (state.error or ""):
                error_response = (
                    "I'm sorry, but I couldn't find the requested document. "
                    "Please verify the document ID and try again."
                )
                error_type = "document_not_found"
            elif "No document chunks" in (state.error or ""):
                error_response = (
                    "I found the document but couldn't access its content. "
                    "The document may not have been processed yet."
                )
                error_type = "document_chunks_missing"
            elif state.retry_count >= 3:
                error_response = (
                    "I'm experiencing technical difficulties processing your request. "
                    "Please try again later or contact support if the issue persists."
                )
                error_type = "max_retries_exceeded"
            else:
                error_response = (
                    "I encountered an error while processing your question about the document. "
                    "Please try rephrasing your question or try again."
                )
                error_type = "general_error"

            result = {
                "final_answer": error_response,
                "messages": [AIMessage(content=error_response)],
            }

            self.observability.complete_node_execution(
                workflow_id=state.workflow_id,
                execution_id=execution_id,
                output_data={
                    "error_type": error_type,
                    "response_length": len(error_response),
                    "retry_count": state.retry_count,
                },
            )

            return result

        except Exception as e:
            self.observability.complete_node_execution(
                workflow_id=state.workflow_id,
                execution_id=execution_id,
                error=e,
            )
            self.logger.error(f"Error in handle_error_node: {e}")
            fallback_response = (
                "I'm sorry, but I'm unable to process your document question at this time. "
                "Please try again later."
            )
            return {
                "final_answer": fallback_response,
                "messages": [AIMessage(content=fallback_response)],
            }

    def _should_continue_after_retrieval(self, state: DocumentQAState) -> str:
        """Decide whether to continue after document retrieval."""
        if state.error and state.retry_count >= 3:
            return "error"
        if state.error:
            return "error"
        if not state.document_metadata or not state.document_chunks:
            return "error"
        return "continue"

    def _should_continue_after_analysis(self, state: DocumentQAState) -> str:
        """Decide whether to continue after context analysis."""
        if state.error and state.retry_count >= 3:
            return "error"
        if state.error:
            return "error"
        if not state.relevant_context:
            return "error"
        return "continue"

    async def process_document_question(
        self,
        document_id: str,
        question: str,
        user_id: str | None = None,
    ) -> str:
        """
        Process a document question through the LangGraph workflow.
        Args:
            document_id: ID of the document to query
            question: Question to ask about the document
            user_id: User identifier for access control
        Returns:
            Final answer to the question
        """
        workflow_execution = None
        try:
            # Create initial state
            initial_state = DocumentQAState(
                document_id=document_id,
                question=question,
                user_id=user_id,
                workflow_id=str(uuid.uuid4()),
                messages=[HumanMessage(content=question)],
            )

            # Start workflow tracking
            workflow_execution = self.observability.start_workflow_tracking(
                workflow_id=initial_state.workflow_id,
                workflow_type="document_qa",
                user_id=user_id,
                input_parameters={
                    "document_id": document_id,
                    "question": question[:100] + "..." if len(question) > 100 else question,
                },
            )

            self.logger.info(f"Starting Document Q&A workflow for document: {document_id}")

            # Run the workflow
            result = await self.graph.ainvoke(initial_state)

            # Extract final answer
            default_error = "I'm sorry, I couldn't process your question about the document."
            final_answer = result.get("final_answer", default_error)
            step_count = result.get("step_count", 0)

            # Complete workflow tracking
            final_output_truncated = (
                final_answer[:200] + "..." if len(final_answer) > 200 else final_answer
            )
            self.observability.complete_workflow(
                workflow_id=initial_state.workflow_id,
                final_output=final_output_truncated,
            )

            self.logger.info(f"Document Q&A workflow completed in {step_count} steps")
            return final_answer

        except Exception as e:
            # Complete workflow tracking with error
            if workflow_execution:
                self.observability.complete_workflow(
                    workflow_id=workflow_execution.workflow_id,
                    error=e,
                )

            self.logger.error(f"Error in Document Q&A workflow: {e}")
            return (
                "I apologize, but I encountered an error while processing your "
                "question about the document. "
                "Please try again or contact support if the issue persists."
            )

    async def stream_document_question(
        self,
        document_id: str,
        question: str,
        user_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream a document question through the LangGraph workflow.

        Args:
            document_id: ID of the document to query
            question: Question to ask about the document
            user_id: User identifier for access control

        Yields:
            Dictionary containing streaming updates with:
            - event: The type of update (node_start, node_end, workflow_complete, error)
            - node: The current node name
            - data: Any relevant data for the update
            - timestamp: When the update occurred
        """
        workflow_execution = None

        try:
            # Create initial state
            initial_state = DocumentQAState(
                document_id=document_id,
                question=question,
                user_id=user_id,
                workflow_id=str(uuid.uuid4()),
                messages=[HumanMessage(content=question)],
            )

            # Start workflow tracking
            workflow_execution = self.observability.start_workflow_tracking(
                workflow_id=initial_state.workflow_id,
                workflow_type="document_qa_streaming",
                user_id=user_id,
                input_parameters={
                    "document_id": document_id,
                    "question": question[:100] + "..." if len(question) > 100 else question,
                },
            )

            self.logger.info(
                f"Starting streaming Document Q&A workflow for document: {document_id}"
            )

            # Yield initial status
            yield {
                "event": "workflow_start",
                "node": None,
                "data": {
                    "workflow_id": initial_state.workflow_id,
                    "status": "Starting document analysis...",
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
                            "data": self._get_node_status_message(node_name),
                            "timestamp": time.time(),
                        }

                    # Check for streaming content in response generation
                    if node_name == "generate_response" and hasattr(node_output, "get"):
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

            # Complete workflow tracking
            final_output_truncated = (
                final_answer[:200] + "..." if len(final_answer) > 200 else final_answer
            )
            self.observability.complete_workflow(
                workflow_id=initial_state.workflow_id,
                final_output=final_output_truncated,
            )

            # Yield completion
            yield {
                "event": "workflow_complete",
                "node": None,
                "data": {
                    "final_answer": final_answer,
                    "status": "Document Q&A completed successfully",
                },
                "timestamp": time.time(),
            }

            self.logger.info("Streaming Document Q&A workflow completed")

        except Exception as e:
            # Complete workflow tracking with error
            if workflow_execution:
                self.observability.complete_workflow(
                    workflow_id=workflow_execution.workflow_id,
                    error=e,
                )

            self.logger.error(f"Error in streaming Document Q&A workflow: {e}")

            yield {
                "event": "error",
                "node": None,
                "data": {
                    "error": str(e),
                    "status": "An error occurred while processing your question",
                },
                "timestamp": time.time(),
            }

    def _get_node_status_message(self, node_name: str) -> dict[str, str]:
        """Get user-friendly status message for each node."""
        status_messages = {
            "retrieve_document": {"status": "Retrieving document information..."},
            "analyze_context": {"status": "Analyzing document content for relevant information..."},
            "generate_response": {"status": "Generating response..."},
            "handle_error": {"status": "Handling error..."},
        }
        return status_messages.get(node_name, {"status": f"Processing {node_name}..."})


# Global service instance
_document_qa_workflow_service: DocumentQAWorkflowService | None = None


def get_document_qa_workflow_service() -> DocumentQAWorkflowService:
    """Get the global Document Q&A workflow service instance."""
    global _document_qa_workflow_service
    if _document_qa_workflow_service is None:
        from app.services.langchain_service import get_langchain_ai_service

        langchain_service = get_langchain_ai_service()
        _document_qa_workflow_service = DocumentQAWorkflowService(langchain_service)
    return _document_qa_workflow_service
