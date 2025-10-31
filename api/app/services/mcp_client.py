"""MCP Client Service for integrating with external MCP servers."""

import logging
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClientService:
    """Service for connecting to and interacting with MCP servers."""

    def __init__(self):
        self.sessions: dict[str, ClientSession] = {}

    async def connect_to_server(self, server_name: str, command: list[str]) -> bool:
        """Connect to an MCP server."""
        try:
            # Create stdio connection to MCP server
            read_stream, write_stream = await stdio_client(command)

            # Create session
            session = ClientSession(read_stream, write_stream)
            await session.initialize()

            self.sessions[server_name] = session
            logger.info(f"Connected to MCP server: {server_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_name}: {e}")
            return False

    async def disconnect_from_server(self, server_name: str) -> bool:
        """Disconnect from an MCP server."""
        try:
            if server_name in self.sessions:
                session = self.sessions[server_name]
                await session.close()
                del self.sessions[server_name]
                logger.info(f"Disconnected from MCP server: {server_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to disconnect from MCP server {server_name}: {e}")
            return False

    async def list_tools(self, server_name: str) -> list[dict[str, Any]]:
        """List available tools from an MCP server."""
        try:
            if server_name not in self.sessions:
                raise ValueError(f"Not connected to server: {server_name}")

            session = self.sessions[server_name]
            result = await session.list_tools()

            tools = []
            for tool in result.tools:
                tools.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema,
                    }
                )

            return tools

        except Exception as e:
            logger.error(f"Failed to list tools from {server_name}: {e}")
            return []

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a tool on an MCP server."""
        try:
            if server_name not in self.sessions:
                raise ValueError(f"Not connected to server: {server_name}")

            session = self.sessions[server_name]
            result = await session.call_tool(tool_name, arguments)

            content = []
            for item in result.content:
                if hasattr(item, "text"):
                    content.append({"type": "text", "text": item.text})
                elif hasattr(item, "data"):
                    content.append({"type": "image", "data": item.data})

            return {
                "success": True,
                "content": content,
                "isError": result.isError if hasattr(result, "isError") else False,
            }

        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on {server_name}: {e}")
            return {"success": False, "error": str(e), "content": []}

    async def list_prompts(self, server_name: str) -> list[dict[str, Any]]:
        """List available prompts from an MCP server."""
        try:
            if server_name not in self.sessions:
                raise ValueError(f"Not connected to server: {server_name}")

            session = self.sessions[server_name]
            result = await session.list_prompts()

            prompts = []
            for prompt in result.prompts:
                prompts.append(
                    {
                        "name": prompt.name,
                        "description": prompt.description,
                        "arguments": prompt.arguments if hasattr(prompt, "arguments") else [],
                    }
                )

            return prompts

        except Exception as e:
            logger.error(f"Failed to list prompts from {server_name}: {e}")
            return []

    async def get_prompt(
        self, server_name: str, prompt_name: str, arguments: dict[str, str]
    ) -> dict[str, Any]:
        """Get a specific prompt from an MCP server."""
        try:
            if server_name not in self.sessions:
                raise ValueError(f"Not connected to server: {server_name}")

            session = self.sessions[server_name]
            result = await session.get_prompt(prompt_name, arguments)

            return {
                "success": True,
                "role": result.message.role,
                "content": result.message.content.text
                if hasattr(result.message.content, "text")
                else str(result.message.content),
            }

        except Exception as e:
            logger.error(f"Failed to get prompt {prompt_name} from {server_name}: {e}")
            return {"success": False, "error": str(e)}

    async def list_resources(self, server_name: str) -> list[dict[str, Any]]:
        """List available resources from an MCP server."""
        try:
            if server_name not in self.sessions:
                raise ValueError(f"Not connected to server: {server_name}")

            session = self.sessions[server_name]
            result = await session.list_resources()

            resources = []
            for resource in result.resources:
                resources.append(
                    {
                        "uri": resource.uri,
                        "name": resource.name,
                        "description": resource.description
                        if hasattr(resource, "description")
                        else "",
                        "mimeType": resource.mimeType if hasattr(resource, "mimeType") else "",
                    }
                )

            return resources

        except Exception as e:
            logger.error(f"Failed to list resources from {server_name}: {e}")
            return []

    async def read_resource(self, server_name: str, uri: str) -> dict[str, Any]:
        """Read a specific resource from an MCP server."""
        try:
            if server_name not in self.sessions:
                raise ValueError(f"Not connected to server: {server_name}")

            session = self.sessions[server_name]
            result = await session.read_resource(uri)

            content = []
            for item in result.contents:
                if hasattr(item, "text"):
                    content.append({"type": "text", "text": item.text})
                elif hasattr(item, "blob"):
                    content.append({"type": "blob", "blob": item.blob})

            return {"success": True, "content": content}

        except Exception as e:
            logger.error(f"Failed to read resource {uri} from {server_name}: {e}")
            return {"success": False, "error": str(e)}

    def get_connected_servers(self) -> list[str]:
        """Get list of connected server names."""
        return list(self.sessions.keys())

    async def close_all_connections(self):
        """Close all MCP server connections."""
        for server_name in list(self.sessions.keys()):
            await self.disconnect_from_server(server_name)


# Global MCP client service instance
_mcp_client_service: MCPClientService | None = None


def get_mcp_client_service() -> MCPClientService:
    """Get the global MCP client service instance."""
    global _mcp_client_service
    if _mcp_client_service is None:
        _mcp_client_service = MCPClientService()
    return _mcp_client_service
