/**
 * Research Agent Service Tests
 *
 * Tests for the Microsoft Agent Framework research service with human-in-the-loop
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
import { researchAgentService } from '@/services/researchAgentService'

describe('ResearchAgentService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(httpClient, 'post').mockResolvedValue({ data: {} } as any)
    vi.spyOn(httpClient, 'get').mockResolvedValue({ data: {} } as any)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('startResearch', () => {
    it('should start a research workflow successfully', async () => {
      const mockResponse = {
        run_id: 'run-123',
        topic: 'What is AI?',
        status: 'started',
        current_phase: 'planning',
      }

      ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const result = await researchAgentService.startResearch('What is AI?')

      expect(result.success).toBe(true)
      expect(result.data?.run_id).toBe('run-123')
      expect(httpClient.post).toHaveBeenCalledWith('/api/v1/research/start', expect.objectContaining({ topic: 'What is AI?' }))
    })

    it('should handle start errors', async () => {
      ;(httpClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { data: { detail: 'Invalid topic' }, status: 400 } })

      const result = await researchAgentService.startResearch('')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Invalid topic')
    })
  })

  describe('runWorkflow', () => {
    it('should run a workflow step', async () => {
      const mockResponse = {
        run_id: 'run-123',
        status: 'completed',
        current_phase: 'report_generation',
        final_report: 'Research findings...',
      }

      ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const result = await researchAgentService.runWorkflow('run-123')

      expect(result.success).toBe(true)
      expect(result.data?.status).toBe('completed')
      expect(httpClient.post).toHaveBeenCalledWith('/api/v1/research/run/run-123')
    })
  })

  describe('getWorkflowStatus', () => {
    it('should get workflow status', async () => {
      const mockStatus = {
        run_id: 'run-123',
        current_phase: 'research',
        topic: 'AI topic',
        has_plan: true,
        findings_count: 2,
        has_report: false,
        pending_approvals: 0,
      }

      ;(httpClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockStatus })

      const result = await researchAgentService.getWorkflowStatus('run-123')

      expect(result.success).toBe(true)
      expect(result.data?.current_phase).toBe('research')
    })

    it('should handle status not found', async () => {
      ;(httpClient.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ response: { data: { detail: 'Run not found' }, status: 404 } })

      const result = await researchAgentService.getWorkflowStatus('invalid-run')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Run not found')
    })
  })

  describe('sendApproval', () => {
    it('should send approval for a checkpoint', async () => {
      const mockResponse = {
        run_id: 'run-123',
        request_id: 'request-456',
        status: 'approved',
        approved: true,
      }

      ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const result = await researchAgentService.sendApproval(
        'run-123',
        'request-456',
        true,
        'Proceed with research',
      )

      expect(result.success).toBe(true)
      expect(httpClient.post).toHaveBeenCalledWith('/api/v1/research/run/run-123/approve', expect.objectContaining({ request_id: 'request-456', approved: true }))
    })

    it('should send rejection', async () => {
      const mockResponse = {
        run_id: 'run-123',
        request_id: 'request-456',
        status: 'rejected',
        approved: false,
      }

      ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const result = await researchAgentService.sendApproval(
        'run-123',
        'request-456',
        false,
        'Do not search external sites',
      )

      expect(result.success).toBe(true)
      expect(httpClient.post).toHaveBeenCalledWith('/api/v1/research/run/run-123/approve', expect.objectContaining({ request_id: 'request-456', approved: false }))
    })
  })

  describe('startWorkflowResearch', () => {
    it('should start a workflow research', async () => {
      const mockResponse = {
        run_id: 'workflow-123',
        topic: 'AI research',
        status: 'started',
        current_phase: 'planning',
        require_approval: false,
      }

      ;(httpClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse })

      const result = await researchAgentService.startWorkflowResearch('AI research')

      expect(result.success).toBe(true)
      expect(result.data?.run_id).toBe('workflow-123')
    })
  })
})
