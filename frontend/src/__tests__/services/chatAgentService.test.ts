/**
 * Chat Agent Service Tests
 *
 * Tests for the Microsoft Agent Framework chat service
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock the auth store
vi.mock('../../stores', () => ({
  useAuthStore: {
    getState: vi.fn(() => ({
      isLoggedIn: vi.fn(() => true),
      updateToken: vi.fn(() => Promise.resolve()),
      getToken: vi.fn(() => 'mock-token'),
    })),
  },
}))

import httpClient from '@/services/httpClient'
import { chatAgentService } from '@/services/chatAgentService'

describe('ChatAgentService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // spy on httpClient methods
    vi.spyOn(httpClient, 'post').mockResolvedValue({ data: {} } as any)
    vi.spyOn(httpClient, 'get').mockResolvedValue({ data: {} } as any)
    vi.spyOn(httpClient, 'delete').mockResolvedValue({ data: {} } as any)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('sendMessage', () => {
    it('should send a message successfully', async () => {
      const mockResponse = {
        response: 'Hello! How can I help you today?',
        session_id: 'test-session-123',
      }

      ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const result = await chatAgentService.sendMessage(
        'Hello, world!',
        'test-session-123',
      )

      expect(result.success).toBe(true)
      expect(result.data).toEqual(mockResponse)
      expect(httpClient.post).toHaveBeenCalledWith('/api/v1/chat/', expect.objectContaining({ message: 'Hello, world!' }))
    })

    it('should handle API errors gracefully', async () => {
      ;(httpClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { data: { detail: 'Internal server error' } } })

      const result = await chatAgentService.sendMessage('Test message')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Internal server error')
    })

    it('should handle network errors', async () => {
      ;(httpClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network error'))

      const result = await chatAgentService.sendMessage('Test message')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Network error')
    })

    it('should include chat history when provided', async () => {
      const mockResponse = {
        response: 'Based on our conversation...',
        session_id: 'test-session-123',
      }

      ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const history = [
        { role: 'user' as const, content: 'First message' },
        { role: 'assistant' as const, content: 'First response' },
      ]

      await chatAgentService.sendMessage('Follow-up', 'session-123', history)

      expect(httpClient.post).toHaveBeenCalledWith('/api/v1/chat/', expect.objectContaining({ message: 'Follow-up' }))
    })
  })

  describe('streamMessage', () => {
    it('should stream message chunks', async () => {
      const mockResponse = {
        response: 'Hello world test',
        session_id: 'test-session',
      }

      ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const chunks: string[] = []
      const onChunk = (chunk: string) => chunks.push(chunk)
      const onError = vi.fn()

      await chatAgentService.streamMessage('Test', undefined, undefined, onChunk, onError)

      expect(onError).not.toHaveBeenCalled()
      // Should have received progressive chunks
      expect(chunks.length).toBeGreaterThan(0)
      // Final chunk should be the complete message
      expect(chunks[chunks.length - 1]).toBe('Hello world test')
    })

    it('should call onError when request fails', async () => {
      ;(httpClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { data: { detail: 'Server error' } } })

      const onChunk = vi.fn()
      const onError = vi.fn()

      await chatAgentService.streamMessage('Test', undefined, undefined, onChunk, onError)

      expect(onError).toHaveBeenCalledWith('Server error')
    })
  })

  describe('healthCheck', () => {
    it('should return health status', async () => {
      ;(httpClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: { status: 'healthy', service: 'chat-agent' } })

      const result = await chatAgentService.healthCheck()

      expect(result.success).toBe(true)
      expect(result.data?.status).toBe('healthy')
    })

    it('should handle health check failure', async () => {
      ;(httpClient.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { status: 503 } })

      const result = await chatAgentService.healthCheck()

      expect(result.success).toBe(false)
      expect(result.error).toContain('Health check failed')
    })
  })

  describe('Session Management', () => {
    describe('createSession', () => {
      it('should create a session successfully', async () => {
        const mockResponse = {
          session_id: 'new-session-123',
          title: 'New Chat Session',
        }

        ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

        const result = await chatAgentService.createSession('New Chat Session')

        expect(result.success).toBe(true)
        expect(result.data?.session_id).toBe('new-session-123')
        expect(httpClient.post).toHaveBeenCalledWith('/api/v1/chat/sessions', null, expect.objectContaining({ params: expect.any(Object) }))
      })

      it('should handle create session errors', async () => {
        ;(httpClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { data: { detail: 'Failed to create session' } } })

        const result = await chatAgentService.createSession()

        expect(result.success).toBe(false)
        expect(result.error).toBe('Failed to create session')
      })
    })

    describe('listSessions', () => {
      it('should list sessions successfully', async () => {
        const mockResponse = {
          sessions: [
            {
              session_id: 'session-1',
              title: 'Chat 1',
              created_at: '2024-01-01T00:00:00Z',
              last_updated: '2024-01-01T01:00:00Z',
              message_count: 5,
            },
            {
              session_id: 'session-2',
              title: 'Chat 2',
              created_at: '2024-01-02T00:00:00Z',
              last_updated: '2024-01-02T01:00:00Z',
              message_count: 3,
            },
          ],
        }

        ;(httpClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

        const result = await chatAgentService.listSessions()

        expect(result.success).toBe(true)
        expect(result.data?.sessions).toHaveLength(2)
        expect(result.data?.sessions[0].session_id).toBe('session-1')
      })
    })

    describe('getSessionHistory', () => {
      it('should get session history successfully', async () => {
        const mockResponse = {
          session_id: 'session-123',
          messages: [
            { id: '1', role: 'user', content: 'Hello', timestamp: '2024-01-01T00:00:00Z' },
            { id: '2', role: 'assistant', content: 'Hi there!', timestamp: '2024-01-01T00:01:00Z' },
          ],
        }

        ;(httpClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

        const result = await chatAgentService.getSessionHistory('session-123')

        expect(result.success).toBe(true)
        expect(result.data?.session_id).toBe('session-123')
        expect(result.data?.messages).toHaveLength(2)
      })
    })

    describe('deleteSession', () => {
      it('should delete a session successfully', async () => {
        const mockResponse = {
          status: 'deleted',
          session_id: 'session-to-delete',
        }

        ;(httpClient.delete as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

        const result = await chatAgentService.deleteSession('session-to-delete')

        expect(result.success).toBe(true)
        expect(result.data?.status).toBe('deleted')
        expect(httpClient.delete).toHaveBeenCalledWith('/api/v1/chat/sessions/session-to-delete')
      })

      it('should handle delete session not found', async () => {
        ;(httpClient.delete as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { data: { detail: 'Session not found' }, status: 404 } })

        const result = await chatAgentService.deleteSession('nonexistent')

        expect(result.success).toBe(false)
        expect(result.error).toBe('Session not found')
      })
    })
  })
})
