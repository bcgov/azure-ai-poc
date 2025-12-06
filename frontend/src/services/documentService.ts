/**
 * Document Service
 *
 * Service for document indexing and vector search using CosmosDB.
 * Provides functionality to index documents, search by semantic similarity,
 * and manage document storage.
 */

import { useAuthStore } from '../stores'
import httpClient from './httpClient'

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

// Request types
export interface IndexDocumentRequest {
  content: string
  document_id?: string
  title?: string
  metadata?: Record<string, unknown>
  chunk_size?: number
  chunk_overlap?: number
}

export interface SearchRequest {
  query: string
  top_k?: number
  document_id?: string
  min_similarity?: number
}

// Response types
export interface IndexDocumentResponse {
  document_id: string
  chunks_created: number
  message: string
}

export interface SearchResultItem {
  chunk_id: string
  document_id: string
  content: string
  similarity: number
  metadata: Record<string, unknown>
}

export interface SearchResponse {
  query: string
  results: SearchResultItem[]
  total: number
}

export interface DeleteDocumentResponse {
  status: string
  document_id: string
  chunks_deleted: number
}

export interface DocumentHealthResponse {
  status: string
  service: string
  cosmos_db: {
    status: string
    database?: string
    containers?: string[]
  }
}

// List documents types
export interface DocumentItem {
  id: string
  document_id: string
  title: string
  created_at?: string
  chunk_count: number
}

export interface DocumentListResponse {
  documents: DocumentItem[]
  total: number
}

class DocumentService {
  private baseUrl = '/api/v1/documents'

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

  private _parseError(error: any, fallback: string): string {
    if (error?.response?.data?.detail) return error.response.data.detail
    if (error?.response?.data?.error) return error.response.data.error
    if (error?.message) return error.message
    return fallback
  }

  /**
   * List all indexed documents for the current user
   */
  async listDocuments(limit: number = 50): Promise<ApiResponse<DocumentListResponse>> {
    try {
      await this.getAuthHeaders()
      const resp = await httpClient.get(`${this.baseUrl}/`, { params: { limit } })
      const data = resp.data as DocumentListResponse
      return { success: true, data }
    } catch (error: any) {
      console.error('List documents error:', error)
      return { success: false, error: this._parseError(error, 'Failed to list documents') }
    }
  }

  /**
   * Index a document for vector search
   *
   * The document is chunked and each chunk is embedded and stored in Cosmos DB.
   */
  async indexDocument(request: IndexDocumentRequest): Promise<ApiResponse<IndexDocumentResponse>> {
    try {
      await this.getAuthHeaders()
      const resp = await httpClient.post(`${this.baseUrl}/index`, {
        content: request.content,
        document_id: request.document_id,
        title: request.title,
        metadata: request.metadata,
        chunk_size: request.chunk_size ?? 1000,
        chunk_overlap: request.chunk_overlap ?? 200,
      })
      const data = resp.data as IndexDocumentResponse
      return { success: true, data }
    } catch (error: any) {
      console.error('Index document error:', error)
      return { success: false, error: this._parseError(error, 'Failed to index document') }
    }
  }

  /**
   * Perform vector similarity search across indexed documents
   */
  async search(request: SearchRequest): Promise<ApiResponse<SearchResponse>> {
    try {
      await this.getAuthHeaders()
      const resp = await httpClient.post(`${this.baseUrl}/search`, {
        query: request.query,
        top_k: request.top_k ?? 5,
        document_id: request.document_id,
        min_similarity: request.min_similarity ?? 0.0,
      })
      const data = resp.data as SearchResponse
      return { success: true, data }
    } catch (error: any) {
      console.error('Search documents error:', error)
      return { success: false, error: this._parseError(error, 'Failed to search documents') }
    }
  }

  /**
   * Delete a document and all its chunks
   */
  async deleteDocument(documentId: string): Promise<ApiResponse<DeleteDocumentResponse>> {
    try {
      await this.getAuthHeaders()
      const resp = await httpClient.delete(`${this.baseUrl}/${documentId}`)
      const data = resp.data as DeleteDocumentResponse
      return { success: true, data }
    } catch (error: any) {
      console.error('Delete document error:', error)
      return { success: false, error: this._parseError(error, 'Failed to delete document') }
    }
  }

  /**
   * Check if the document service is healthy
   */
  async healthCheck(): Promise<ApiResponse<DocumentHealthResponse>> {
    try {
      await this.getAuthHeaders()
      const resp = await httpClient.get(`${this.baseUrl}/health`)
      const data = resp.data as DocumentHealthResponse
      return { success: true, data }
    } catch (error: any) {
      console.error('Document service health check error:', error)
      return { success: false, error: this._parseError(error, 'Health check failed') }
    }
  }
}

// Export singleton instance
export const documentService = new DocumentService()
export default documentService
