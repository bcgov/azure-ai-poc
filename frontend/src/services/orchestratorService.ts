/**
 * Orchestrator Agent Service
 *
 * Service for interacting with the multi-agent orchestrator that coordinates
 * OrgBook and Geocoder agents for BC government data queries.
 */

import httpClient from './httpClient';

const API_BASE_URL = import.meta.env.VITE_API_MS_AGENT_URL || 'http://localhost:4000';

/**
 * Source information for citations
 */
export interface SourceInfo {
  source_type: 'api' | 'llm_knowledge' | 'document' | 'web' | 'unknown';
  description: string;
  confidence: 'high' | 'medium' | 'low';
  url?: string;
  api_endpoint?: string; // API endpoint path for API sources
  api_params?: Record<string, string>; // Query parameters for API sources
}

/**
 * Response from the orchestrator query endpoint
 */
export interface OrchestratorQueryResponse {
  response: string;
  sources: SourceInfo[];
  has_sufficient_info: boolean;
  key_findings: string[];
}

/**
 * Health status of the orchestrator services
 */
export interface OrchestratorHealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  services: {
    orchestrator: 'healthy' | 'degraded' | 'unhealthy';
    orgbook_api: 'healthy' | 'degraded' | 'unhealthy';
    geocoder_api: 'healthy' | 'degraded' | 'unhealthy';
  };
}

/**
 * Query the orchestrator agent for BC business and location information.
 *
 * @param query - Natural language query
 * @param sessionId - Optional session ID for tracking conversation context
 * @returns Promise with the orchestrator response including citations
 */
export async function queryOrchestrator(
  query: string,
  sessionId?: string
): Promise<OrchestratorQueryResponse> {
  const response = await httpClient.post<OrchestratorQueryResponse>(
    `/api/v1/orchestrator/query`,
    {
      query,
      session_id: sessionId,
    }
  );
  return response.data;
}

/**
 * Check the health status of the orchestrator and its sub-agents.
 *
 * @returns Promise with the health status
 */
export async function getOrchestratorHealth(): Promise<OrchestratorHealthStatus> {
  const response = await httpClient.get<OrchestratorHealthStatus>(
    `/api/v1/orchestrator/health`
  );
  return response.data;
}

export default {
  queryOrchestrator,
  getOrchestratorHealth,
};
