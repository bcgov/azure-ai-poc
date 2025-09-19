"""FastAPI router for MCP (Model Context Protocol) endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.mcp_client import get_mcp_client_service
from app.services.mcp_server import mcp_server

logger = logging.getLogger(__name__)

router = APIRouter()


class MCPServerConnectRequest(BaseModel):
    """Request model for connecting to an MCP server."""

    server_name: str
    command: list[str]


class MCPToolCallRequest(BaseModel):
    """Request model for calling an MCP tool."""

    server_name: str
    tool_name: str
    arguments: dict[str, Any]


class MCPPromptRequest(BaseModel):
    """Request model for getting an MCP prompt."""

    server_name: str
    prompt_name: str
    arguments: dict[str, str]


class MCPResourceRequest(BaseModel):
    """Request model for reading an MCP resource."""

    server_name: str
    uri: str


@router.get("/servers")
async def list_connected_servers():
    """List all connected MCP servers."""
    try:
        mcp_client_service = get_mcp_client_service()
        mcp_client_service = get_mcp_client_service()
        servers = mcp_client_service.get_connected_servers()
        return {"servers": servers}
    except Exception as e:
        logger.error(f"Failed to list servers: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/servers/connect")
async def connect_to_server(request: MCPServerConnectRequest):
    """Connect to an MCP server."""
    try:
        mcp_client_service = get_mcp_client_service()
        mcp_client_service = get_mcp_client_service()
        success = await mcp_client_service.connect_to_server(request.server_name, request.command)
        if success:
            return {"message": f"Connected to server: {request.server_name}"}
        else:
            raise HTTPException(
                status_code=400, detail=f"Failed to connect to server: {request.server_name}"
            )
    except Exception as e:
        logger.error(f"Failed to connect to server {request.server_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/servers/{server_name}")
async def disconnect_from_server(server_name: str):
    """Disconnect from an MCP server."""
    try:
        mcp_client_service = get_mcp_client_service()
        mcp_client_service = get_mcp_client_service()
        success = await mcp_client_service.disconnect_from_server(server_name)
        if success:
            return {"message": f"Disconnected from server: {server_name}"}
        else:
            raise HTTPException(status_code=404, detail=f"Server not found: {server_name}")
    except Exception as e:
        logger.error(f"Failed to disconnect from server {server_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/servers/{server_name}/tools")
async def list_tools(server_name: str):
    """List available tools from an MCP server."""
    try:
        mcp_client_service = get_mcp_client_service()
        tools = await mcp_client_service.list_tools(server_name)
        return {"tools": tools}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to list tools from {server_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/servers/tools/call")
async def call_tool(request: MCPToolCallRequest):
    """Call a tool on an MCP server."""
    try:
        mcp_client_service = get_mcp_client_service()
        result = await mcp_client_service.call_tool(
            request.server_name, request.tool_name, request.arguments
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to call tool {request.tool_name} on {request.server_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/servers/{server_name}/prompts")
async def list_prompts(server_name: str):
    """List available prompts from an MCP server."""
    try:
        mcp_client_service = get_mcp_client_service()
        prompts = await mcp_client_service.list_prompts(server_name)
        return {"prompts": prompts}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to list prompts from {server_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/servers/prompts/get")
async def get_prompt(request: MCPPromptRequest):
    """Get a specific prompt from an MCP server."""
    try:
        mcp_client_service = get_mcp_client_service()
        result = await mcp_client_service.get_prompt(
            request.server_name, request.prompt_name, request.arguments
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to get prompt {request.prompt_name} from {request.server_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/servers/{server_name}/resources")
async def list_resources(server_name: str):
    """List available resources from an MCP server."""
    try:
        mcp_client_service = get_mcp_client_service()
        resources = await mcp_client_service.list_resources(server_name)
        return {"resources": resources}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to list resources from {server_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/servers/resources/read")
async def read_resource(request: MCPResourceRequest):
    """Read a specific resource from an MCP server."""
    try:
        mcp_client_service = get_mcp_client_service()
        result = await mcp_client_service.read_resource(request.server_name, request.uri)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to read resource {request.uri} from {request.server_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/internal/tools")
async def list_internal_tools():
    """List tools provided by the internal MCP server."""
    try:
        # Access the internal MCP server tools directly
        tools = [
            {
                "name": "document_search",
                "description": "Search through uploaded documents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query for documents"},
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "chat_completion",
                "description": "Generate AI chat completion using Azure OpenAI",
                "inputSchema": {
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
            },
            {
                "name": "document_upload",
                "description": "Upload and process a new document",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Name of the file to upload"},
                        "content": {"type": "string", "description": "Base64 encoded file content"},
                        "content_type": {"type": "string", "description": "MIME type of the file"},
                    },
                    "required": ["filename", "content", "content_type"],
                },
            },
        ]
        return {"tools": tools}
    except Exception as e:
        logger.error(f"Failed to list internal tools: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/internal/tools/call")
async def call_internal_tool(request: MCPToolCallRequest):
    """Call a tool on the internal MCP server."""
    try:
        # Route to the appropriate internal tool handler
        if request.tool_name == "document_search":
            result = await mcp_server._handle_document_search(request.arguments)
        elif request.tool_name == "chat_completion":
            result = await mcp_server._handle_chat_completion(request.arguments)
        elif request.tool_name == "document_upload":
            result = await mcp_server._handle_document_upload(request.arguments)
        else:
            raise HTTPException(status_code=404, detail=f"Tool not found: {request.tool_name}")

        # Convert TextContent objects to dict format
        content = []
        for item in result:
            content.append({"type": item.type, "text": item.text})

        return {"success": True, "content": content}
    except Exception as e:
        logger.error(f"Failed to call internal tool {request.tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
