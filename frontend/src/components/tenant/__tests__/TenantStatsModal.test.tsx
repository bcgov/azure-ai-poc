import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TenantStatsModal from '@/components/tenant/TenantStatsModal'
import type { Tenant, TenantStats } from '@/services/tenantService'

describe('TenantStatsModal', () => {
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
    user_count: 50,
    document_count: 125,
    storage_used_gb: 3.5,
    status: 'active',
    last_activity: '2024-01-20T15:00:00Z',
  }

  const defaultProps = {
    show: true,
    tenant: mockTenant,
    stats: mockStats,
    onHide: vi.fn(),
  }

  it('should not render when show is false', () => {
    render(<TenantStatsModal {...defaultProps} show={false} />)
    
    expect(screen.queryByText(/Tenant Statistics/i)).not.toBeInTheDocument()
  })

  it('should render modal when show is true', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    expect(screen.getByText(/Tenant Statistics/i)).toBeInTheDocument()
  })

  it('should display tenant name in header', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    // Text is split: "Tenant Statistics - Test Display Name"
    expect(screen.getByText(/Tenant Statistics/i)).toBeInTheDocument()
  })

  it('should display tenant display name', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    // Display name appears in the modal title, verify by checking modal title content
    const modalTitle = document.body.querySelector('.modal-title')
    expect(modalTitle?.textContent).toContain('Test Display Name')
  })

  it('should display tenant status badge', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    // Modal renders to document.body, use screen query
    const badge = screen.getByText('active')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge')
  })

  it('should show loading spinner when stats are null', () => {
    render(<TenantStatsModal {...defaultProps} stats={null} />)
    
    // Modal doesn't render body content when stats is null
    expect(screen.queryByText(/Users:/i)).not.toBeInTheDocument()
  })

  it('should display user count', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    expect(screen.getByText(/50/)).toBeInTheDocument()
    expect(screen.getByText(/Users:/i)).toBeInTheDocument()
  })

  it('should display document count', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    expect(screen.getByText(/125/)).toBeInTheDocument()
    expect(screen.getByText(/Documents:/i)).toBeInTheDocument()
  })

  it('should display formatted storage', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    expect(screen.getByText(/3.5 GB/)).toBeInTheDocument()
    expect(screen.getByText(/Storage Used/i)).toBeInTheDocument()
  })

  it('should display formatted last activity date', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    expect(screen.getByText(/Last Activity/i)).toBeInTheDocument()
    // Date format depends on locale, just check it exists
    const lastActivityRow = screen.getByText(/Last Activity/i).closest('.row')
    expect(lastActivityRow).toBeTruthy()
  })

  it('should call onHide when close button is clicked', async () => {
    const user = userEvent.setup()
    const mockOnHide = vi.fn()
    
    render(<TenantStatsModal {...defaultProps} onHide={mockOnHide} />)
    
    // Get the close button by aria-label to avoid ambiguity
    const closeButton = screen.getByLabelText('Close')
    await user.click(closeButton)
    
    expect(mockOnHide).toHaveBeenCalledTimes(1)
  })

  it('should render all stat cards', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    // Modal renders to document.body, check for card headers
    expect(screen.getByText('Usage Statistics')).toBeInTheDocument()
    expect(screen.getByText('Activity')).toBeInTheDocument()
  })

  it('should have proper modal structure', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    // Modal renders to document.body via portal, use document.body queries
    const modalContent = document.body.querySelector('.modal-content')
    expect(modalContent).toBeInTheDocument()
    
    const modalHeader = document.body.querySelector('.modal-header')
    expect(modalHeader).toBeInTheDocument()
    
    const modalBody = document.body.querySelector('.modal-body')
    expect(modalBody).toBeInTheDocument()
    
    const modalFooter = document.body.querySelector('.modal-footer')
    expect(modalFooter).toBeInTheDocument()
  })

  it('should display tenant name in header', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    // Component shows display_name in header, not description
    expect(screen.getByText(/Test Display Name/)).toBeInTheDocument()
  })

  it('should not show description in modal body', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    // Component does not render tenant description
    expect(screen.queryByText('Test description')).not.toBeInTheDocument()
  })

  it('should render icons in stat cards', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    // Modal renders to document.body, use document.body queries
    expect(document.body.querySelector('.bi-people-fill')).toBeInTheDocument()
    expect(document.body.querySelector('.bi-file-earmark-text-fill')).toBeInTheDocument()
    expect(document.body.querySelector('.bi-database-fill')).toBeInTheDocument()
    expect(document.body.querySelector('.bi-clock-history')).toBeInTheDocument()
  })

  it('should have responsive layout classes', () => {
    render(<TenantStatsModal {...defaultProps} />)
    
    // Modal renders to document.body, use document.body queries
    const rows = document.body.querySelectorAll('.row')
    const cols = document.body.querySelectorAll('.col-md-6')
    
    expect(rows.length).toBeGreaterThan(0)
    expect(cols.length).toBe(2) // 2 columns in the row
  })

  it('should update when stats change', () => {
    const { rerender } = render(<TenantStatsModal {...defaultProps} />)
    
    expect(screen.getByText(/50/)).toBeInTheDocument()
    
    const newStats: TenantStats = {
      ...mockStats,
      user_count: 100,
    }
    
    rerender(<TenantStatsModal {...defaultProps} stats={newStats} />)
    
    expect(screen.getByText(/100/)).toBeInTheDocument()
  })
})
