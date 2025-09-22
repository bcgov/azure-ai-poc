import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Mock import.meta.env before importing the service
vi.stubGlobal('import', {
  meta: {
    env: {
      VITE_API_URL: 'http://test-api.local',
    },
  },
})

// Mock fetch
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

import type { LangGraphAgentRequest } from '@/services/langGraphAgentService'
import { langGraphAgentService } from '@/services/langGraphAgentService'

describe('LangGraphAgentService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock environment variable
    vi.stubEnv('VITE_API_URL', 'http://test-api.local')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  describe('sendMessage', () => {
    it('should send a message successfully', async () => {
      const mockResponse = {
        response: 'Test response',
        session_id: 'test-session',
        metadata: {
          steps: 3,
          tools_used: ['search', 'calculator'],
          reasoning: 'Test reasoning',
        },
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const request: LangGraphAgentRequest = {
        message: 'Test message',
        session_id: 'test-session',
        user_id: 'test-user',
      }

      const result = await langGraphAgentService.sendMessage(request)

      expect(result.success).toBe(true)
      expect(result.data).toEqual(mockResponse)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/chat/agent',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        },
      )
    })

    it('should handle API errors', async () => {
      const errorResponse = {
        detail: 'Invalid request',
      }

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => errorResponse,
      })

      const request: LangGraphAgentRequest = {
        message: 'Test message',
      }

      const result = await langGraphAgentService.sendMessage(request)

      expect(result.success).toBe(false)
      expect(result.error).toBe('Invalid request')
    })

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      const request: LangGraphAgentRequest = {
        message: 'Test message',
      }

      const result = await langGraphAgentService.sendMessage(request)

      expect(result.success).toBe(false)
      expect(result.error).toBe('Network error')
    })
  })

  describe('streamMessage', () => {
    it('should simulate streaming with chunks', async () => {
      const mockResponse = {
        response: 'Hello world test',
        session_id: 'test-session',
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const chunks: string[] = []
      const errors: string[] = []

      const onChunk = (chunk: string) => chunks.push(chunk)
      const onError = (error: string) => errors.push(error)

      const request: LangGraphAgentRequest = {
        message: 'Test message',
      }

      await langGraphAgentService.streamMessage(request, onChunk, onError)

      expect(errors).toHaveLength(0)
      expect(chunks.length).toBeGreaterThan(0)
      expect(chunks[chunks.length - 1]).toBe('Hello world test')
    })
  })

  describe('getCapabilities', () => {
    it('should return capabilities when endpoint exists', async () => {
      const mockCapabilities = {
        tools: ['search', 'calculator', 'weather'],
        features: ['reasoning', 'memory'],
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCapabilities,
      })

      const result = await langGraphAgentService.getCapabilities()

      expect(result.success).toBe(true)
      expect(result.data).toEqual(mockCapabilities)
    })

    it('should return fallback capabilities when endpoint fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      })

      const result = await langGraphAgentService.getCapabilities()

      expect(result.success).toBe(false)
      expect(result.data).toEqual({
        tools: ['document_search', 'weather', 'calculator'],
        features: [
          'multi-step reasoning',
          'tool chaining',
          'memory persistence',
        ],
      })
    })
  })
})
