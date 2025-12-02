/**
 * Chat Agent Service
 *
 * Service for interacting with the Microsoft Agent Framework chat endpoint.
 * Provides chat functionality with session support and CosmosDB persistence.
 * All responses include source attribution for traceability.
 */

import { useAuthStore } from '../stores'
import httpClient from './httpClient'

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export interface ChatRequest {
  message: string
  session_id?: string
  history?: Array<{ role: string; content: string }>
}

export interface SourceInfo {
  source_type: string // 'llm_knowledge', 'document', 'web', 'api', etc.
  description: string
  confidence: string // 'high', 'medium', 'low'
  url?: string | null
  api_endpoint?: string // API endpoint path for API sources
  api_params?: Record<string, string> // Query parameters for API sources
}

export interface ChatResponse {
  response: string
  session_id: string
  sources: SourceInfo[] // Required for traceability
  has_sufficient_info: boolean
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  id?: string
  timestamp?: string
  sources?: SourceInfo[]
}

// Session types for CosmosDB persistence
export interface Session {
  session_id: string
  title: string
  created_at: string
  last_updated: string
  message_count: number
}

export interface SessionListResponse {
  sessions: Session[]
}

export interface SessionHistoryResponse {
  session_id: string
  messages: ChatMessage[]
}

class ChatAgentService {
  private baseUrl = '/api/v1/chat'

  private _parseError(error: any, fallback: string): string {
    if (error?.response?.data?.detail) return error.response.data.detail
    if (error?.response?.data?.error) return error.response.data.error
    if (error?.message) return error.message
    return fallback
  }

  /**
   * Get authorization headers
   */
  private async getAuthHeaders(): Promise<Record<string, string>> {
    const authStore = useAuthStore.getState()

    if (authStore.isLoggedIn()) {
      try {
        await authStore.updateToken(30)
      } catch (error) {
        console.warn('Token refresh failed:', error)
      }
    }

    const token = authStore.getToken()
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }
  }

  /**
   * Send a message to the chat agent
   */
  async sendMessage(
    message: string,
    sessionId?: string,
    history?: ChatMessage[],
  ): Promise<ApiResponse<ChatResponse>> {
    try {
      // Ensure token is refreshed before making the request via the http client
      await this.getAuthHeaders()

      const request: ChatRequest = {
        message,
        session_id: sessionId,
        history: history?.map((msg) => ({ role: msg.role, content: msg.content })),
      }

      const resp = await httpClient.post(`${this.baseUrl}/`, request)
      const data: ChatResponse = resp.data as ChatResponse
      return {
        success: true,
        data,
      }
    } catch (error: any) {
      console.error('Chat Agent API error:', error)
      let message = 'Failed to send message to chat agent'
      if (error?.response?.data?.detail) {
        message = error.response.data.detail
      } else if (error?.response?.data?.error) {
        message = error.response.data.error
      } else if (error instanceof Error) {
        message = error.message
      }
      return { success: false, error: message }
    }
  }

  /**
   * Stream a message response (simulated until real streaming is implemented)
   * Returns sources and metadata after streaming completes
   */
  async streamMessage(
    message: string,
    sessionId?: string,
    history?: ChatMessage[],
    onChunk?: (chunk: string) => void,
    onError?: (error: string) => void,
  ): Promise<{ sources: SourceInfo[]; hasSufficientInfo: boolean; sessionId?: string } | null> {
    try {
      const result = await this.sendMessage(message, sessionId, history)

      if (result.success && result.data) {
        const response = result.data.response
        if (response && typeof response === 'string') {
          // Simulate streaming by sending words progressively
          const words = response.split(' ')
          for (let i = 0; i < words.length; i++) {
            const chunk = words.slice(0, i + 1).join(' ')
            onChunk?.(chunk)
            await new Promise((resolve) => setTimeout(resolve, 30))
          }
        } else {
          onError?.('Invalid response format from agent')
          return null
        }
        // Return sources and metadata after streaming completes
        return {
          sources: result.data.sources || [],
          hasSufficientInfo: result.data.has_sufficient_info,
          sessionId: result.data.session_id,
        }
      } else {
        onError?.(result.error || 'Failed to get response')
        return null
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Streaming failed'
      console.error('Chat Agent streaming error:', error)
      onError?.(errorMessage)
      return null
    }
  }

  /**
   * Check if the chat service is healthy
   */
  async healthCheck(): Promise<ApiResponse<{ status: string; service: string }>> {
    try {
      const resp = await httpClient.get(`${this.baseUrl}/health`)
      const data = resp.data
      return { success: true, data }
    } catch (error) {
      console.error('Health check error:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Health check failed',
      }
    }
  }

  // ===================
  // Session Management
  // ===================

  /**
   * Create a new chat session
   */
  async createSession(title?: string): Promise<ApiResponse<{ session_id: string; title: string }>> {
    try {
      const headers = await this.getAuthHeaders()
      const url = new URL(`${this.baseUrl}/sessions`, window.location.origin)
      if (title) {
        url.searchParams.append('title', title)
      }

      const resp = await httpClient.post(`${this.baseUrl}/sessions`, null, { params: { title } })
      const data = resp.data as { session_id: string; title: string }
      return { success: true, data }
    } catch (error: any) {
      console.error('Create session error:', error)
      return { success: false, error: this._parseError(error, 'Failed to create session') }
    }
  }

  /**
   * List all chat sessions for the current user
   */
  async listSessions(limit: number = 20): Promise<ApiResponse<SessionListResponse>> {
    try {
      const headers = await this.getAuthHeaders()
      const url = new URL(`${this.baseUrl}/sessions`, window.location.origin)
      url.searchParams.append('limit', limit.toString())

      const resp = await httpClient.get(`${this.baseUrl}/sessions`, { params: { limit } })
      const data = resp.data as SessionListResponse
      return { success: true, data }
    } catch (error: any) {
      console.error('List sessions error:', error)
      return { success: false, error: this._parseError(error, 'Failed to list sessions') }
    }
  }

  /**
   * Get chat history for a specific session
   */
  async getSessionHistory(sessionId: string, limit: number = 50): Promise<ApiResponse<SessionHistoryResponse>> {
    try {
      const headers = await this.getAuthHeaders()
      const url = new URL(`${this.baseUrl}/sessions/${sessionId}/history`, window.location.origin)
      url.searchParams.append('limit', limit.toString())

      const resp = await httpClient.get(`${this.baseUrl}/sessions/${sessionId}/history`, { params: { limit } })
      const data = resp.data as SessionHistoryResponse
      return { success: true, data }
    } catch (error: any) {
      console.error('Get session history error:', error)
      return { success: false, error: this._parseError(error, 'Failed to get session history') }
    }
  }

  /**
   * Delete a chat session and all its messages
   */
  async deleteSession(sessionId: string): Promise<ApiResponse<{ status: string; session_id: string }>> {
    try {
      const headers = await this.getAuthHeaders()

      const resp = await httpClient.delete(`${this.baseUrl}/sessions/${sessionId}`)

      const data = resp.data
      return { success: true, data }
    } catch (error: any) {
      console.error('Delete session error:', error)
      return { success: false, error: this._parseError(error, 'Failed to delete session') }
    }
  }
}

// Export singleton instance
export const chatAgentService = new ChatAgentService()
export default chatAgentService
