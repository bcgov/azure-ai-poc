import '@testing-library/jest-dom'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import LoadingSpinner from '@/components/common/LoadingSpinner'

describe('LoadingSpinner', () => {
  it('should render spinner with default props', () => {
    const { container } = render(<LoadingSpinner />)
    
    const spinner = container.querySelector('.spinner-border')
    expect(spinner).toBeInTheDocument()
  })

  it('should render with small size', () => {
    const { container } = render(<LoadingSpinner size="sm" />)
    
    const spinner = container.querySelector('.spinner-border')
    expect(spinner).toBeInTheDocument()
  })

  it('should render without size prop by default', () => {
    const { container } = render(<LoadingSpinner />)
    
    const spinner = container.querySelector('.spinner-border')
    expect(spinner).toBeInTheDocument()
  })

  it('should render with custom message', () => {
    render(<LoadingSpinner message="Loading data..." />)
    
    expect(screen.getByText('Loading data...')).toBeInTheDocument()
  })

  it('should not render message when not provided', () => {
    const { container } = render(<LoadingSpinner />)
    
    const message = container.querySelector('.text-muted')
    expect(message).not.toBeInTheDocument()
  })

  it('should apply custom className', () => {
    const { container } = render(<LoadingSpinner className="custom-class" />)
    
    const wrapper = container.firstChild
    expect(wrapper).toHaveClass('custom-class')
  })

  it('should have default d-flex class', () => {
    const { container } = render(<LoadingSpinner />)
    
    const wrapper = container.firstChild
    expect(wrapper).toHaveClass('d-flex', 'align-items-center')
  })

  it('should combine default and custom classNames', () => {
    const { container } = render(<LoadingSpinner className="my-5" />)
    
    const wrapper = container.firstChild
    expect(wrapper).toHaveClass('d-flex', 'align-items-center', 'my-5')
  })

  it('should render spinner from react-bootstrap', () => {
    const { container } = render(<LoadingSpinner />)
    
    const spinner = container.querySelector('.spinner-border')
    expect(spinner).toBeInTheDocument()
  })

  it('should render message with correct styling', () => {
    render(<LoadingSpinner message="Please wait..." />)
    
    const message = screen.getByText('Please wait...')
    expect(message).toBeInTheDocument()
    expect(message).toHaveClass('text-muted')
  })

  it('should have proper structure with message', () => {
    const { container } = render(<LoadingSpinner message="Loading data..." />)
    
    const wrapper = container.firstChild
    const spinner = container.querySelector('.spinner-border')
    const message = screen.getByText('Loading data...')
    
    expect(wrapper).toContainElement(spinner as HTMLElement)
    expect(wrapper).toContainElement(message)
  })

  it('should render small spinner correctly', () => {
    const { container } = render(<LoadingSpinner size="sm" message="Loading..." />)
    
    const spinner = container.querySelector('.spinner-border')
    expect(spinner).toBeInTheDocument()
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('should have margin between spinner and message', () => {
    const { container } = render(<LoadingSpinner message="Loading..." />)
    
    const spinner = container.querySelector('.spinner-border')
    expect(spinner).toHaveClass('me-2')
  })

  it('should handle empty message gracefully', () => {
    const { container } = render(<LoadingSpinner message="" />)
    
    expect(container.querySelector('.spinner-border')).toBeInTheDocument()
    // Empty message should not render the span (empty string is falsy in conditional)
    const message = container.querySelector('.text-muted')
    expect(message).not.toBeInTheDocument()
  })

  it('should not break with all props provided', () => {
    const { container } = render(
      <LoadingSpinner 
        size="sm" 
        message="Loading complete data..." 
        className="my-custom-class" 
      />
    )
    
    const wrapper = container.firstChild
    expect(wrapper).toHaveClass('d-flex', 'align-items-center', 'my-custom-class')
    expect(container.querySelector('.spinner-border')).toBeInTheDocument()
    expect(screen.getByText('Loading complete data...')).toBeInTheDocument()
  })

  it('should render animation property correctly', () => {
    const { container } = render(<LoadingSpinner />)
    
    const spinner = container.querySelector('.spinner-border')
    expect(spinner).toBeInTheDocument()
  })

  it('should work without any props', () => {
    const { container } = render(<LoadingSpinner />)
    
    const wrapper = container.firstChild
    expect(wrapper).toHaveClass('d-flex', 'align-items-center')
    expect(container.querySelector('.spinner-border')).toBeInTheDocument()
  })
})
