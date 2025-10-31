import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DocumentList from '@/components/chat/DocumentList'
import type { Document } from '@/components/chat/DocumentList'

describe('DocumentList', () => {
  const mockDocuments: Document[] = [
    {
      id: 'doc-1',
      filename: 'document1.pdf',
      uploadedAt: '2024-01-20T10:00:00Z',
      totalPages: 10,
    },
    {
      id: 'doc-2',
      filename: 'document2.md',
      uploadedAt: '2024-01-21T10:00:00Z',
    },
  ]

  const mockGetFileIcon = vi.fn((filename: string) => {
    if (filename.endsWith('.pdf')) return 'bi-file-pdf'
    if (filename.endsWith('.md')) return 'bi-file-text'
    return 'bi-file-earmark'
  })

  const defaultProps = {
    documents: mockDocuments,
    selectedDocument: null,
    onSelectDocument: vi.fn(),
    onDeleteDocument: vi.fn(),
    isLoadingDocuments: false,
    getFileIcon: mockGetFileIcon,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render loading spinner when loading', () => {
    render(<DocumentList {...defaultProps} isLoadingDocuments={true} />)
    
    expect(screen.getByText(/Loading documents.../i)).toBeInTheDocument()
  })

  it('should render nothing when no documents and not loading', () => {
    const { container } = render(<DocumentList {...defaultProps} documents={[]} />)
    
    expect(container.firstChild).toBeNull()
  })

  it('should render "Across All Docs" button', () => {
    render(<DocumentList {...defaultProps} />)
    
    const allDocsButton = screen.getByRole('button', { name: /Across All Docs/i })
    expect(allDocsButton).toBeInTheDocument()
  })

  it('should highlight "Across All Docs" button when no document selected', () => {
    render(<DocumentList {...defaultProps} selectedDocument={null} />)
    
    const allDocsButton = screen.getByRole('button', { name: /Across All Docs/i })
    expect(allDocsButton).toHaveClass('btn-primary')
  })

  it('should not highlight "Across All Docs" button when document selected', () => {
    render(<DocumentList {...defaultProps} selectedDocument="doc-1" />)
    
    const allDocsButton = screen.getByRole('button', { name: /Across All Docs/i })
    expect(allDocsButton).toHaveClass('btn-outline-secondary')
  })

  it('should call onSelectDocument with null when "Across All Docs" clicked', async () => {
    const user = userEvent.setup()
    const mockOnSelect = vi.fn()
    
    render(<DocumentList {...defaultProps} onSelectDocument={mockOnSelect} />)
    
    const allDocsButton = screen.getByRole('button', { name: /Across All Docs/i })
    await user.click(allDocsButton)
    
    expect(mockOnSelect).toHaveBeenCalledWith(null)
  })

  it('should render all document chips', () => {
    render(<DocumentList {...defaultProps} />)
    
    expect(screen.getByText('document1.pdf')).toBeInTheDocument()
    expect(screen.getByText('document2.md')).toBeInTheDocument()
  })

  it('should call getFileIcon for each document', () => {
    render(<DocumentList {...defaultProps} />)
    
    expect(mockGetFileIcon).toHaveBeenCalledWith('document1.pdf')
    expect(mockGetFileIcon).toHaveBeenCalledWith('document2.md')
  })

  it('should render file icons for documents', () => {
    const { container } = render(<DocumentList {...defaultProps} />)
    
    expect(container.querySelector('.bi-file-pdf')).toBeInTheDocument()
    expect(container.querySelector('.bi-file-text')).toBeInTheDocument()
  })

  it('should call onSelectDocument when document chip clicked', async () => {
    const user = userEvent.setup()
    const mockOnSelect = vi.fn()
    
    render(<DocumentList {...defaultProps} onSelectDocument={mockOnSelect} />)
    
    const docButton = screen.getByText('document1.pdf').closest('button')
    if (docButton) await user.click(docButton)
    
    expect(mockOnSelect).toHaveBeenCalledWith('doc-1')
  })

  it('should highlight selected document chip', () => {
    const { container } = render(<DocumentList {...defaultProps} selectedDocument="doc-1" />)
    
    const selectedChip = container.querySelector('.document-chip.selected')
    expect(selectedChip).toBeInTheDocument()
  })

  it('should apply selected styling to selected document', () => {
    const { container } = render(<DocumentList {...defaultProps} selectedDocument="doc-1" />)
    
    const chips = container.querySelectorAll('.document-chip')
    const selectedChip = Array.from(chips).find(chip => chip.textContent?.includes('document1.pdf'))
    
    expect(selectedChip).toHaveStyle({ border: '0.125rem solid #0d6efd' })
  })

  it('should render delete button for each document', () => {
    const { container } = render(<DocumentList {...defaultProps} />)
    
    const deleteButtons = container.querySelectorAll('.bi-x-circle')
    expect(deleteButtons).toHaveLength(2)
  })

  it('should call onDeleteDocument when delete button clicked', async () => {
    const user = userEvent.setup()
    const mockOnDelete = vi.fn()
    
    render(<DocumentList {...defaultProps} onDeleteDocument={mockOnDelete} />)
    
    const deleteButtons = screen.getAllByTitle('Delete document')
    await user.click(deleteButtons[0])
    
    expect(mockOnDelete).toHaveBeenCalledWith(mockDocuments[0])
  })

  it('should truncate long filenames', () => {
    const longFilename = 'very-long-filename-that-should-be-truncated.pdf'
    const docsWithLongName: Document[] = [
      {
        id: 'doc-long',
        filename: longFilename,
        uploadedAt: '2024-01-20T10:00:00Z',
      },
    ]
    
    const { container } = render(<DocumentList {...defaultProps} documents={docsWithLongName} />)
    
    const truncatedElement = container.querySelector('.text-truncate')
    expect(truncatedElement).toBeInTheDocument()
    expect(truncatedElement).toHaveAttribute('title', longFilename)
  })

  it('should disable "Across All Docs" button when no documents', () => {
    render(<DocumentList {...defaultProps} documents={[]} isLoadingDocuments={false} />)
    
    // Should render nothing, so button shouldn't exist
    const allDocsButton = screen.queryByRole('button', { name: /Across All Docs/i })
    expect(allDocsButton).not.toBeInTheDocument()
  })

  it('should render "Ask about:" label', () => {
    render(<DocumentList {...defaultProps} />)
    
    expect(screen.getByText('Ask about:')).toBeInTheDocument()
  })

  it('should handle single document', () => {
    render(<DocumentList {...defaultProps} documents={[mockDocuments[0]]} />)
    
    expect(screen.getByText('document1.pdf')).toBeInTheDocument()
    expect(screen.queryByText('document2.md')).not.toBeInTheDocument()
  })

  it('should apply correct button variant to selected document', () => {
    render(<DocumentList {...defaultProps} selectedDocument="doc-1" />)
    
    const selectedButton = screen.getByText('document1.pdf').closest('button')
    expect(selectedButton).toHaveClass('btn-primary')
  })

  it('should apply correct button variant to unselected document', () => {
    render(<DocumentList {...defaultProps} selectedDocument="doc-1" />)
    
    const unselectedButton = screen.getByText('document2.md').closest('button')
    expect(unselectedButton).toHaveClass('btn-outline-secondary')
  })
})
