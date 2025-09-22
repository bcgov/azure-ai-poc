"""
LangChain tool wrappers for MCP tools.

This module provides LangChain-compatible tool wrappers for existing MCP tools,
allowing them to be used in LangGraph workflows while maintaining MCP compatibility.
"""

import json

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.logger import get_logger
from app.services.mcp_server import mcp_server


class DocumentSearchInput(BaseModel):
    """Input schema for document search tool."""

    query: str = Field(description="Search query for documents")
    limit: int = Field(default=10, description="Maximum number of results")


class ChatCompletionInput(BaseModel):
    """Input schema for chat completion tool."""

    message: str = Field(description="User message for chat completion")
    context: str = Field(default="", description="Additional context for the chat")


class DocumentUploadInput(BaseModel):
    """Input schema for document upload tool."""

    filename: str = Field(description="Name of the file to upload")
    content: str = Field(description="Base64 encoded file content")
    content_type: str = Field(description="MIME type of the file")


class MCPDocumentSearchTool(BaseTool):
    """LangChain tool wrapper for MCP document search functionality."""

    name: str = "mcp_document_search"
    description: str = (
        "Search through uploaded documents in the Azure AI Search index. "
        "Use this tool when users ask about documents, policies, or need "
        "to find specific information."
    )
    args_schema: type[BaseModel] = DocumentSearchInput

    def _run(self, query: str, limit: int = 10) -> str:
        """Execute the document search synchronously."""
        try:
            logger = get_logger(__name__)
            logger.info(f"Executing MCP document search: query='{query}', limit={limit}")

            # Call the MCP server's document search handler directly
            # Note: This is a placeholder for synchronous operation
            # Full implementation will be in step 8

            response = {
                "query": query,
                "results": [],
                "message": "Document search functionality will be fully integrated in step 8",
                "status": "placeholder",
            }

            results_count = len(response.get("results", []))
            logger.info(f"MCP document search completed: {results_count} results")
            return json.dumps(response, indent=2)

        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Error in MCP document search: {e}")
            error_response = {"error": str(e), "query": query, "results": [], "status": "error"}
            return json.dumps(error_response, indent=2)

    async def _arun(self, query: str, limit: int = 10) -> str:
        """Execute the document search asynchronously."""
        try:
            logger = get_logger(__name__)
            logger.info(f"Executing async MCP document search: query='{query}', limit={limit}")

            # Call the MCP server's document search handler
            result = await mcp_server._handle_document_search({"query": query, "limit": limit})

            # Convert TextContent results to JSON
            search_results = []
            for item in result:
                if hasattr(item, "text"):
                    try:
                        # Try to parse as JSON if it's structured data
                        data = json.loads(item.text)
                        search_results.append(data)
                    except json.JSONDecodeError:
                        # If not JSON, treat as plain text
                        search_results.append({"text": item.text, "type": "text"})

            response = {
                "query": query,
                "results": search_results,
                "count": len(search_results),
                "status": "success",
            }

            logger.info(f"Async MCP document search completed: {len(search_results)} results")
            return json.dumps(response, indent=2)

        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Error in async MCP document search: {e}")
            error_response = {"error": str(e), "query": query, "results": [], "status": "error"}
            return json.dumps(error_response, indent=2)


class MCPChatCompletionTool(BaseTool):
    """LangChain tool wrapper for MCP chat completion functionality."""

    name: str = "mcp_chat_completion"
    description: str = (
        "Generate AI chat completion using Azure OpenAI through the MCP server. "
        "Use this for general conversation and AI responses when no specific tools are needed."
    )
    args_schema: type[BaseModel] = ChatCompletionInput

    def _run(self, message: str, context: str = "") -> str:
        """Execute the chat completion synchronously."""
        try:
            logger = get_logger(__name__)
            logger.info(f"Executing MCP chat completion: message='{message[:100]}...'")

            # For synchronous call, return a placeholder
            response = {
                "message": message,
                "response": "Chat completion functionality is available through async interface",
                "status": "sync_placeholder",
            }

            return json.dumps(response, indent=2)

        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Error in MCP chat completion: {e}")
            error_response = {"error": str(e), "message": message, "status": "error"}
            return json.dumps(error_response, indent=2)

    async def _arun(self, message: str, context: str = "") -> str:
        """Execute the chat completion asynchronously."""
        try:
            logger = get_logger(__name__)
            logger.info(f"Executing async MCP chat completion: message='{message[:100]}...'")

            # Call the MCP server's chat completion handler
            result = await mcp_server._handle_chat_completion(
                {"message": message, "context": context}
            )

            # Convert TextContent results to JSON
            chat_response = ""
            for item in result:
                if hasattr(item, "text"):
                    chat_response += item.text

            response = {
                "message": message,
                "response": chat_response,
                "context": context,
                "status": "success",
            }

            logger.info("Async MCP chat completion completed")
            return json.dumps(response, indent=2)

        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Error in async MCP chat completion: {e}")
            error_response = {"error": str(e), "message": message, "status": "error"}
            return json.dumps(error_response, indent=2)


class MCPDocumentUploadTool(BaseTool):
    """LangChain tool wrapper for MCP document upload functionality."""

    name: str = "mcp_document_upload"
    description: str = (
        "Upload and process a new document into the system. "
        "Use this when users want to upload files or add new documents to the knowledge base."
    )
    args_schema: type[BaseModel] = DocumentUploadInput

    def _run(self, filename: str, content: str, content_type: str) -> str:
        """Execute the document upload synchronously."""
        try:
            logger = get_logger(__name__)
            logger.info(f"Executing MCP document upload: filename='{filename}'")

            # For synchronous call, return a placeholder
            response = {
                "filename": filename,
                "content_type": content_type,
                "status": "sync_placeholder",
                "message": "Document upload functionality is available through async interface",
            }

            return json.dumps(response, indent=2)

        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Error in MCP document upload: {e}")
            error_response = {"error": str(e), "filename": filename, "status": "error"}
            return json.dumps(error_response, indent=2)

    async def _arun(self, filename: str, content: str, content_type: str) -> str:
        """Execute the document upload asynchronously."""
        try:
            logger = get_logger(__name__)
            logger.info(f"Executing async MCP document upload: filename='{filename}'")

            # Call the MCP server's document upload handler
            result = await mcp_server._handle_document_upload(
                {"filename": filename, "content": content, "content_type": content_type}
            )

            # Convert TextContent results to JSON
            upload_response = ""
            for item in result:
                if hasattr(item, "text"):
                    upload_response += item.text

            response = {
                "filename": filename,
                "content_type": content_type,
                "response": upload_response,
                "status": "success",
            }

            logger.info("Async MCP document upload completed")
            return json.dumps(response, indent=2)

        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Error in async MCP document upload: {e}")
            error_response = {"error": str(e), "filename": filename, "status": "error"}
            return json.dumps(error_response, indent=2)


def get_mcp_tools() -> list[BaseTool]:
    """Get all available MCP tools as LangChain tools."""
    return [
        MCPDocumentSearchTool(),
        MCPChatCompletionTool(),
        MCPDocumentUploadTool(),
    ]


def get_mcp_tool_by_name(tool_name: str) -> BaseTool | None:
    """Get a specific MCP tool by name."""
    tools = get_mcp_tools()
    for tool in tools:
        if tool.name == tool_name:
            return tool
    return None
