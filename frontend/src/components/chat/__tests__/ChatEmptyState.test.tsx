import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChatEmptyState from '@/components/chat/ChatEmptyState'

describe('ChatEmptyState', () => {
  const mockOnUploadClick = vi.fn()

  beforeEach(() => {
    mockOnUploadClick.mockClear()
  })

  it('should render upload prompt when no documents', () => {
    render(<ChatEmptyState documentsCount={0} onUploadClick={mockOnUploadClick} />)
    
    expect(screen.getByText(/Get Started with Document Q&A/i)).toBeInTheDocument()
  })

  it('should render upload button when no documents', () => {
    render(<ChatEmptyState documentsCount={0} onUploadClick={mockOnUploadClick} />)
    
    const uploadButton = screen.getByRole('button', { name: /Upload Your First Document/i })
    expect(uploadButton).toBeInTheDocument()
  })

  it('should call onUploadClick when upload button is clicked', async () => {
    const user = userEvent.setup()
    render(<ChatEmptyState documentsCount={0} onUploadClick={mockOnUploadClick} />)
    
    const uploadButton = screen.getByRole('button', { name: /Upload Your First Document/i })
    await user.click(uploadButton)
    
    expect(mockOnUploadClick).toHaveBeenCalledTimes(1)
  })

  it('should display supported formats when no documents', () => {
    render(<ChatEmptyState documentsCount={0} onUploadClick={mockOnUploadClick} />)
    
    expect(screen.getByText(/Supported formats:/i)).toBeInTheDocument()
    expect(screen.getByText('PDF')).toBeInTheDocument()
    expect(screen.getByText('Markdown')).toBeInTheDocument()
    expect(screen.getByText('HTML')).toBeInTheDocument()
  })

  it('should render cloud upload icon when no documents', () => {
    const { container } = render(<ChatEmptyState documentsCount={0} onUploadClick={mockOnUploadClick} />)
    
    const icon = container.querySelector('.bi-cloud-upload')
    expect(icon).toBeInTheDocument()
  })

  it('should render welcome message when documents exist', () => {
    render(<ChatEmptyState documentsCount={5} onUploadClick={mockOnUploadClick} />)
    
    expect(screen.getByText(/Welcome to AI Document Assistant/i)).toBeInTheDocument()
  })

  it('should not render upload button when documents exist', () => {
    render(<ChatEmptyState documentsCount={5} onUploadClick={mockOnUploadClick} />)
    
    const uploadButton = screen.queryByRole('button', { name: /Upload Your First Document/i })
    expect(uploadButton).not.toBeInTheDocument()
  })

  it('should render chat icon when documents exist', () => {
    const { container } = render(<ChatEmptyState documentsCount={5} onUploadClick={mockOnUploadClick} />)
    
    const icon = container.querySelector('.bi-chat-quote')
    expect(icon).toBeInTheDocument()
  })

  it('should render description about uploading and searching when documents exist', () => {
    render(<ChatEmptyState documentsCount={5} onUploadClick={mockOnUploadClick} />)
    
    expect(screen.getByText(/Upload documents/i)).toBeInTheDocument()
    expect(screen.getByText(/search across all your uploaded documents/i)).toBeInTheDocument()
  })

  it('should display file type icons when no documents', () => {
    const { container } = render(<ChatEmptyState documentsCount={0} onUploadClick={mockOnUploadClick} />)
    
    expect(container.querySelector('.bi-file-pdf')).toBeInTheDocument()
    expect(container.querySelector('.bi-file-text')).toBeInTheDocument()
    expect(container.querySelector('.bi-file-code')).toBeInTheDocument()
  })

  it('should have upload button icon', () => {
    const { container } = render(<ChatEmptyState documentsCount={0} onUploadClick={mockOnUploadClick} />)
    
    const button = screen.getByRole('button', { name: /Upload Your First Document/i })
    const icon = button.querySelector('.bi-cloud-upload')
    expect(icon).toBeInTheDocument()
  })

  it('should display format badges with secondary variant', () => {
    const { container } = render(<ChatEmptyState documentsCount={0} onUploadClick={mockOnUploadClick} />)
    
    const badges = container.querySelectorAll('.badge.bg-secondary')
    expect(badges.length).toBe(3) // PDF, Markdown, HTML
  })
})
