import '@testing-library/jest-dom'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import EmptyState from '@/components/common/EmptyState'

describe('EmptyState', () => {
  it('should render with required props', () => {
    const { container } = render(<EmptyState icon="bi-inbox" title="Empty State" />)
    
    expect(container.querySelector('.empty-state')).toBeInTheDocument()
  })

  it('should render with custom icon', () => {
    const { container } = render(<EmptyState icon="bi-inbox" title="Test" />)
    
    const icon = container.querySelector('.bi-inbox')
    expect(icon).toBeInTheDocument()
  })

  it('should render with custom title', () => {
    render(<EmptyState icon="bi-inbox" title="Custom Title" />)
    
    expect(screen.getByText('Custom Title')).toBeInTheDocument()
    expect(screen.getByText('Custom Title').tagName).toBe('H5')
  })

  it('should render with custom description', () => {
    render(<EmptyState icon="bi-inbox" title="Test" description="Custom description text" />)
    
    expect(screen.getByText('Custom description text')).toBeInTheDocument()
  })

  it('should render children when provided', () => {
    render(
      <EmptyState icon="bi-inbox" title="Test">
        <button>Custom Action</button>
      </EmptyState>
    )
    
    expect(screen.getByRole('button', { name: 'Custom Action' })).toBeInTheDocument()
  })

  it('should render with info variant', () => {
    const { container } = render(<EmptyState icon="bi-inbox" title="Test" variant="info" />)
    
    const icon = container.querySelector('.bi-inbox')
    expect(icon).toHaveClass('text-primary')
  })

  it('should render with warning variant', () => {
    const { container } = render(<EmptyState icon="bi-inbox" title="Test" variant="warning" />)
    
    const icon = container.querySelector('.bi-inbox')
    expect(icon).toHaveClass('text-warning')
  })

  it('should render with danger variant', () => {
    const { container } = render(<EmptyState icon="bi-inbox" title="Test" variant="danger" />)
    
    const icon = container.querySelector('.bi-inbox')
    expect(icon).toHaveClass('text-danger')
  })

  it('should render with success variant', () => {
    const { container } = render(<EmptyState icon="bi-inbox" title="Test" variant="success" />)
    
    const icon = container.querySelector('.bi-inbox')
    expect(icon).toHaveClass('text-success')
  })

  it('should render with info variant by default', () => {
    const { container } = render(<EmptyState icon="bi-inbox" title="Test" />)
    
    const icon = container.querySelector('.bi-inbox')
    expect(icon).toHaveClass('text-primary')
  })

  it('should render icon with correct classes', () => {
    const { container } = render(<EmptyState icon="bi-inbox" title="Test" />)
    
    const icon = container.querySelector('.bi-inbox')
    expect(icon).toHaveClass('empty-state-icon', 'd-block')
  })

  it('should render title as h5', () => {
    render(<EmptyState icon="bi-inbox" title="Test Title" />)
    
    const title = screen.getByText('Test Title')
    expect(title.tagName).toBe('H5')
  })

  it('should not render description when not provided', () => {
    const { container } = render(<EmptyState icon="bi-inbox" title="Only title" />)
    
    const paragraphs = container.querySelectorAll('p')
    expect(paragraphs).toHaveLength(0)
  })

  it('should render description when provided', () => {
    render(<EmptyState icon="bi-inbox" title="Test" description="Description text" />)
    
    expect(screen.getByText('Description text')).toBeInTheDocument()
  })

  it('should render all props together', () => {
    const { container } = render(
      <EmptyState
        icon="bi-inbox"
        title="Complete Example"
        description="This is a full example"
        variant="info"
      >
        <button>Action Button</button>
      </EmptyState>
    )
    
    expect(container.querySelector('.bi-inbox')).toBeInTheDocument()
    expect(screen.getByText('Complete Example')).toBeInTheDocument()
    expect(screen.getByText('This is a full example')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Action Button' })).toBeInTheDocument()
  })

  it('should have proper structure', () => {
    const { container } = render(<EmptyState icon="bi-inbox" title="Test" />)
    
    const emptyState = container.querySelector('.empty-state')
    expect(emptyState).toBeInTheDocument()
  })

  it('should render different icons correctly', () => {
    const { container: container1 } = render(<EmptyState icon="bi-inbox" title="Test" />)
    const { container: container2 } = render(<EmptyState icon="bi-folder" title="Test" />)
    
    expect(container1.querySelector('.bi-inbox')).toBeInTheDocument()
    expect(container2.querySelector('.bi-folder')).toBeInTheDocument()
  })

  it('should apply variant color to icon', () => {
    const { container } = render(<EmptyState icon="bi-inbox" title="Test" variant="danger" />)
    
    const icon = container.querySelector('.bi-inbox')
    expect(icon).toHaveClass('text-danger')
  })
})
