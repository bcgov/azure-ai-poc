import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DocumentDeleteConfirm from '@/components/chat/DocumentDeleteConfirm'
import type { Document } from '@/components/chat/DocumentList'

describe('DocumentDeleteConfirm', () => {
  const mockDocument: Document = {
    id: 'doc-123',
    filename: 'test-document.pdf',
    uploadedAt: '2024-01-20T10:00:00Z',
    totalPages: 10,
  }

  const mockGetFileIcon = vi.fn((filename: string) => {
    if (filename.endsWith('.pdf')) return 'bi-file-pdf'
    if (filename.endsWith('.md')) return 'bi-file-text'
    return 'bi-file-earmark'
  })

  const defaultProps = {
    show: true,
    document: mockDocument,
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
    isDeleting: false,
    getFileIcon: mockGetFileIcon,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should not render when show is false', () => {
    render(<DocumentDeleteConfirm {...defaultProps} show={false} />)
    
    expect(screen.queryByText('Confirm Delete')).not.toBeInTheDocument()
  })

  it('should render modal when show is true', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    expect(screen.getByText('Confirm Delete')).toBeInTheDocument()
  })

  it('should render warning icon in title', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    const title = screen.getByText('Confirm Delete')
    const icon = title.parentElement?.querySelector('.bi-exclamation-triangle')
    expect(icon).toBeInTheDocument()
  })

  it('should display document filename in confirmation message', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    expect(screen.getByText(/test-document.pdf/i)).toBeInTheDocument()
  })

  it('should call getFileIcon with document filename', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    expect(mockGetFileIcon).toHaveBeenCalledWith('test-document.pdf')
  })

  it('should render file icon based on document type', () => {
    const { container } = render(<DocumentDeleteConfirm {...defaultProps} />)
    
    const icon = document.body.querySelector('.bi-file-pdf')
    expect(icon).toBeInTheDocument()
  })

  it('should render default file icon when document is null', () => {
    const { container } = render(<DocumentDeleteConfirm {...defaultProps} document={null} />)
    
    const icon = document.body.querySelector('.bi-file-text')
    expect(icon).toBeInTheDocument()
  })

  it('should display warning message about permanent deletion', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    expect(screen.getByText(/This action cannot be undone/i)).toBeInTheDocument()
  })

  it('should render Cancel button', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    const cancelButton = screen.getByRole('button', { name: /Cancel/i })
    expect(cancelButton).toBeInTheDocument()
  })

  it('should render Delete button', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    const deleteButton = screen.getByRole('button', { name: /Delete Document/i })
    expect(deleteButton).toBeInTheDocument()
  })

  it('should call onCancel when Cancel button clicked', async () => {
    const user = userEvent.setup()
    const mockOnCancel = vi.fn()
    
    render(<DocumentDeleteConfirm {...defaultProps} onCancel={mockOnCancel} />)
    
    const cancelButton = screen.getByRole('button', { name: /Cancel/i })
    await user.click(cancelButton)
    
    expect(mockOnCancel).toHaveBeenCalledTimes(1)
  })

  it('should call onConfirm when Delete button clicked', async () => {
    const user = userEvent.setup()
    const mockOnConfirm = vi.fn()
    
    render(<DocumentDeleteConfirm {...defaultProps} onConfirm={mockOnConfirm} />)
    
    const deleteButton = screen.getByRole('button', { name: /Delete Document/i })
    await user.click(deleteButton)
    
    expect(mockOnConfirm).toHaveBeenCalledTimes(1)
  })

  it('should disable Cancel button when deleting', () => {
    render(<DocumentDeleteConfirm {...defaultProps} isDeleting={true} />)
    
    const cancelButton = screen.getByRole('button', { name: /Cancel/i })
    expect(cancelButton).toBeDisabled()
  })

  it('should disable Delete button when deleting', () => {
    render(<DocumentDeleteConfirm {...defaultProps} isDeleting={true} />)
    
    const deleteButton = screen.getByRole('button', { name: /Deleting.../i })
    expect(deleteButton).toBeDisabled()
  })

  it('should show spinner when deleting', () => {
    const { container } = render(<DocumentDeleteConfirm {...defaultProps} isDeleting={true} />)
    
    const spinner = document.body.querySelector('.spinner-border')
    expect(spinner).toBeInTheDocument()
  })

  it('should show "Deleting..." text when deleting', () => {
    render(<DocumentDeleteConfirm {...defaultProps} isDeleting={true} />)
    
    expect(screen.getByText(/Deleting.../i)).toBeInTheDocument()
  })

  it('should render Delete button with trash icon when not deleting', () => {
    const { container } = render(<DocumentDeleteConfirm {...defaultProps} isDeleting={false} />)
    
    const deleteButton = screen.getByRole('button', { name: /Delete Document/i })
    const icon = deleteButton.querySelector('.bi-trash')
    expect(icon).toBeInTheDocument()
  })

  it('should apply danger variant to Delete button', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    const deleteButton = screen.getByRole('button', { name: /Delete Document/i })
    expect(deleteButton).toHaveClass('btn-danger')
  })

  it('should apply secondary variant to Cancel button', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    const cancelButton = screen.getByRole('button', { name: /Cancel/i })
    expect(cancelButton).toHaveClass('btn-secondary')
  })

  it('should render "Delete Document" heading', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    expect(screen.getByRole('heading', { name: /Delete Document/i })).toBeInTheDocument()
  })

  it('should display warning about data removal', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    expect(screen.getByText(/permanently removed/i)).toBeInTheDocument()
  })

  it('should render modal with centered prop', () => {
    const { container } = render(<DocumentDeleteConfirm {...defaultProps} />)
    
    const modal = document.body.querySelector('.modal')
    expect(modal).toBeInTheDocument()
  })

  it('should render close button in header', () => {
    render(<DocumentDeleteConfirm {...defaultProps} />)
    
    const closeButton = document.body.querySelector('.btn-close')
    expect(closeButton).toBeInTheDocument()
  })

  it('should display file icon with correct size', () => {
    const { container } = render(<DocumentDeleteConfirm {...defaultProps} />)
    
    const icon = document.body.querySelector('.display-4')
    expect(icon).toBeInTheDocument()
  })

  it('should display file icon with danger color', () => {
    const { container } = render(<DocumentDeleteConfirm {...defaultProps} />)
    
    const icon = document.body.querySelector('.text-danger.display-4')
    expect(icon).toBeInTheDocument()
  })
})
