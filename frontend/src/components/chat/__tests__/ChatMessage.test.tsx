import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChatMessage from '@/components/chat/ChatMessage'

describe('ChatMessage', () => {
  const mockGetFileIcon = vi.fn((filename: string) => {
    if (filename.endsWith('.pdf')) return 'bi-file-pdf'
    if (filename.endsWith('.md')) return 'bi-file-text'
    return 'bi-file-earmark'
  })

  const defaultProps = {
    type: 'user' as const,
    content: 'Test message content',
    timestamp: new Date('2024-01-20T10:30:00'),
    getFileIcon: mockGetFileIcon,
  }

  beforeEach(() => {
    mockGetFileIcon.mockClear()
  })

  it('should render user message with correct styling', () => {
    render(<ChatMessage {...defaultProps} />)
    
    expect(screen.getByText('Test message content')).toBeInTheDocument()
  })

  it('should render assistant message with robot icon', () => {
    const { container } = render(<ChatMessage {...defaultProps} type="assistant" />)
    
    const robotIcon = container.querySelector('.bi-robot')
    expect(robotIcon).toBeInTheDocument()
  })

  it('should render user message with person icon', () => {
    const { container } = render(<ChatMessage {...defaultProps} type="user" />)
    
    const personIcon = container.querySelector('.bi-person-fill')
    expect(personIcon).toBeInTheDocument()
  })

  it('should format timestamp correctly', () => {
    render(<ChatMessage {...defaultProps} />)
    
    // Timestamp should be formatted as HH:MM
    const timestamp = screen.getByText(/10:30/)
    expect(timestamp).toBeInTheDocument()
  })

  it('should display document badge when document info provided', () => {
    render(
      <ChatMessage
        {...defaultProps}
        documentId="doc-123"
        documentName="test.pdf"
      />
    )
    
    expect(screen.getByText('test.pdf')).toBeInTheDocument()
    expect(mockGetFileIcon).toHaveBeenCalledWith('test.pdf')
  })

  it('should call getFileIcon with correct filename', () => {
    const { container } = render(
      <ChatMessage
        {...defaultProps}
        documentId="doc-123"
        documentName="document.md"
      />
    )
    
    expect(mockGetFileIcon).toHaveBeenCalledWith('document.md')
    const icon = container.querySelector('.bi-file-text')
    expect(icon).toBeInTheDocument()
  })

  it('should not display document badge when no document info', () => {
    render(<ChatMessage {...defaultProps} />)
    
    const badge = screen.queryByRole('status')
    expect(badge).not.toBeInTheDocument()
  })

  it('should apply correct alignment for user messages', () => {
    const { container } = render(<ChatMessage {...defaultProps} type="user" />)
    
    const messageWrapper = container.querySelector('.justify-content-end')
    expect(messageWrapper).toBeInTheDocument()
  })

  it('should apply correct alignment for assistant messages', () => {
    const { container } = render(<ChatMessage {...defaultProps} type="assistant" />)
    
    const messageWrapper = container.querySelector('.justify-content-start')
    expect(messageWrapper).toBeInTheDocument()
  })

  it('should apply primary background for user messages', () => {
    const { container } = render(<ChatMessage {...defaultProps} type="user" />)
    
    const card = container.querySelector('.bg-primary')
    expect(card).toBeInTheDocument()
  })

  it('should apply light background for assistant messages', () => {
    const { container } = render(<ChatMessage {...defaultProps} type="assistant" />)
    
    const card = container.querySelector('.bg-light')
    expect(card).toBeInTheDocument()
  })

  it('should preserve whitespace and break words correctly', () => {
    const multilineContent = 'Line 1\nLine 2\nLine 3'
    const { container } = render(<ChatMessage {...defaultProps} content={multilineContent} />)
    
    const contentDiv = container.querySelector('[style*="white-space: pre-wrap"]')
    expect(contentDiv).toBeInTheDocument()
  })

  it('should handle long content without breaking layout', () => {
    const longContent = 'A'.repeat(500)
    render(<ChatMessage {...defaultProps} content={longContent} />)
    
    expect(screen.getByText(longContent)).toBeInTheDocument()
  })

  it('should render both document badge and timestamp', () => {
    render(
      <ChatMessage
        {...defaultProps}
        documentId="doc-123"
        documentName="test.pdf"
      />
    )
    
    expect(screen.getByText('test.pdf')).toBeInTheDocument()
    expect(screen.getByText(/10:30/)).toBeInTheDocument()
  })

  it('should display document badge with correct variant for user messages', () => {
    const { container } = render(
      <ChatMessage
        {...defaultProps}
        type="user"
        documentId="doc-123"
        documentName="test.pdf"
      />
    )
    
    const badge = container.querySelector('.badge')
    expect(badge).toHaveClass('bg-light', 'text-dark')
  })

  it('should display document badge with correct variant for assistant messages', () => {
    const { container } = render(
      <ChatMessage
        {...defaultProps}
        type="assistant"
        documentId="doc-123"
        documentName="test.pdf"
      />
    )
    
    const badge = container.querySelector('.badge')
    expect(badge).toHaveClass('bg-secondary', 'text-light')
  })

  it('should render message content in card body', () => {
    const { container } = render(<ChatMessage {...defaultProps} />)
    
    const cardBody = container.querySelector('.card-body')
    expect(cardBody).toBeInTheDocument()
    expect(cardBody).toHaveTextContent('Test message content')
  })

  it('should handle empty content gracefully', () => {
    render(<ChatMessage {...defaultProps} content="" />)
    
    const timestamp = screen.getByText(/10:30/)
    expect(timestamp).toBeInTheDocument()
  })

  describe('Source Attribution', () => {
    const sourcesProps = {
      ...defaultProps,
      type: 'assistant' as const,
      sources: [
        {
          source_type: 'llm_knowledge',
          description: 'Based on general training data',
          confidence: 'high',
          url: null,
        },
        {
          source_type: 'document',
          description: 'From uploaded document',
          confidence: 'medium',
          url: 'https://example.com/doc',
        },
      ],
    }

    it('should render sources section for assistant messages with sources', () => {
      render(<ChatMessage {...sourcesProps} />)
      
      expect(screen.getByText(/Sources \(2\)/)).toBeInTheDocument()
    })

    it('should display source type badges', () => {
      render(<ChatMessage {...sourcesProps} />)
      
      expect(screen.getByText(/llm knowledge/i)).toBeInTheDocument()
      expect(screen.getByText(/document/i)).toBeInTheDocument()
    })

    it('should not render sources section for user messages', () => {
      render(
        <ChatMessage
          {...sourcesProps}
          type="user"
        />
      )
      
      expect(screen.queryByText(/Sources/)).not.toBeInTheDocument()
    })

    it('should not render sources section when no sources provided', () => {
      render(<ChatMessage {...defaultProps} type="assistant" />)
      
      expect(screen.queryByText(/Sources/)).not.toBeInTheDocument()
    })

    it('should not render sources section when sources array is empty', () => {
      render(<ChatMessage {...defaultProps} type="assistant" sources={[]} />)
      
      expect(screen.queryByText(/Sources/)).not.toBeInTheDocument()
    })

    it('should render insufficient info warning when hasSufficientInfo is false', () => {
      render(
        <ChatMessage
          {...defaultProps}
          type="assistant"
          hasSufficientInfo={false}
        />
      )
      
      expect(screen.getByText(/Limited information available/)).toBeInTheDocument()
    })

    it('should not render insufficient info warning when hasSufficientInfo is true', () => {
      render(
        <ChatMessage
          {...defaultProps}
          type="assistant"
          hasSufficientInfo={true}
        />
      )
      
      expect(screen.queryByText(/Limited information available/)).not.toBeInTheDocument()
    })

    it('should apply correct badge color for high confidence', () => {
      const { container } = render(
        <ChatMessage
          {...defaultProps}
          type="assistant"
          sources={[
            {
              source_type: 'llm_knowledge',
              description: 'Test',
              confidence: 'high',
            },
          ]}
        />
      )
      
      const badge = container.querySelector('.badge.bg-success')
      expect(badge).toBeInTheDocument()
    })

    it('should apply correct badge color for medium confidence', () => {
      const { container } = render(
        <ChatMessage
          {...defaultProps}
          type="assistant"
          sources={[
            {
              source_type: 'document',
              description: 'Test',
              confidence: 'medium',
            },
          ]}
        />
      )
      
      const badge = container.querySelector('.badge.bg-warning')
      expect(badge).toBeInTheDocument()
    })

    it('should apply correct badge color for low confidence', () => {
      const { container } = render(
        <ChatMessage
          {...defaultProps}
          type="assistant"
          sources={[
            {
              source_type: 'web',
              description: 'Test',
              confidence: 'low',
            },
          ]}
        />
      )
      
      const badge = container.querySelector('.badge.bg-danger')
      expect(badge).toBeInTheDocument()
    })
  })
})
