/**
 * LangGraph Agent Service
 *
 * @deprecated This service is deprecated. Use chatAgentService or researchAgentService instead.
 * This service was used for interacting with the old LangGraph agent endpoint.
 * The new API uses Microsoft Agent Framework endpoints:
 *   - chatAgentService: /api/v1/chat/
 *   - researchAgentService: /api/v1/research/
 */

import httpClient from './httpClient'
import { acquireToken } from '@/service/auth-service'

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
  private _parseError(error: any, fallback: string): string {
    if (error?.response?.data?.detail) return error.response.data.detail
    if (error?.response?.data?.error) return error.response.data.error
    if (error?.message) return error.message
    return fallback
  }
  /**
   * Send a message to the LangGraph agent with document context support
   */
  async sendMessage(
    request: LangGraphAgentRequest,
  ): Promise<ApiResponse<LangGraphAgentResponse>> {
    try {
      // Ensure an access token is available before making the request via http client
      await acquireToken().catch((error) => {
        console.warn('Token acquisition failed:', error)
        return undefined
      })

      const resp = await httpClient.post('/api/v1/chat/ask', request)
      const data = resp.data as LangGraphAgentResponse
      return {
        success: true,
        data,
      }
    } catch (error: any) {
      console.error('LangGraph Agent API error:', error)
      return { success: false, error: this._parseError(error, 'Failed to send message to LangGraph agent') }
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
