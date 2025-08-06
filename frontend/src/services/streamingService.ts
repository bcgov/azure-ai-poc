import { useAuthStore } from '../stores'
export interface StreamEvent {
  type: 'start' | 'token' | 'end' | 'error'
  content?: string
  message?: string
  documentId?: string
  question?: string
  timestamp: string
}

export class StreamingService {
  /**
   * Stream a general chat question
   */
  async *streamChatQuestion(
    question: string,
  ): AsyncGenerator<StreamEvent, void, unknown> {
    const authStore = useAuthStore.getState()
    try {
      if (authStore.isLoggedIn()) {
        // Try to refresh token if it's close to expiring (within 30 seconds)
        try {
          await authStore.updateToken(30)
        } catch (error) {
          console.warn('Token refresh failed in request interceptor:', error)
        }

        const token = authStore.getToken()
        const response = await fetch(`/api/v1/chat/ask/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ question }),
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        if (!response.body) {
          throw new Error('Response body is null')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()

        try {
          while (true) {
            const { done, value } = await reader.read()

            if (done) break

            const chunk = decoder.decode(value, { stream: true })
            const lines = chunk.split('\n')

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = line.slice(6) // Remove 'data: ' prefix
                  if (data.trim()) {
                    const event: StreamEvent = JSON.parse(data)
                    yield event
                  }
                } catch (parseError) {
                  console.warn('Failed to parse SSE data:', parseError)
                }
              }
            }
          }
        } finally {
          reader.releaseLock()
        }
      } else {
        throw new Error('User is not authenticated')
      }
    } catch (error) {
      yield {
        type: 'error',
        message:
          error instanceof Error ? error.message : 'An unknown error occurred',
        timestamp: new Date().toISOString(),
      }
    }
  }

  /**
   * Stream a document-based question
   */
  async *streamDocumentQuestion(
    question: string,
    documentId: string,
  ): AsyncGenerator<StreamEvent, void, unknown> {
    const authStore = useAuthStore.getState()
    try {
      if (authStore.isLoggedIn()) {
        // Try to refresh token if it's close to expiring (within 30 seconds)
        try {
          await authStore.updateToken(30)
        } catch (error) {
          console.warn('Token refresh failed in request interceptor:', error)
        }

        const token = authStore.getToken()
        const response = await fetch(`/api/v1/documents/ask/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ question, documentId }),
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        if (!response.body) {
          throw new Error('Response body is null')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()

        try {
          while (true) {
            const { done, value } = await reader.read()

            if (done) break

            const chunk = decoder.decode(value, { stream: true })
            const lines = chunk.split('\n')

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = line.slice(6) // Remove 'data: ' prefix
                  if (data.trim()) {
                    const event: StreamEvent = JSON.parse(data)
                    yield event
                  }
                } catch (parseError) {
                  console.warn('Failed to parse SSE data:', parseError)
                }
              }
            }
          }
        } finally {
          reader.releaseLock()
        }
      } else {
        throw new Error('User is not authenticated')
      }
    } catch (error) {
      yield {
        type: 'error',
        message:
          error instanceof Error ? error.message : 'An unknown error occurred',
        timestamp: new Date().toISOString(),
      }
    }
  }
}

export default new StreamingService()
