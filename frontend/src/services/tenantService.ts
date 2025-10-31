import httpClient from './httpClient'
import { env } from '../env'

const API_BASE_URL = env.VITE_API_URL || 'http://localhost:3000/api/v1'

// Types for tenant management
export interface Tenant {
  id: string
  name: string
  display_name: string
  description?: string
  created_at: string
  updated_at: string
  status: 'active' | 'inactive' | 'suspended'
  quotas?: {
    max_users?: number
    max_documents?: number
    max_storage_gb?: number
  }
  metadata?: Record<string, any>
}

export interface CreateTenantRequest {
  name: string
  display_name: string
  description?: string
  quotas?: {
    max_users?: number
    max_documents?: number
    max_storage_gb?: number
  }
  metadata?: Record<string, any>
}

export interface UpdateTenantRequest {
  display_name?: string
  description?: string
  status?: 'active' | 'inactive' | 'suspended'
  quotas?: {
    max_users?: number
    max_documents?: number
    max_storage_gb?: number
  }
  metadata?: Record<string, any>
}

export interface TenantUser {
  user_id: string
  tenant_id: string
  roles: string[]
  added_at: string
  added_by: string
  status: 'active' | 'inactive'
  metadata?: Record<string, any>
}

export interface AddTenantUserRequest {
  user_id: string
  roles: string[]
  metadata?: Record<string, any>
}

export interface UpdateTenantUserRequest {
  roles?: string[]
  status?: 'active' | 'inactive'
  metadata?: Record<string, any>
}

export interface TenantStats {
  tenant_id: string
  user_count: number
  document_count: number
  storage_used_gb: number
  last_activity: string | null
  status: string
}

export interface SearchIndexStats {
  index_name: string
  document_count: number
  storage_size_bytes: number
  last_updated: string
  status: string
}

export interface TenantsListResponse {
  tenants: Tenant[]
  total: number
  page: number
  size: number
}

export interface TenantUsersListResponse {
  users: TenantUser[]
  total: number
}

export interface SearchIndexesListResponse {
  indexes: string[]
  total: number
}

// Tenant Management Service
export class TenantService {
  // Tenant CRUD operations
  async getTenants(
    page: number = 1,
    size: number = 10,
  ): Promise<TenantsListResponse> {
    const response = await httpClient.get(`${API_BASE_URL}/tenants`, {
      params: { page, size },
    })
    return response.data
  }

  async getTenant(tenantId: string): Promise<Tenant> {
    const response = await httpClient.get(`${API_BASE_URL}/tenants/${tenantId}`)
    return response.data
  }

  async createTenant(tenant: CreateTenantRequest): Promise<Tenant> {
    const response = await httpClient.post(`${API_BASE_URL}/tenants`, tenant)
    return response.data
  }

  async updateTenant(
    tenantId: string,
    updates: UpdateTenantRequest,
  ): Promise<Tenant> {
    const response = await httpClient.put(
      `${API_BASE_URL}/tenants/${tenantId}`,
      updates,
    )
    return response.data
  }

  async deleteTenant(tenantId: string): Promise<void> {
    await httpClient.delete(`${API_BASE_URL}/tenants/${tenantId}`)
  }

  async getTenantStats(tenantId: string): Promise<TenantStats> {
    const response = await httpClient.get(
      `${API_BASE_URL}/tenants/${tenantId}/stats`,
    )
    return response.data
  }

  async getTenantHealth(tenantId: string): Promise<any> {
    const response = await httpClient.get(
      `${API_BASE_URL}/tenants/${tenantId}/health`,
    )
    return response.data
  }

  // Tenant User Management
  async getTenantUsers(tenantId: string): Promise<TenantUsersListResponse> {
    const response = await httpClient.get(
      `${API_BASE_URL}/tenants/${tenantId}/users`,
    )
    return response.data
  }

  async addTenantUser(
    tenantId: string,
    user: AddTenantUserRequest,
  ): Promise<TenantUser> {
    const response = await httpClient.post(
      `${API_BASE_URL}/tenants/${tenantId}/users`,
      user,
    )
    return response.data
  }

  async updateTenantUser(
    tenantId: string,
    userId: string,
    updates: UpdateTenantUserRequest,
  ): Promise<TenantUser> {
    const response = await httpClient.put(
      `${API_BASE_URL}/tenants/${tenantId}/users/${userId}`,
      updates,
    )
    return response.data
  }

  async removeTenantUser(tenantId: string, userId: string): Promise<void> {
    await httpClient.delete(
      `${API_BASE_URL}/tenants/${tenantId}/users/${userId}`,
    )
  }

  // Search Index Management
  async createTenantSearchIndex(tenantId: string): Promise<any> {
    const response = await httpClient.post(
      `${API_BASE_URL}/tenants/${tenantId}/search-index`,
    )
    return response.data
  }

  async deleteTenantSearchIndex(tenantId: string): Promise<any> {
    const response = await httpClient.delete(
      `${API_BASE_URL}/tenants/${tenantId}/search-index`,
    )
    return response.data
  }

  async getTenantSearchIndexStats(tenantId: string): Promise<SearchIndexStats> {
    const response = await httpClient.get(
      `${API_BASE_URL}/tenants/${tenantId}/search-index/stats`,
    )
    return response.data
  }

  async recreateTenantSearchIndex(tenantId: string): Promise<any> {
    const response = await httpClient.post(
      `${API_BASE_URL}/tenants/${tenantId}/search-index/recreate`,
    )
    return response.data
  }

  async getAllSearchIndexes(): Promise<SearchIndexesListResponse> {
    const response = await httpClient.get(
      `${API_BASE_URL}/tenants/search-indexes`,
    )
    return response.data
  }
}

// Export singleton instance
export const tenantService = new TenantService()
