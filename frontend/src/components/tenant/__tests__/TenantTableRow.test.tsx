import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TenantTableRow from '@/components/tenant/TenantTableRow'
import type { Tenant, TenantStats } from '@/services/tenantService'

describe('TenantTableRow', () => {
  const mockTenant: Tenant = {
    id: 'tenant-123',
    name: 'Test Tenant',
    display_name: 'Test Display Name',
    description: 'Test description',
    status: 'active',
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T10:30:00Z',
  }

  const mockStats: TenantStats = {
    tenant_id: 'tenant-123',
    user_count: 10,
    document_count: 25,
    storage_used_gb: 1.5,
    status: 'active',
    last_activity: '2024-01-20T15:00:00Z',
  }

  const defaultProps = {
    tenant: mockTenant,
    onViewStats: vi.fn(),
    onCreateSearchIndex: vi.fn(),
    onDeleteSearchIndex: vi.fn(),
  }

  it('should render tenant name', () => {
    render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} />
        </tbody>
      </table>
    )
    
    expect(screen.getByText('Test Tenant')).toBeInTheDocument()
  })

  it('should render tenant display name', () => {
    render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} />
        </tbody>
      </table>
    )
    
    expect(screen.getByText('Test Display Name')).toBeInTheDocument()
  })

  it('should render tenant description', () => {
    render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} />
        </tbody>
      </table>
    )
    
    expect(screen.getByText('Test description')).toBeInTheDocument()
  })

  it('should not render description when not provided', () => {
    const tenantWithoutDesc = { ...mockTenant, description: undefined }
    
    render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} tenant={tenantWithoutDesc} />
        </tbody>
      </table>
    )
    
    expect(screen.queryByText('Test description')).not.toBeInTheDocument()
  })

  it('should render status badge', () => {
    const { container } = render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} />
        </tbody>
      </table>
    )
    
    const badge = container.querySelector('.badge')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent('active')
  })

  it('should show loading spinner when stats are not loaded', () => {
    const { container } = render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} />
        </tbody>
      </table>
    )
    
    const spinners = container.querySelectorAll('.spinner-border')
    expect(spinners.length).toBeGreaterThan(0)
  })

  it('should display stats when available', () => {
    const tenantWithStats = { ...mockTenant, stats: mockStats }
    
    render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} tenant={tenantWithStats} />
        </tbody>
      </table>
    )
    
    expect(screen.getByText('10')).toBeInTheDocument() // user_count
    expect(screen.getByText('25')).toBeInTheDocument() // document_count
  })

  it('should format storage correctly', () => {
    const tenantWithStats = { ...mockTenant, stats: mockStats }
    
    render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} tenant={tenantWithStats} />
        </tbody>
      </table>
    )
    
    expect(screen.getByText('1.5 GB')).toBeInTheDocument()
  })

  it('should format date correctly', () => {
    render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} />
        </tbody>
      </table>
    )
    
    // Date should be formatted (exact format depends on locale)
    const cells = screen.getAllByRole('cell')
    const dateCell = cells.find(cell => cell.textContent?.includes('/') || cell.textContent?.includes('-'))
    expect(dateCell).toBeTruthy()
  })

  it('should render action buttons', () => {
    render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} />
        </tbody>
      </table>
    )
    
    expect(screen.getByTitle('View Statistics')).toBeInTheDocument()
    expect(screen.getByTitle('Create Search Index')).toBeInTheDocument()
    expect(screen.getByTitle('Delete Search Index')).toBeInTheDocument()
  })

  it('should call onViewStats when view stats button is clicked', async () => {
    const user = userEvent.setup()
    const mockOnViewStats = vi.fn()
    
    render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} onViewStats={mockOnViewStats} />
        </tbody>
      </table>
    )
    
    const viewStatsButton = screen.getByTitle('View Statistics')
    await user.click(viewStatsButton)
    
    expect(mockOnViewStats).toHaveBeenCalledWith(mockTenant)
  })

  it('should call onCreateSearchIndex with tenant id', async () => {
    const user = userEvent.setup()
    const mockOnCreate = vi.fn()
    
    render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} onCreateSearchIndex={mockOnCreate} />
        </tbody>
      </table>
    )
    
    const createButton = screen.getByTitle('Create Search Index')
    await user.click(createButton)
    
    expect(mockOnCreate).toHaveBeenCalledWith('tenant-123')
  })

  it('should call onDeleteSearchIndex with tenant id', async () => {
    const user = userEvent.setup()
    const mockOnDelete = vi.fn()
    
    render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} onDeleteSearchIndex={mockOnDelete} />
        </tbody>
      </table>
    )
    
    const deleteButton = screen.getByTitle('Delete Search Index')
    await user.click(deleteButton)
    
    expect(mockOnDelete).toHaveBeenCalledWith('tenant-123')
  })

  it('should have proper table row styling', () => {
    const { container } = render(
      <table>
        <tbody>
          <TenantTableRow {...defaultProps} />
        </tbody>
      </table>
    )
    
    const row = container.querySelector('tr')
    expect(row).toBeInTheDocument()
  })
})
