/**
 * MCP Service for communicating with the backend MCP endpoints
 */

export interface MCPServerInfo {
  server_name: string
  command: string[]
}

export interface MCPTool {
  name: string
  description: string
  inputSchema: any
}

export interface MCPPrompt {
  name: string
  description: string
  arguments: any[]
}

export interface MCPResource {
  uri: string
  name: string
  description: string
  mimeType: string
}

export interface MCPToolCallRequest {
  server_name: string
  tool_name: string
  arguments: Record<string, any>
}

export interface MCPPromptRequest {
  server_name: string
  prompt_name: string
  arguments: Record<string, string>
}

export interface MCPResourceRequest {
  server_name: string
  uri: string
}

export interface MCPToolCallResponse {
  success: boolean
  content: Array<{
    type: string
    text?: string
    data?: string
  }>
  error?: string
  isError?: boolean
}

export interface MCPPromptResponse {
  success: boolean
  role?: string
  content?: string
  error?: string
}

export interface MCPResourceResponse {
  success: boolean
  content?: Array<{
    type: string
    text?: string
    blob?: string
  }>
  error?: string
}

class MCPService {
  private baseUrl = '/api/v1/mcp'

  /**
   * Get list of connected MCP servers
   */
  async getConnectedServers(): Promise<string[]> {
    const response = await fetch(`${this.baseUrl}/servers`)
    if (!response.ok) {
      throw new Error(`Failed to get servers: ${response.statusText}`)
    }
    const data = await response.json()
    return data.servers
  }

  /**
   * Connect to an MCP server
   */
  async connectToServer(serverName: string, command: string[]): Promise<void> {
    const response = await fetch(`${this.baseUrl}/servers/connect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        server_name: serverName,
        command: command,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(
        error.detail || `Failed to connect to server: ${response.statusText}`,
      )
    }
  }

  /**
   * Disconnect from an MCP server
   */
  async disconnectFromServer(serverName: string): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/servers/${encodeURIComponent(serverName)}`,
      {
        method: 'DELETE',
      },
    )

    if (!response.ok) {
      const error = await response.json()
      throw new Error(
        error.detail ||
          `Failed to disconnect from server: ${response.statusText}`,
      )
    }
  }

  /**
   * Get available tools from an MCP server
   */
  async getTools(serverName: string): Promise<MCPTool[]> {
    const response = await fetch(
      `${this.baseUrl}/servers/${encodeURIComponent(serverName)}/tools`,
    )
    if (!response.ok) {
      const error = await response.json()
      throw new Error(
        error.detail || `Failed to get tools: ${response.statusText}`,
      )
    }
    const data = await response.json()
    return data.tools
  }

  /**
   * Call a tool on an MCP server
   */
  async callTool(request: MCPToolCallRequest): Promise<MCPToolCallResponse> {
    const response = await fetch(`${this.baseUrl}/servers/tools/call`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(
        error.detail || `Failed to call tool: ${response.statusText}`,
      )
    }

    return await response.json()
  }

  /**
   * Get available prompts from an MCP server
   */
  async getPrompts(serverName: string): Promise<MCPPrompt[]> {
    const response = await fetch(
      `${this.baseUrl}/servers/${encodeURIComponent(serverName)}/prompts`,
    )
    if (!response.ok) {
      const error = await response.json()
      throw new Error(
        error.detail || `Failed to get prompts: ${response.statusText}`,
      )
    }
    const data = await response.json()
    return data.prompts
  }

  /**
   * Get a specific prompt from an MCP server
   */
  async getPrompt(request: MCPPromptRequest): Promise<MCPPromptResponse> {
    const response = await fetch(`${this.baseUrl}/servers/prompts/get`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(
        error.detail || `Failed to get prompt: ${response.statusText}`,
      )
    }

    return await response.json()
  }

  /**
   * Get available resources from an MCP server
   */
  async getResources(serverName: string): Promise<MCPResource[]> {
    const response = await fetch(
      `${this.baseUrl}/servers/${encodeURIComponent(serverName)}/resources`,
    )
    if (!response.ok) {
      const error = await response.json()
      throw new Error(
        error.detail || `Failed to get resources: ${response.statusText}`,
      )
    }
    const data = await response.json()
    return data.resources
  }

  /**
   * Read a specific resource from an MCP server
   */
  async readResource(
    request: MCPResourceRequest,
  ): Promise<MCPResourceResponse> {
    const response = await fetch(`${this.baseUrl}/servers/resources/read`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(
        error.detail || `Failed to read resource: ${response.statusText}`,
      )
    }

    return await response.json()
  }

  /**
   * Get internal tools provided by the API itself
   */
  async getInternalTools(): Promise<MCPTool[]> {
    const response = await fetch(`${this.baseUrl}/internal/tools`)
    if (!response.ok) {
      const error = await response.json()
      throw new Error(
        error.detail || `Failed to get internal tools: ${response.statusText}`,
      )
    }
    const data = await response.json()
    return data.tools
  }

  /**
   * Call an internal tool
   */
  async callInternalTool(
    toolName: string,
    args: Record<string, any>,
  ): Promise<MCPToolCallResponse> {
    const response = await fetch(`${this.baseUrl}/internal/tools/call`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        server_name: 'internal',
        tool_name: toolName,
        arguments: args,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(
        error.detail || `Failed to call internal tool: ${response.statusText}`,
      )
    }

    return await response.json()
  }
}

export const mcpService = new MCPService()
