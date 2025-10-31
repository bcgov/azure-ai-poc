import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TenantTable from '@/components/tenant/TenantTable'
import type { Tenant, TenantStats } from '@/services/tenantService'

describe('TenantTable', () => {
  const mockTenants: Tenant[] = [
    {
      id: 'tenant-1',
      name: 'Tenant One',
      display_name: 'Display One',
      description: 'First tenant',
      status: 'active',
      created_at: '2024-01-15T10:30:00Z',
      updated_at: '2024-01-15T10:30:00Z',
    },
    {
      id: 'tenant-2',
      name: 'Tenant Two',
      display_name: 'Display Two',
      description: 'Second tenant',
      status: 'inactive',
      created_at: '2024-01-16T10:30:00Z',
      updated_at: '2024-01-16T10:30:00Z',
    },
  ]

  const defaultProps = {
    tenants: mockTenants,
    onViewStats: vi.fn(),
    onCreateSearchIndex: vi.fn(),
    onDeleteSearchIndex: vi.fn(),
  }

  it('should render table headers', () => {
    render(<TenantTable {...defaultProps} />)
    
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Display Name')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Users')).toBeInTheDocument()
    expect(screen.getByText('Documents')).toBeInTheDocument()
    expect(screen.getByText('Storage')).toBeInTheDocument()
    expect(screen.getByText('Created')).toBeInTheDocument()
    expect(screen.getByText('Actions')).toBeInTheDocument()
  })

  it('should render all tenant rows', () => {
    render(<TenantTable {...defaultProps} />)
    
    expect(screen.getByText('Tenant One')).toBeInTheDocument()
    expect(screen.getByText('Tenant Two')).toBeInTheDocument()
  })

  it('should show empty state when no tenants', () => {
    render(<TenantTable {...defaultProps} tenants={[]} />)
    
    expect(screen.getByText(/No tenants found/i)).toBeInTheDocument()
  })

  it('should render table with card wrapper', () => {
    const { container } = render(<TenantTable {...defaultProps} />)
    
    const card = container.querySelector('.tenant-card')
    expect(card).toBeInTheDocument()
    
    const tableDiv = container.querySelector('.tenant-table')
    expect(tableDiv).toBeInTheDocument()
  })

  it('should render table with proper Bootstrap classes', () => {
    const { container } = render(<TenantTable {...defaultProps} />)
    
    const table = container.querySelector('table')
    expect(table).toHaveClass('table', 'table-hover')
  })

  it('should call onViewStats for the correct tenant', async () => {
    const user = userEvent.setup()
    const mockOnViewStats = vi.fn()
    
    render(<TenantTable {...defaultProps} onViewStats={mockOnViewStats} />)
    
    const viewStatsButtons = screen.getAllByTitle('View Statistics')
    await user.click(viewStatsButtons[0])
    
    expect(mockOnViewStats).toHaveBeenCalledWith(mockTenants[0])
  })

  it('should call onCreateSearchIndex for the correct tenant', async () => {
    const user = userEvent.setup()
    const mockOnCreate = vi.fn()
    
    render(<TenantTable {...defaultProps} onCreateSearchIndex={mockOnCreate} />)
    
    const createButtons = screen.getAllByTitle('Create Search Index')
    await user.click(createButtons[1])
    
    expect(mockOnCreate).toHaveBeenCalledWith('tenant-2')
  })

  it('should call onDeleteSearchIndex for the correct tenant', async () => {
    const user = userEvent.setup()
    const mockOnDelete = vi.fn()
    
    render(<TenantTable {...defaultProps} onDeleteSearchIndex={mockOnDelete} />)
    
    const deleteButtons = screen.getAllByTitle('Delete Search Index')
    await user.click(deleteButtons[0])
    
    expect(mockOnDelete).toHaveBeenCalledWith('tenant-1')
  })

  it('should render correct number of rows', () => {
    const { container } = render(<TenantTable {...defaultProps} />)
    
    const rows = container.querySelectorAll('tbody tr')
    expect(rows).toHaveLength(2)
  })

  it('should handle empty tenant array gracefully', () => {
    render(<TenantTable {...defaultProps} tenants={[]} />)
    
    const emptyState = screen.getByText(/No tenants found/i)
    expect(emptyState).toBeInTheDocument()
  })

  it('should render with single tenant', () => {
    render(<TenantTable {...defaultProps} tenants={[mockTenants[0]]} />)
    
    expect(screen.getByText('Tenant One')).toBeInTheDocument()
    expect(screen.queryByText('Tenant Two')).not.toBeInTheDocument()
  })

  it('should have proper table structure', () => {
    const { container } = render(<TenantTable {...defaultProps} />)
    
    const table = container.querySelector('table')
    const thead = table?.querySelector('thead')
    const tbody = table?.querySelector('tbody')
    
    expect(thead).toBeInTheDocument()
    expect(tbody).toBeInTheDocument()
  })

  it('should render column headers in correct order', () => {
    render(<TenantTable {...defaultProps} />)
    
    const headers = screen.getAllByRole('columnheader')
    expect(headers[0]).toHaveTextContent('Name')
    expect(headers[1]).toHaveTextContent('Display Name')
    expect(headers[2]).toHaveTextContent('Status')
    expect(headers[3]).toHaveTextContent('Users')
    expect(headers[4]).toHaveTextContent('Documents')
    expect(headers[5]).toHaveTextContent('Storage')
    expect(headers[6]).toHaveTextContent('Created')
    expect(headers[7]).toHaveTextContent('Actions')
  })
})
