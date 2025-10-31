"""Model Context Protocol (MCP) Server Implementation."""

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Prompt,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server for Azure AI POC."""

    def __init__(self):
        self.server = Server("azure-ai-poc-mcp")
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="document_search",
                    description="Search through uploaded documents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for documents",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="chat_completion",
                    description="Generate AI chat completion using Azure OpenAI",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "User message for chat completion",
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context for the chat",
                                "default": "",
                            },
                        },
                        "required": ["message"],
                    },
                ),
                Tool(
                    name="document_upload",
                    description="Upload and process a new document",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Name of the file to upload",
                            },
                            "content": {
                                "type": "string",
                                "description": "Base64 encoded file content",
                            },
                            "content_type": {
                                "type": "string",
                                "description": "MIME type of the file",
                            },
                        },
                        "required": ["filename", "content", "content_type"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "document_search":
                    return await self._handle_document_search(arguments)
                elif name == "chat_completion":
                    return await self._handle_chat_completion(arguments)
                elif name == "document_upload":
                    return await self._handle_document_upload(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @self.server.list_prompts()
        async def list_prompts() -> list[Prompt]:
            """List available prompts."""
            return [
                Prompt(
                    name="document_analysis",
                    description="Analyze uploaded documents for insights",
                    arguments=[
                        {
                            "name": "document_id",
                            "description": "ID of the document to analyze",
                            "required": True,
                        },
                        {
                            "name": "analysis_type",
                            "description": (
                                "Type of analysis to perform (summary, keywords, sentiment)"
                            ),
                            "required": False,
                        },
                    ],
                ),
                Prompt(
                    name="chat_context",
                    description="Generate contextual chat responses with document context",
                    arguments=[
                        {"name": "user_message", "description": "User's message", "required": True},
                        {
                            "name": "document_context",
                            "description": "Relevant document context",
                            "required": False,
                        },
                    ],
                ),
            ]

        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict[str, str]) -> PromptMessage:
            """Get specific prompt."""
            if name == "document_analysis":
                document_id = arguments.get("document_id", "")
                analysis_type = arguments.get("analysis_type", "summary")

                prompt_text = f"""
Analyze the document with ID: {document_id}

Please provide a {analysis_type} analysis of this document. Focus on:
- Key themes and topics
- Important insights
- Actionable information
- Relevant context for future conversations

Format your response in a clear, structured manner.
"""
                return PromptMessage(
                    role="user", content=TextContent(type="text", text=prompt_text)
                )

            elif name == "chat_context":
                user_message = arguments.get("user_message", "")
                document_context = arguments.get("document_context", "")

                prompt_text = f"""
User Message: {user_message}

Document Context: {document_context}

Please provide a helpful response that takes into account both the user's message and
the available document context. Be specific and reference relevant information from
the documents when appropriate.
"""
                return PromptMessage(
                    role="user", content=TextContent(type="text", text=prompt_text)
                )

            else:
                raise ValueError(f"Unknown prompt: {name}")

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available resources."""
            return [
                Resource(
                    uri="azure-ai-poc://documents",
                    name="Documents",
                    description="Access to uploaded documents and their metadata",
                    mimeType="application/json",
                ),
                Resource(
                    uri="azure-ai-poc://chat-history",
                    name="Chat History",
                    description="Access to chat conversation history",
                    mimeType="application/json",
                ),
                Resource(
                    uri="azure-ai-poc://system-status",
                    name="System Status",
                    description="Current system status and health metrics",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read resource content."""
            if uri == "azure-ai-poc://documents":
                # In a real implementation, fetch from database
                return json.dumps(
                    {"documents": [], "total_count": 0, "last_updated": "2024-01-01T00:00:00Z"}
                )
            elif uri == "azure-ai-poc://chat-history":
                return json.dumps({"conversations": [], "total_messages": 0})
            elif uri == "azure-ai-poc://system-status":
                return json.dumps(
                    {"status": "healthy", "uptime": "1h 30m", "active_connections": 5}
                )
            else:
                raise ValueError(f"Unknown resource: {uri}")

    async def _handle_document_search(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle document search tool."""
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)

        # In a real implementation, integrate with your document search service
        results = {"query": query, "results": [], "total_found": 0, "limit": limit}

        return [
            TextContent(
                type="text",
                text=f"Document search results for '{query}':\n{json.dumps(results, indent=2)}",
            )
        ]

    async def _handle_chat_completion(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle chat completion tool."""
        message = arguments.get("message", "")
        context = arguments.get("context", "")

        # In a real implementation, integrate with your Azure OpenAI service
        response = {
            "message": message,
            "context_used": context,
            "response": f"AI response to: {message}",
            "timestamp": "2024-01-01T00:00:00Z",
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    async def _handle_document_upload(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle document upload tool."""
        filename = arguments.get("filename", "")
        content = arguments.get("content", "")
        content_type = arguments.get("content_type", "")

        # In a real implementation, integrate with your document upload service
        result = {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(content) if content else 0,
            "status": "uploaded",
            "document_id": f"doc_{hash(filename)}",
            "timestamp": "2024-01-01T00:00:00Z",
        }

        return [
            TextContent(
                type="text", text=f"Document uploaded successfully:\n{json.dumps(result, indent=2)}"
            )
        ]

    async def run_stdio(self):
        """Run the MCP server using stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(server_name="azure-ai-poc-mcp", server_version="1.0.0"),
            )


# Global server instance
mcp_server = MCPServer()


async def start_mcp_server():
    """Start the MCP server."""
    try:
        await mcp_server.run_stdio()
    except Exception as e:
        logger.error(f"MCP Server error: {e}")
        raise


if __name__ == "__main__":
    # For running as standalone MCP server
    asyncio.run(start_mcp_server())
