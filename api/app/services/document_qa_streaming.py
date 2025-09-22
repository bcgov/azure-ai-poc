"""
Streaming version of the Document Q&A workflow service.
This service provides streaming capabilities for the Document Q&A workflow,
allowing real-time response generation for better user experience.
"""

import json
import uuid
from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage

from app.core.logger import get_logger
from app.services.document_qa_workflow import DocumentQAState, get_document_qa_workflow_service
from app.services.langchain_service import get_langchain_ai_service


class DocumentQAStreamingService:
    """
    Streaming service for Document Q&A workflow.
    This service provides real-time streaming responses for document-based
    question answering using the LangGraph workflow with streaming capabilities.
    """

    def __init__(self):
        """Initialize the streaming service."""
        self.workflow_service = get_document_qa_workflow_service()
        self.langchain_service = get_langchain_ai_service()
        self.logger = get_logger(__name__)
        self.logger.info("DocumentQAStreamingService initialized")

    async def stream_document_question(
        self,
        document_id: str,
        question: str,
        user_id: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream a document question response through the LangGraph workflow.

        This method uses LangGraph's native streaming capabilities for real-time
        workflow execution and response generation.

        Args:
            document_id: ID of the document to query
            question: Question to ask about the document
            user_id: User identifier for access control

        Yields:
            Streaming response chunks formatted for Server-Sent Events (SSE)
        """
        try:
            workflow_id = str(uuid.uuid4())
            self.logger.info(
                f"Starting streaming Document Q&A workflow for document: {document_id}"
            )

            # Stream the workflow using the enhanced workflow service
            async for update in self.workflow_service.stream_document_question(
                document_id=document_id,
                question=question,
                user_id=user_id,
            ):
                event = update.get("event")
                node = update.get("node")
                data = update.get("data", {})

                # Format different types of updates
                if event == "workflow_start":
                    yield f"data: {data.get('status', 'Starting...')}\n\n"

                elif event == "node_start":
                    status = data.get("status", f"Processing {node}...")
                    yield f"data: {status}\n\n"

                elif event == "streaming_content":
                    # Real-time streaming content from response generation
                    chunk = data.get("chunk", "")
                    if chunk.strip():
                        yield f"data: {chunk}\n\n"

                elif event == "workflow_complete":
                    # Final completion message
                    final_answer = data.get("final_answer", "")
                    # If we haven't streamed content, send the final answer
                    has_streamed = any(
                        "streaming_content" in str(prev_update) for prev_update in []
                    )
                    if final_answer and not has_streamed:
                        yield f"data: {final_answer}\n\n"
                    yield f"data: {data.get('status', 'Completed')}\n\n"

                elif event == "error":
                    error_message = data.get("status", "An error occurred")
                    yield f"data: Error: {error_message}\n\n"

            self.logger.info("Streaming Document Q&A workflow completed")

        except Exception as e:
            self.logger.error(f"Error in streaming Document Q&A workflow: {e}")
            yield (
                "data: I apologize, but I encountered an error while processing your "
                "question about the document. Please try again.\n\n"
            )

    async def stream_document_question_enhanced(
        self,
        document_id: str,
        question: str,
        user_id: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Enhanced streaming with more detailed workflow updates.

        This method provides detailed progress updates and handles streaming
        response generation with better error handling and observability.

        Args:
            document_id: ID of the document to query
            question: Question to ask about the document
            user_id: User identifier for access control

        Yields:
            JSON-formatted streaming updates with detailed workflow information
        """
        try:
            workflow_id = str(uuid.uuid4())
            self.logger.info(f"Starting enhanced streaming for document: {document_id}")

            # Send initial status
            yield self._format_json_update(
                {
                    "type": "status",
                    "message": "Initializing document analysis...",
                    "workflow_id": workflow_id,
                    "progress": 0,
                }
            )

            progress = 0
            total_steps = 4  # retrieve, analyze, generate, complete

            # Stream the workflow using the enhanced workflow service
            async for update in self.workflow_service.stream_document_question(
                document_id=document_id,
                question=question,
                user_id=user_id,
            ):
                event = update.get("event")
                node = update.get("node")
                data = update.get("data", {})

                # Update progress based on workflow state
                if event == "node_start":
                    progress += 1
                    node_messages = {
                        "retrieve_document": "Retrieving document information...",
                        "analyze_context": "Analyzing document content...",
                        "generate_response": "Generating response...",
                        "handle_error": "Handling error...",
                    }

                    yield self._format_json_update(
                        {
                            "type": "progress",
                            "message": node_messages.get(node, f"Processing {node}..."),
                            "workflow_id": workflow_id,
                            "progress": int((progress / total_steps) * 100),
                            "current_step": node,
                        }
                    )

                elif event == "streaming_content":
                    # Real-time content streaming
                    chunk = data.get("chunk", "")
                    if chunk.strip():
                        yield self._format_json_update(
                            {
                                "type": "content",
                                "content": chunk,
                                "workflow_id": workflow_id,
                                "is_streaming": True,
                            }
                        )

                elif event == "workflow_complete":
                    final_answer = data.get("final_answer", "")

                    yield self._format_json_update(
                        {
                            "type": "complete",
                            "message": "Document Q&A completed successfully",
                            "final_answer": final_answer,
                            "workflow_id": workflow_id,
                            "progress": 100,
                        }
                    )

                elif event == "error":
                    yield self._format_json_update(
                        {
                            "type": "error",
                            "message": data.get("status", "An error occurred"),
                            "error": data.get("error", "Unknown error"),
                            "workflow_id": workflow_id,
                        }
                    )

            self.logger.info("Enhanced streaming Document Q&A workflow completed")

        except Exception as e:
            self.logger.error(f"Error in enhanced streaming workflow: {e}")
            yield self._format_json_update(
                {
                    "type": "error",
                    "message": "I encountered an error while processing your question",
                    "error": str(e),
                }
            )

    async def stream_simple_format(
        self,
        document_id: str,
        question: str,
        user_id: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream a document question response in simple text format.

        This method provides a simpler streaming interface that returns
        just the response text without SSE formatting.

        Args:
            document_id: ID of the document to query
            question: Question to ask about the document
            user_id: User identifier for access control

        Yields:
            Plain text response chunks
        """
        try:
            # Use the main streaming method but strip SSE formatting
            async for chunk in self.stream_document_question(document_id, question, user_id):
                if chunk.startswith("data: "):
                    content = chunk[6:]  # Remove "data: " prefix
                    is_status = content.startswith("Starting") or content.startswith("Retrieving")
                    if content.strip() and not is_status:
                        yield content
        except Exception as e:
            self.logger.error(f"Error in simple streaming: {e}")
            yield (
                "I apologize, but I encountered an error while processing your "
                "question about the document. Please try again."
            )

    def _format_json_update(self, data: dict) -> str:
        """Format update data as JSON for structured streaming."""
        return f"data: {json.dumps(data)}\n\n"


# Global service instance
_document_qa_streaming_service: DocumentQAStreamingService | None = None


def get_document_qa_streaming_service() -> DocumentQAStreamingService:
    """Get the global Document Q&A streaming service instance."""
    global _document_qa_streaming_service
    if _document_qa_streaming_service is None:
        _document_qa_streaming_service = DocumentQAStreamingService()
    return _document_qa_streaming_service
