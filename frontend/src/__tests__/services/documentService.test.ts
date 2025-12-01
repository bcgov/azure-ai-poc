/**
 * Document Service Tests
 *
 * Tests for the document indexing and vector search service
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
import { documentService } from '@/services/documentService'

describe('DocumentService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(httpClient, 'get').mockResolvedValue({ data: {} } as any)
    vi.spyOn(httpClient, 'post').mockResolvedValue({ data: {} } as any)
    vi.spyOn(httpClient, 'delete').mockResolvedValue({ data: {} } as any)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('listDocuments', () => {
    it('should list documents successfully', async () => {
      const mockResponse = {
        documents: [
          {
            id: 'doc-1',
            document_id: 'doc-1',
            title: 'Test Document 1',
            created_at: '2024-01-01T00:00:00Z',
            chunk_count: 5,
          },
          {
            id: 'doc-2',
            document_id: 'doc-2',
            title: 'Test Document 2',
            created_at: '2024-01-02T00:00:00Z',
            chunk_count: 3,
          },
        ],
        total: 2,
      }

      ;(httpClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const result = await documentService.listDocuments()

      expect(result.success).toBe(true)
      expect(result.data?.total).toBe(2)
      expect(result.data?.documents).toHaveLength(2)
      expect(result.data?.documents[0].title).toBe('Test Document 1')
    })

    it('should handle list documents errors', async () => {
      ;(httpClient.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { data: { detail: 'List failed' } } })

      const result = await documentService.listDocuments()

      expect(result.success).toBe(false)
      expect(result.error).toBe('List failed')
    })
  })

  describe('indexDocument', () => {
    it('should index a document successfully', async () => {
      const mockResponse = {
        document_id: 'doc-123',
        chunks_created: 5,
        message: 'Document indexed successfully with 5 chunks',
      }

      ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const result = await documentService.indexDocument({
        content: 'This is a test document content.',
        title: 'Test Document',
      })

      expect(result.success).toBe(true)
      expect(result.data?.document_id).toBe('doc-123')
      expect(result.data?.chunks_created).toBe(5)
      expect(httpClient.post).toHaveBeenCalledWith('/api/v1/documents/index', expect.objectContaining({ content: 'This is a test document content.' }))
    })

    it('should handle indexing errors', async () => {
      ;(httpClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { data: { detail: 'Content too short' } } })

      const result = await documentService.indexDocument({
        content: '',
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Content too short')
    })
  })

  describe('search', () => {
    it('should search documents successfully', async () => {
      const mockResponse = {
        query: 'test query',
        results: [
          {
            chunk_id: 'chunk-1',
            document_id: 'doc-123',
            content: 'Relevant content here',
            similarity: 0.95,
            metadata: { title: 'Test Doc' },
          },
          {
            chunk_id: 'chunk-2',
            document_id: 'doc-123',
            content: 'More relevant content',
            similarity: 0.85,
            metadata: { title: 'Test Doc' },
          },
        ],
        total: 2,
      }

      ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const result = await documentService.search({
        query: 'test query',
        top_k: 5,
      })

      expect(result.success).toBe(true)
      expect(result.data?.results).toHaveLength(2)
      expect(result.data?.results[0].similarity).toBe(0.95)
      expect(httpClient.post).toHaveBeenCalledWith('/api/v1/documents/search', expect.objectContaining({ query: 'test query' }))
    })

    it('should filter by document_id when provided', async () => {
      const mockResponse = {
        query: 'specific search',
        results: [],
        total: 0,
      }

      ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      await documentService.search({
        query: 'specific search',
        document_id: 'specific-doc-id',
      })

      const callArgs = (httpClient.post as ReturnType<typeof vi.fn>).mock.calls[0]
      const callBody = callArgs[1]
      expect(callBody.document_id).toBe('specific-doc-id')
    })

    it('should handle search errors', async () => {
      ;(httpClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { data: { detail: 'Search failed' } } })

      const result = await documentService.search({
        query: 'test',
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Search failed')
    })
  })

  describe('deleteDocument', () => {
    it('should delete a document successfully', async () => {
      const mockResponse = {
        status: 'deleted',
        document_id: 'doc-to-delete',
        chunks_deleted: 5,
      }

      ;(httpClient.delete as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const result = await documentService.deleteDocument('doc-to-delete')

      expect(result.success).toBe(true)
      expect(result.data?.status).toBe('deleted')
      expect(result.data?.chunks_deleted).toBe(5)
      expect(httpClient.delete).toHaveBeenCalledWith('/api/v1/documents/doc-to-delete')
    })

    it('should handle delete errors', async () => {
      ;(httpClient.delete as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { data: { detail: 'Delete failed' } } })

      const result = await documentService.deleteDocument('doc-id')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Delete failed')
    })
  })

  describe('healthCheck', () => {
    it('should return health status with cosmos_db info', async () => {
      const mockResponse = {
        status: 'ok',
        service: 'documents',
        cosmos_db: {
          status: 'healthy',
          database: 'ai-documents',
          containers: ['embeddings', 'chat_history'],
        },
      }

      ;(httpClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const result = await documentService.healthCheck()

      expect(result.success).toBe(true)
      expect(result.data?.status).toBe('ok')
      expect(result.data?.cosmos_db.status).toBe('healthy')
    })

    it('should handle health check failure', async () => {
      ;(httpClient.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { status: 503 } })

      const result = await documentService.healthCheck()

      expect(result.success).toBe(false)
      expect(result.error).toContain('Health check failed')
    })
  })
})
