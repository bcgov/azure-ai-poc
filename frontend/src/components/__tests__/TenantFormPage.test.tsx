import { vi, describe, test, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import TenantFormPage from '@/components/TenantFormPage'

// Mock the tenant service
vi.mock('@/services/tenantService', () => ({
  tenantService: {
    getTenant: vi.fn(),
    createTenant: vi.fn(),
    updateTenant: vi.fn(),
  },
}))

// Mock TanStack Router
const mockNavigate = vi.fn()
vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => mockNavigate,
}))

import { tenantService } from '@/services/tenantService'
const mockTenantService = tenantService as any

const mockTenant = {
  id: 'tenant-1',
  name: 'test-tenant',
  display_name: 'Test Tenant',
  description: 'A test tenant',
  status: 'active' as const,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  quotas: {
    max_users: 100,
    max_documents: 1000,
    max_storage_gb: 10,
  },
}

describe('TenantFormPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockTenantService.getTenant.mockResolvedValue(mockTenant)
    mockTenantService.createTenant.mockResolvedValue(mockTenant)
    mockTenantService.updateTenant.mockResolvedValue(mockTenant)
  })

  test('renders create tenant form when no tenantId provided', () => {
    render(<TenantFormPage />)

    expect(screen.getByText('New Tenant')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Create Tenant' }),
    ).toBeInTheDocument()
  })

  test('renders edit tenant form when tenantId provided', async () => {
    render(<TenantFormPage tenantId="tenant-1" />)

    await waitFor(() => {
      expect(mockTenantService.getTenant).toHaveBeenCalledWith('tenant-1')
    })

    await waitFor(() => {
      expect(screen.getByText('Edit Tenant')).toBeInTheDocument()
    })
  })

  test('loads tenant data when editing', async () => {
    render(<TenantFormPage tenantId="tenant-1" />)

    await waitFor(() => {
      expect(mockTenantService.getTenant).toHaveBeenCalledWith('tenant-1')
    })

    await waitFor(() => {
      expect(screen.getByDisplayValue('test-tenant')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Test Tenant')).toBeInTheDocument()
      expect(screen.getByDisplayValue('A test tenant')).toBeInTheDocument()
      expect(screen.getByDisplayValue('100')).toBeInTheDocument()
      expect(screen.getByDisplayValue('1000')).toBeInTheDocument()
      expect(screen.getByDisplayValue('10')).toBeInTheDocument()
    })
  })

  test('validates required fields', async () => {
    render(<TenantFormPage />)

    const saveButton = screen.getByRole('button', { name: 'Create Tenant' })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText('Name is required')).toBeInTheDocument()
      expect(screen.getByText('Display name is required')).toBeInTheDocument()
    })
  })

  test('validates name format', async () => {
    render(<TenantFormPage />)

    const nameInput = screen.getByPlaceholderText('my-tenant')
    fireEvent.change(nameInput, { target: { value: 'Invalid Name!' } })

    const saveButton = screen.getByRole('button', { name: 'Create Tenant' })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(
        screen.getByText(
          'Name must contain only lowercase letters, numbers, and hyphens',
        ),
      ).toBeInTheDocument()
    })
  })

  test('creates new tenant successfully', async () => {
    render(<TenantFormPage />)

    // Fill in required fields
    fireEvent.change(screen.getByPlaceholderText('my-tenant'), {
      target: { value: 'new-tenant' },
    })
    fireEvent.change(screen.getByPlaceholderText('My Tenant'), {
      target: { value: 'New Tenant' },
    })
    fireEvent.change(
      screen.getByPlaceholderText('Brief description of this tenant...'),
      {
        target: { value: 'A new tenant' },
      },
    )

    const saveButton = screen.getByRole('button', { name: 'Create Tenant' })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(mockTenantService.createTenant).toHaveBeenCalledWith({
        name: 'new-tenant',
        display_name: 'New Tenant',
        description: 'A new tenant',
      })
    })

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith({ to: '/tenants' })
    })
  })

  test('updates existing tenant successfully', async () => {
    render(<TenantFormPage tenantId="tenant-1" />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Tenant')).toBeInTheDocument()
    })

    // Update display name
    const displayNameInput = screen.getByDisplayValue('Test Tenant')
    fireEvent.change(displayNameInput, {
      target: { value: 'Updated Test Tenant' },
    })

    const saveButton = screen.getByText('Update Tenant')
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(mockTenantService.updateTenant).toHaveBeenCalledWith('tenant-1', {
        display_name: 'Updated Test Tenant',
        description: 'A test tenant',
        status: 'active',
        quotas: {
          max_users: 100,
          max_documents: 1000,
          max_storage_gb: 10,
        },
      })
    })

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith({ to: '/tenants' })
    })
  })

  test('handles API errors during creation', async () => {
    mockTenantService.createTenant.mockRejectedValue({
      response: { data: { detail: 'Tenant name already exists' } },
    })

    render(<TenantFormPage />)

    // Fill in required fields
    fireEvent.change(screen.getByPlaceholderText('my-tenant'), {
      target: { value: 'existing-tenant' },
    })
    fireEvent.change(screen.getByPlaceholderText('My Tenant'), {
      target: { value: 'Existing Tenant' },
    })

    const saveButton = screen.getByRole('button', { name: 'Create Tenant' })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText('Tenant name already exists')).toBeInTheDocument()
    })
  })

  test('handles loading error when fetching tenant', async () => {
    mockTenantService.getTenant.mockRejectedValue(new Error('API Error'))

    render(<TenantFormPage tenantId="tenant-1" />)

    await waitFor(() => {
      expect(
        screen.getByText('Failed to load tenant details. Please try again.'),
      ).toBeInTheDocument()
    })
  })

  test('shows loading spinner while fetching tenant data', async () => {
    mockTenantService.getTenant.mockImplementation(() => new Promise(() => {}))

    render(<TenantFormPage tenantId="tenant-1" />)

    expect(screen.getByText('Loading tenant details...')).toBeInTheDocument()
  })

  test('navigates back on cancel button click', async () => {
    render(<TenantFormPage />)

    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)

    expect(mockNavigate).toHaveBeenCalledWith({ to: '/tenants' })
  })

  test('navigates back on back arrow click', async () => {
    render(<TenantFormPage />)

    const backButton = screen.getByRole('button', { name: '' }) // Back arrow button
    fireEvent.click(backButton)

    expect(mockNavigate).toHaveBeenCalledWith({ to: '/tenants' })
  })

  test('clears validation errors when user starts typing', async () => {
    render(<TenantFormPage />)

    // Trigger validation error
    const saveButton = screen.getByRole('button', { name: 'Create Tenant' })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText('Name is required')).toBeInTheDocument()
    })

    // Start typing to clear error
    const nameInput = screen.getByPlaceholderText('my-tenant')
    fireEvent.change(nameInput, { target: { value: 'a' } })

    expect(screen.queryByText('Name is required')).not.toBeInTheDocument()
  })

  test('disables form controls while saving', async () => {
    render(<TenantFormPage />)

    // Fill required fields
    fireEvent.change(screen.getByPlaceholderText('my-tenant'), {
      target: { value: 'test-tenant' },
    })
    fireEvent.change(screen.getByPlaceholderText('My Tenant'), {
      target: { value: 'Test Tenant' },
    })

    // Mock slow API response
    mockTenantService.createTenant.mockImplementation(
      () => new Promise(() => {}),
    )

    const saveButton = screen.getByRole('button', { name: 'Create Tenant' })
    fireEvent.click(saveButton)

    // Button should be disabled while saving
    await waitFor(() => {
      expect(saveButton).toBeDisabled()
    })

    // Cancel button should also be disabled
    const cancelButton = screen.getByText('Cancel')
    expect(cancelButton).toBeDisabled()
  })
})
