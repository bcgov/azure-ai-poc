/**
 * Research Agent Service
 *
 * Service for interacting with the Microsoft Agent Framework research endpoints.
 * Provides deep research functionality with human-in-the-loop approval.
 */

import { useAuthStore } from '../stores'
import httpClient from './httpClient'

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

// ==================== Research Agent Types ====================

export interface StartResearchRequest {
  topic: string
  user_id?: string
  model?: string
}

export interface StartResearchResponse {
  run_id: string
  topic: string
  status: string
  current_phase: string
}

export interface ResearchPlan {
  main_topic: string
  research_questions: string[]
  subtopics: string[]
  methodology: string
  estimated_depth?: string
}

export interface ResearchFinding {
  subtopic: string
  content: string
  confidence: string
  key_points?: string[]
}

export interface WorkflowResult {
  run_id: string
  status: string
  current_phase?: string
  plan?: ResearchPlan
  findings?: ResearchFinding[]
  final_report?: string
  workflow_state?: string
  error?: string
}

export interface WorkflowStatus {
  run_id: string
  current_phase: string
  topic: string
  has_plan: boolean
  findings_count: number
  has_report: boolean
  pending_approvals: number
}

export interface ApprovalRequest {
  request_id: string
  approved: boolean
  feedback?: string
}

export interface ApprovalResponse {
  run_id: string
  request_id: string
  status: string
  approved: boolean
}

// ==================== Workflow Research Types ====================

export interface StartWorkflowResearchRequest {
  topic: string
  require_approval?: boolean
  user_id?: string
  model?: string
}

export interface StartWorkflowResearchResponse {
  run_id: string
  topic: string
  status: string
  current_phase: string
  require_approval: boolean
}

export interface WorkflowResearchResult {
  run_id: string
  status: string
  current_phase: string
  topic?: string
  plan?: ResearchPlan
  findings?: ResearchFinding[]
  final_report?: string
  report_preview?: string
  message?: string
  error?: string
}

export interface WorkflowResearchStatus {
  run_id: string
  current_phase: string
  topic: string
  require_approval: boolean
  has_plan: boolean
  findings_count: number
  has_report: boolean
  error?: string
}

export interface WorkflowApprovalRequest {
  approved: boolean
  feedback?: string
}

export interface WorkflowApprovalResponse {
  run_id: string
  status: string
  approved: boolean
  current_phase: string
  final_report?: string
  plan?: ResearchPlan
  findings?: ResearchFinding[]
  feedback?: string
}

class ResearchAgentService {
  private researchBaseUrl = '/api/v1/research'
  private workflowBaseUrl = '/api/v1/workflow-research'

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

  // ==================== Research Agent Methods (Human-in-the-loop) ====================

  /**
   * Start a new research workflow with human-in-the-loop approval
   */
  async startResearch(
    topic: string,
    userId?: string,
    model?: string,
  ): Promise<ApiResponse<StartResearchResponse>> {
    try {
      await this.getAuthHeaders()
      const resp = await httpClient.post(`${this.researchBaseUrl}/start`, { topic, user_id: userId, model })
      const data = resp.data as StartResearchResponse
      return { success: true, data }
    } catch (error) {
      console.error('Start research error:', error)
      return {
        success: false,
        error: this._parseError(error, 'Failed to start research'),
      }
    }
  }

  /**
   * Execute the research workflow
   */
  async runWorkflow(runId: string): Promise<ApiResponse<WorkflowResult>> {
    try {
      await this.getAuthHeaders()
      const resp = await httpClient.post(`${this.researchBaseUrl}/run/${runId}`)
      const data = resp.data as WorkflowResult
      return { success: true, data }
    } catch (error) {
      console.error('Run workflow error:', error)
      return {
        success: false,
        error: this._parseError(error, 'Failed to run workflow'),
      }
    }
  }

  /**
   * Get workflow status
   */
  async getWorkflowStatus(runId: string): Promise<ApiResponse<WorkflowStatus>> {
    try {
      await this.getAuthHeaders()
      const resp = await httpClient.get(`${this.researchBaseUrl}/run/${runId}/status`)
      const data = resp.data as WorkflowStatus
      return { success: true, data }
    } catch (error) {
      console.error('Get workflow status error:', error)
      return {
        success: false,
        error: this._parseError(error, 'Failed to get workflow status'),
      }
    }
  }

  /**
   * Send approval for a pending checkpoint
   */
  async sendApproval(
    runId: string,
    requestId: string,
    approved: boolean,
    feedback?: string,
  ): Promise<ApiResponse<ApprovalResponse>> {
    try {
      await this.getAuthHeaders()
      const request: ApprovalRequest = { request_id: requestId, approved, feedback }
      const resp = await httpClient.post(`${this.researchBaseUrl}/run/${runId}/approve`, request)
      const data = resp.data as ApprovalResponse
      return { success: true, data }
    } catch (error) {
      console.error('Send approval error:', error)
      return {
        success: false,
        error: this._parseError(error, 'Failed to send approval'),
      }
    }
  }

  // ==================== Workflow Research Methods (Auto-running) ====================

  /**
   * Start a workflow research (runs automatically unless approval requested)
   */
  async startWorkflowResearch(
    topic: string,
    requireApproval?: boolean,
    userId?: string,
    model?: string,
  ): Promise<ApiResponse<StartWorkflowResearchResponse>> {
    try {
      await this.getAuthHeaders()
      const request: StartWorkflowResearchRequest = { topic, require_approval: requireApproval, user_id: userId, model }
      const resp = await httpClient.post(`${this.workflowBaseUrl}/start`, request)
      const data = resp.data as StartWorkflowResearchResponse
      return { success: true, data }
    } catch (error) {
      console.error('Start workflow research error:', error)
      return {
        success: false,
        error: this._parseError(error, 'Failed to start workflow research'),
      }
    }
  }

  /**
   * Execute the workflow research
   */
  async runWorkflowResearch(runId: string): Promise<ApiResponse<WorkflowResearchResult>> {
    try {
      await this.getAuthHeaders()
      const resp = await httpClient.post(`${this.workflowBaseUrl}/run/${runId}`)
      const data = resp.data as WorkflowResearchResult
      return { success: true, data }
    } catch (error) {
      console.error('Run workflow research error:', error)
      return {
        success: false,
        error: this._parseError(error, 'Failed to run workflow research'),
      }
    }
  }

  /**
   * Get workflow research status
   */
  async getWorkflowResearchStatus(runId: string): Promise<ApiResponse<WorkflowResearchStatus>> {
    try {
      await this.getAuthHeaders()
      const resp = await httpClient.get(`${this.workflowBaseUrl}/run/${runId}/status`)
      const data = resp.data as WorkflowResearchStatus
      return { success: true, data }
    } catch (error) {
      console.error('Get workflow research status error:', error)
      return {
        success: false,
        error: this._parseError(error, 'Failed to get workflow research status'),
      }
    }
  }

  /**
   * Send approval for workflow research
   */
  async sendWorkflowApproval(
    runId: string,
    approved: boolean,
    feedback?: string,
  ): Promise<ApiResponse<WorkflowApprovalResponse>> {
    try {
      await this.getAuthHeaders()
      const request: WorkflowApprovalRequest = { approved, feedback }
      const resp = await httpClient.post(`${this.workflowBaseUrl}/run/${runId}/approve`, request)
      const data = resp.data as WorkflowApprovalResponse
      return { success: true, data }
    } catch (error) {
      console.error('Send workflow approval error:', error)
      return {
        success: false,
        error: this._parseError(error, 'Failed to send workflow approval'),
      }
    }
  }

  // ==================== Health Checks ====================

  /**
   * Check research service health
   */
  async researchHealthCheck(): Promise<ApiResponse<{ status: string; service: string }>> {
    try {
      const resp = await httpClient.get(`${this.researchBaseUrl}/health`)
      if (!response.ok) {
        throw new Error(`Health check failed: HTTP ${response.status}`)
      }
      const data = await response.json()
      return { success: true, data }
    } catch (error) {
      return {
        success: false,
        error: this._parseError(error, 'Health check failed'),
      }
    }
  }

  /**
   * Check workflow research service health
   */
  async workflowResearchHealthCheck(): Promise<
    ApiResponse<{ status: string; service: string; features: string[] }>
  > {
    try {
      const resp = await httpClient.get(`${this.workflowBaseUrl}/health`)
      if (!response.ok) {
        throw new Error(`Health check failed: HTTP ${response.status}`)
      }
      const data = await response.json()
      return { success: true, data }
    } catch (error) {
      return {
        success: false,
        error: this._parseError(error, 'Health check failed'),
      }
    }
  }
}

// Export singleton instance
export const researchAgentService = new ResearchAgentService()
export default researchAgentService
