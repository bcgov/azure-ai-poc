import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TenantActions from '@/components/tenant/TenantActions'

describe('TenantActions', () => {
  const defaultProps = {
    tenantId: 'tenant-123',
    onViewStats: vi.fn(),
    onCreateSearchIndex: vi.fn(),
    onDeleteSearchIndex: vi.fn(),
  }

  it('should render all three action buttons', () => {
    render(<TenantActions {...defaultProps} />)
    
    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(3)
  })

  it('should render view stats button with correct icon', () => {
    const { container } = render(<TenantActions {...defaultProps} />)
    
    const viewStatsButton = screen.getByTitle('View Statistics')
    expect(viewStatsButton).toBeInTheDocument()
    
    const icon = viewStatsButton.querySelector('.bi-bar-chart')
    expect(icon).toBeInTheDocument()
  })

  it('should render create search index button with correct icon', () => {
    const { container } = render(<TenantActions {...defaultProps} />)
    
    const createButton = screen.getByTitle('Create Search Index')
    expect(createButton).toBeInTheDocument()
    
    const icon = createButton.querySelector('.bi-plus-circle')
    expect(icon).toBeInTheDocument()
  })

  it('should render delete search index button with correct icon', () => {
    const { container } = render(<TenantActions {...defaultProps} />)
    
    const deleteButton = screen.getByTitle('Delete Search Index')
    expect(deleteButton).toBeInTheDocument()
    
    const icon = deleteButton.querySelector('.bi-trash')
    expect(icon).toBeInTheDocument()
  })

  it('should call onViewStats when view stats button is clicked', async () => {
    const user = userEvent.setup()
    const mockOnViewStats = vi.fn()
    
    render(<TenantActions {...defaultProps} onViewStats={mockOnViewStats} />)
    
    const viewStatsButton = screen.getByTitle('View Statistics')
    await user.click(viewStatsButton)
    
    expect(mockOnViewStats).toHaveBeenCalledTimes(1)
  })

  it('should call onCreateSearchIndex when create button is clicked', async () => {
    const user = userEvent.setup()
    const mockOnCreate = vi.fn()
    
    render(<TenantActions {...defaultProps} onCreateSearchIndex={mockOnCreate} />)
    
    const createButton = screen.getByTitle('Create Search Index')
    await user.click(createButton)
    
    expect(mockOnCreate).toHaveBeenCalledTimes(1)
  })

  it('should call onDeleteSearchIndex when delete button is clicked', async () => {
    const user = userEvent.setup()
    const mockOnDelete = vi.fn()
    
    render(<TenantActions {...defaultProps} onDeleteSearchIndex={mockOnDelete} />)
    
    const deleteButton = screen.getByTitle('Delete Search Index')
    await user.click(deleteButton)
    
    expect(mockOnDelete).toHaveBeenCalledTimes(1)
  })

  it('should have proper button variants', () => {
    render(<TenantActions {...defaultProps} />)
    
    const viewStatsButton = screen.getByTitle('View Statistics')
    const createButton = screen.getByTitle('Create Search Index')
    const deleteButton = screen.getByTitle('Delete Search Index')
    
    expect(viewStatsButton).toHaveClass('btn-outline-primary')
    expect(createButton).toHaveClass('btn-outline-success')
    expect(deleteButton).toHaveClass('btn-outline-danger')
  })

  it('should have small size buttons', () => {
    render(<TenantActions {...defaultProps} />)
    
    const buttons = screen.getAllByRole('button')
    buttons.forEach(button => {
      expect(button).toHaveClass('btn-sm')
    })
  })

  it('should render buttons in a flex gap container', () => {
    const { container } = render(<TenantActions {...defaultProps} />)
    
    const buttonContainer = container.firstChild
    expect(buttonContainer).toHaveClass('d-flex', 'gap-2')
  })

  it('should handle rapid clicks on different buttons', async () => {
    const user = userEvent.setup()
    const mockOnViewStats = vi.fn()
    const mockOnCreate = vi.fn()
    const mockOnDelete = vi.fn()
    
    render(
      <TenantActions
        {...defaultProps}
        onViewStats={mockOnViewStats}
        onCreateSearchIndex={mockOnCreate}
        onDeleteSearchIndex={mockOnDelete}
      />
    )
    
    const viewStatsButton = screen.getByTitle('View Statistics')
    const createButton = screen.getByTitle('Create Search Index')
    const deleteButton = screen.getByTitle('Delete Search Index')
    
    await user.click(viewStatsButton)
    await user.click(createButton)
    await user.click(deleteButton)
    
    expect(mockOnViewStats).toHaveBeenCalledTimes(1)
    expect(mockOnCreate).toHaveBeenCalledTimes(1)
    expect(mockOnDelete).toHaveBeenCalledTimes(1)
  })
})
