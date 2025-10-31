/**
 * LangGraph Agent Service
 *
 * Service for interacting with the LangGraph agent endpoint that provides
 * multi-step reasoning and tool usage capabilities.
 */

import { useAuthStore } from '../stores'

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export interface LangGraphAgentRequest {
  message: string
  user_id?: string
  session_id?: string
  context?: string
  selected_document_ids?: string[]
}

export interface LangGraphAgentResponse {
  answer: string
  timestamp: string
  session_id?: string
  metadata?: {
    steps?: number
    tools_used?: string[]
    reasoning?: string
    document_sources?: Array<{
      document_title: string
      page_number: string
      document_id: string
      relevance_score: number
    }>
  }
}

export interface LangGraphAgentError {
  error: string
  details?: string
  type?: 'validation' | 'processing' | 'timeout' | 'internal'
}

class LangGraphAgentService {
  /**
   * Send a message to the LangGraph agent with document context support
   */
  async sendMessage(
    request: LangGraphAgentRequest,
  ): Promise<ApiResponse<LangGraphAgentResponse>> {
    try {
      const authStore = useAuthStore.getState()

      if (authStore.isLoggedIn()) {
        // Try to refresh token if it's close to expiring (within 30 seconds)
        try {
          await authStore.updateToken(30)
        } catch (error) {
          console.warn('Token refresh failed in request interceptor:', error)
        }
      }

      const token = authStore.getToken()
      const response = await fetch(`/api/v1/chat/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(request),
      })

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ error: 'Unknown error' }))
        throw new Error(
          errorData.detail || errorData.error || `HTTP ${response.status}`,
        )
      }

      const data = await response.json()
      return {
        success: true,
        data,
      }
    } catch (error) {
      console.error('LangGraph Agent API error:', error)
      return {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : 'Failed to send message to LangGraph agent',
      }
    }
  }

  /**
   * Send a document-focused query to the LangGraph agent
   */
  async queryDocuments(
    message: string,
    selectedDocumentIds?: string[],
    sessionId?: string,
    context?: string,
  ): Promise<ApiResponse<LangGraphAgentResponse>> {
    const request: LangGraphAgentRequest = {
      message,
      session_id: sessionId,
      context,
      selected_document_ids: selectedDocumentIds,
    }

    return this.sendMessage(request)
  }

  /**
   * Stream a message to the LangGraph agent with document context support
   */
  async streamMessage(
    request: LangGraphAgentRequest,
    onChunk?: (chunk: string) => void,
    onError?: (error: string) => void,
  ): Promise<void> {
    try {
      // For now, we'll use the regular endpoint and simulate streaming
      // This can be updated when a streaming endpoint is available
      const result = await this.sendMessage(request)

      if (result.success && result.data) {
        // Simulate streaming by sending chunks
        const response = result.data.answer
        if (response && typeof response === 'string') {
          const words = response.split(' ')

          for (let i = 0; i < words.length; i++) {
            const chunk = words.slice(0, i + 1).join(' ')
            onChunk?.(chunk)

            // Small delay to simulate streaming
            await new Promise((resolve) => setTimeout(resolve, 50))
          }
        } else {
          onError?.('Invalid response format from agent')
        }
      } else {
        onError?.(result.error || 'Failed to get response')
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Streaming failed'
      console.error('LangGraph Agent streaming error:', error)
      onError?.(errorMessage)
    }
  }

  /**
   * Stream a document-focused query to the LangGraph agent
   */
  async streamDocumentQuery(
    message: string,
    selectedDocumentIds: string[] | undefined,
    sessionId: string | undefined,
    onChunk?: (chunk: string) => void,
    onError?: (error: string) => void,
  ): Promise<void> {
    const request: LangGraphAgentRequest = {
      message,
      session_id: sessionId,
      selected_document_ids: selectedDocumentIds,
    }

    return this.streamMessage(request, onChunk, onError)
  }

  /**
   * Get agent capabilities and configuration
   */
  async getCapabilities(): Promise<
    ApiResponse<{ tools: string[]; features: string[] }>
  > {
    try {
      // Return static capabilities since we have a unified LangGraph agent
      const capabilities = {
        tools: [
          'document_search',
          'citation_generator',
          'context_analyzer',
          'memory_manager',
        ],
        features: [
          'Document-aware responses',
          'Automatic source citations',
          'Multi-step reasoning',
          'Tool usage capabilities',
          'Context-aware conversations',
          'Session memory',
        ],
      }

      return {
        success: true,
        data: capabilities,
      }
    } catch (error) {
      console.error('Failed to get LangGraph agent capabilities:', error)
      return {
        success: false,
        error: 'Failed to get agent capabilities',
        data: {
          tools: ['document_search', 'citation_generator'],
          features: [
            'Document search',
            'AI responses with citations',
            'Session memory',
          ],
        },
      }
    }
  }
}

// Export singleton instance
export const langGraphAgentService = new LangGraphAgentService()
export default langGraphAgentService
