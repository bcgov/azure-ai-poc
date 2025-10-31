import { vi, describe, test, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import TenantsListPage from '@/components/TenantsListPage'

// Mock the tenant service
vi.mock('@/services/tenantService', () => ({
  tenantService: {
    getTenants: vi.fn(),
    getTenantStats: vi.fn(),
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
    hasRole: vi.fn((role: string): role is any => role === 'SUPER_ADMIN'),
  }),
}))

import { tenantService } from '@/services/tenantService'
const mockTenantService = tenantService as any

describe('TenantsListPage', () => {
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
        {
          id: 'tenant-2',
          name: 'test-tenant-2',
          display_name: 'Test Tenant 2',
          description: 'Another test tenant',
          status: 'inactive',
          created_at: '2024-01-02T00:00:00Z',
          updated_at: '2024-01-02T00:00:00Z',
        },
      ],
      total: 2,
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
    render(<TenantsListPage />)

    await waitFor(() => {
      expect(screen.getByText('Tenant Management')).toBeInTheDocument()
    })
  })

  test('renders create tenant button as disabled', async () => {
    render(<TenantsListPage />)

    await waitFor(() => {
      const createButton = screen.getByText('Create Tenant')
      expect(createButton).toBeInTheDocument()
      expect(createButton).toBeDisabled()
    })
  })

  test('loads and displays tenants in table format', async () => {
    render(<TenantsListPage />)

    await waitFor(() => {
      expect(mockTenantService.getTenants).toHaveBeenCalledWith(1, 10)
    })

    await waitFor(() => {
      expect(screen.getByText('Test Tenant')).toBeInTheDocument()
      expect(screen.getByText('Test Tenant 2')).toBeInTheDocument()
    })

    // Check table headers
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Users')).toBeInTheDocument()
    expect(screen.getByText('Documents')).toBeInTheDocument()
    expect(screen.getByText('Storage')).toBeInTheDocument()
  })

  test('displays tenant status badges correctly', async () => {
    render(<TenantsListPage />)

    await waitFor(() => {
      expect(screen.getByText('active')).toBeInTheDocument()
      expect(screen.getByText('inactive')).toBeInTheDocument()
    })
  })

  test('displays loading spinner while fetching data', async () => {
    // Make the API call hang to test loading state
    mockTenantService.getTenants.mockImplementation(() => new Promise(() => {}))

    render(<TenantsListPage />)

    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  test('handles error when loading tenants fails', async () => {
    mockTenantService.getTenants.mockRejectedValue(new Error('API Error'))

    render(<TenantsListPage />)

    await waitFor(() => {
      expect(
        screen.getByText(/Failed to load tenants. Please try again./),
      ).toBeInTheDocument()
    })
  })

  test('shows empty state when no tenants exist', async () => {
    mockTenantService.getTenants.mockResolvedValue({
      tenants: [],
      total: 0,
      page: 1,
      pages: 0,
    })

    render(<TenantsListPage />)

    await waitFor(() => {
      expect(screen.getByText('No tenants found')).toBeInTheDocument()
    })
  })

  test('handles tenant deletion flow', async () => {
    mockTenantService.deleteTenant.mockResolvedValue(undefined)

    render(<TenantsListPage />)

    await waitFor(() => {
      expect(screen.getByText('Test Tenant')).toBeInTheDocument()
    })

    // Find and click the dropdown button (icon button)
    const actionButtons = screen.getAllByRole('button')
    const dropdownButton = actionButtons.find((btn) =>
      btn.querySelector('.bi-three-dots-vertical'),
    )
    expect(dropdownButton).toBeTruthy()
    fireEvent.click(dropdownButton!)

    const deleteButton = screen.getByText('Delete')
    fireEvent.click(deleteButton)

    // Confirm deletion in modal
    const confirmButton = screen.getByRole('button', { name: 'Delete Tenant' })
    fireEvent.click(confirmButton)

    await waitFor(() => {
      expect(mockTenantService.deleteTenant).toHaveBeenCalledWith('tenant-1')
    })
  })

  test('handles pagination when multiple pages exist', async () => {
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
      total: 15,
      page: 1,
      pages: 2,
    })

    render(<TenantsListPage />)

    await waitFor(() => {
      expect(screen.getByText('Test Tenant')).toBeInTheDocument()
    })

    // Check pagination controls
    expect(screen.getByText('Next')).toBeInTheDocument()
    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument()
  })

  test('displays tenant statistics correctly', async () => {
    render(<TenantsListPage />)

    await waitFor(() => {
      expect(screen.getAllByText('5')).toHaveLength(2) // user count for both tenants
      expect(screen.getAllByText('10')).toHaveLength(2) // document count for both tenants
      expect(screen.getAllByText('1.5 GB')).toHaveLength(2) // storage used for both tenants
    })
  })

  test('handles stats loading failure gracefully', async () => {
    mockTenantService.getTenantStats.mockRejectedValue(
      new Error('Stats API Error'),
    )

    render(<TenantsListPage />)

    await waitFor(() => {
      expect(screen.getByText('Test Tenant')).toBeInTheDocument()
    })

    // Should still show the tenant even if stats fail to load
    expect(screen.getByText('Test Tenant')).toBeInTheDocument()
  })

  test('cancels deletion when modal is closed', async () => {
    render(<TenantsListPage />)

    await waitFor(() => {
      expect(screen.getByText('Test Tenant')).toBeInTheDocument()
    })

    // Find and click the dropdown button (icon button)
    const actionButtons = screen.getAllByRole('button')
    const dropdownButton = actionButtons.find((btn) =>
      btn.querySelector('.bi-three-dots-vertical'),
    )
    expect(dropdownButton).toBeTruthy()
    fireEvent.click(dropdownButton!)

    const deleteButton = screen.getByText('Delete')
    fireEvent.click(deleteButton)

    // Cancel deletion
    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)

    // Should not call delete API
    expect(mockTenantService.deleteTenant).not.toHaveBeenCalled()
  })
})
