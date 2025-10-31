import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TenantHeader from '@/components/tenant/TenantHeader'

describe('TenantHeader', () => {
  it('should render tenant management title', () => {
    render(<TenantHeader tenantCount={5} onRefresh={vi.fn()} />)
    
    expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument()
    expect(screen.getByText(/Tenant Management/i)).toBeInTheDocument()
  })

  it('should display the correct tenant count in header', () => {
    const { rerender } = render(<TenantHeader tenantCount={5} onRefresh={vi.fn()} />)
    
    // Initial render with 5 tenants
    expect(screen.getByRole('heading')).toBeInTheDocument()
    
    // Update to 10 tenants
    rerender(<TenantHeader tenantCount={10} onRefresh={vi.fn()} />)
    expect(screen.getByRole('heading')).toBeInTheDocument()
  })

  it('should render refresh button', () => {
    render(<TenantHeader tenantCount={5} onRefresh={vi.fn()} />)
    
    const refreshButton = screen.getByRole('button', { name: /refresh/i })
    expect(refreshButton).toBeInTheDocument()
  })

  it('should call onRefresh when refresh button is clicked', async () => {
    const user = userEvent.setup()
    const mockOnRefresh = vi.fn()
    
    render(<TenantHeader tenantCount={5} onRefresh={mockOnRefresh} />)
    
    const refreshButton = screen.getByRole('button', { name: /refresh/i })
    await user.click(refreshButton)
    
    expect(mockOnRefresh).toHaveBeenCalledTimes(1)
  })

  it('should render building icon', () => {
    const { container } = render(<TenantHeader tenantCount={5} onRefresh={vi.fn()} />)
    
    const icon = container.querySelector('.bi-building')
    expect(icon).toBeInTheDocument()
  })

  it('should render refresh icon in button', () => {
    const { container } = render(<TenantHeader tenantCount={5} onRefresh={vi.fn()} />)
    
    const icon = container.querySelector('.bi-arrow-clockwise')
    expect(icon).toBeInTheDocument()
  })

  it('should handle multiple refresh clicks', async () => {
    const user = userEvent.setup()
    const mockOnRefresh = vi.fn()
    
    render(<TenantHeader tenantCount={5} onRefresh={mockOnRefresh} />)
    
    const refreshButton = screen.getByRole('button', { name: /refresh/i })
    
    await user.click(refreshButton)
    await user.click(refreshButton)
    await user.click(refreshButton)
    
    expect(mockOnRefresh).toHaveBeenCalledTimes(3)
  })

  it('should have proper styling classes', () => {
    const { container } = render(<TenantHeader tenantCount={5} onRefresh={vi.fn()} />)
    
    const headerContainer = container.firstChild
    expect(headerContainer).toHaveClass('d-flex', 'justify-content-between', 'align-items-center')
  })

  it('should render with zero tenants', () => {
    render(<TenantHeader tenantCount={0} onRefresh={vi.fn()} />)
    
    expect(screen.getByRole('heading')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument()
  })
})
