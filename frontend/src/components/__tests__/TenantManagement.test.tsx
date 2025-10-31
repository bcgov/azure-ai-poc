import { vi, describe, test, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import TenantManagement from '@/components/TenantManagement'
import { tenantService } from '@/services/tenantService'

// Mock the tenant service
vi.mock('@/services/tenantService', () => ({
  tenantService: {
    getTenants: vi.fn(),
    getTenantStats: vi.fn(),
    createTenantSearchIndex: vi.fn(),
    deleteTenantSearchIndex: vi.fn(),
    recreateTenantSearchIndex: vi.fn(),
    deleteTenant: vi.fn(),
  },
}))

// Mock authentication store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    user: {
      id: 'test-user',
      roles: ['SUPER_ADMIN'],
    },
    hasRole: vi.fn((role: string) => role === 'SUPER_ADMIN'),
  }),
}))

const mockTenantService = tenantService as any

describe('TenantManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Default successful responses
    mockTenantService.getTenants.mockResolvedValue({
      tenants: [
        {
          id: 'tenant-1',
          name: 'test-tenant',
          display_name: 'Test Tenant',
          description: 'A test tenant',
          status: 'active',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      pages: 1,
    })

    mockTenantService.getTenantStats.mockResolvedValue({
      tenant_id: 'tenant-1',
      user_count: 5,
      document_count: 10,
      storage_used_gb: 1.5,
      search_index_exists: true,
    })
  })

  test('renders tenant management heading', async () => {
    render(<TenantManagement />)

    await waitFor(() => {
      expect(screen.getByText('Tenant Management')).toBeInTheDocument()
    })
  })

  test('loads and displays tenants on mount', async () => {
    render(<TenantManagement />)

    await waitFor(() => {
      expect(mockTenantService.getTenants).toHaveBeenCalledWith(1, 20)
    })

    await waitFor(() => {
      expect(screen.getByText('Test Tenant')).toBeInTheDocument()
    })
  })

  test('displays tenant statistics', async () => {
    render(<TenantManagement />)

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument() // user count
      expect(screen.getByText('10')).toBeInTheDocument() // document count
      expect(screen.getByText('1.5 GB')).toBeInTheDocument() // storage used
    })
  })

  test('handles create search index action', async () => {
    mockTenantService.createTenantSearchIndex.mockResolvedValue(undefined)

    render(<TenantManagement />)

    // Wait for component to load data
    await waitFor(() => {
      expect(screen.getByText('Test Tenant')).toBeInTheDocument()
    })

    // Click the create search index button (icon button with title)
    const createIndexButton = screen.getByTitle('Create Search Index')
    fireEvent.click(createIndexButton)

    await waitFor(() => {
      expect(mockTenantService.createTenantSearchIndex).toHaveBeenCalledWith(
        'tenant-1',
      )
    })
  })

  test('handles delete tenant action with confirmation', async () => {
    mockTenantService.deleteTenantSearchIndex.mockResolvedValue(undefined)
    // Mock window.confirm to return true
    const originalConfirm = window.confirm
    window.confirm = vi.fn().mockReturnValue(true)

    render(<TenantManagement />)

    // Wait for component to load data
    await waitFor(() => {
      expect(screen.getByText('Test Tenant')).toBeInTheDocument()
    })

    // Click the delete search index button (icon button with title)
    const deleteButton = screen.getByTitle('Delete Search Index')
    fireEvent.click(deleteButton)

    await waitFor(() => {
      expect(mockTenantService.deleteTenantSearchIndex).toHaveBeenCalledWith(
        'tenant-1',
      )
    })

    // Restore original confirm
    window.confirm = originalConfirm
  })

  test('handles error when loading tenants fails', async () => {
    mockTenantService.getTenants.mockRejectedValue(new Error('API Error'))

    render(<TenantManagement />)

    await waitFor(() => {
      expect(screen.getByText(/Failed to load tenants/)).toBeInTheDocument()
    })
  })

  test('shows empty state when no tenants exist', async () => {
    mockTenantService.getTenants.mockResolvedValue({
      tenants: [],
      total: 0,
      page: 1,
      pages: 0,
    })

    render(<TenantManagement />)

    await waitFor(() => {
      expect(screen.getByText('No tenants found')).toBeInTheDocument()
    })
  })

  test('displays action buttons for tenants', async () => {
    render(<TenantManagement />)

    await waitFor(() => {
      expect(screen.getByText('Test Tenant')).toBeInTheDocument()
    })

    // Check if action buttons are present with their titles
    expect(screen.getByTitle('View Statistics')).toBeInTheDocument()
    expect(screen.getByTitle('Create Search Index')).toBeInTheDocument()
    expect(screen.getByTitle('Delete Search Index')).toBeInTheDocument()
  })
})
