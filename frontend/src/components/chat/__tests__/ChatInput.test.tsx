import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChatInput from '@/components/chat/ChatInput'

describe('ChatInput', () => {
  const defaultProps = {
    currentQuestion: '',
    setCurrentQuestion: vi.fn(),
    onSubmit: vi.fn(),
    isLoading: false,
    isStreaming: false,
    streamingEnabled: true,
    setStreamingEnabled: vi.fn(),
    documentsCount: 5,
    selectedDocument: null,
    selectedDocumentName: null,
    onKeyPress: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render textarea with placeholder', () => {
    render(<ChatInput {...defaultProps} />)
    
    const textarea = screen.getByPlaceholderText(/Ask a question across all your documents/i)
    expect(textarea).toBeInTheDocument()
  })

  it('should render streaming toggle', () => {
    render(<ChatInput {...defaultProps} />)
    
    const toggle = screen.getByLabelText('Streaming')
    expect(toggle).toBeInTheDocument()
    expect(toggle).toBeChecked()
  })

  it('should call setStreamingEnabled when toggle is clicked', async () => {
    const user = userEvent.setup()
    const mockSetStreaming = vi.fn()
    
    render(<ChatInput {...defaultProps} setStreamingEnabled={mockSetStreaming} />)
    
    const toggle = screen.getByLabelText('Streaming')
    await user.click(toggle)
    
    expect(mockSetStreaming).toHaveBeenCalledWith(false)
  })

  it('should render LangGraph badge', () => {
    render(<ChatInput {...defaultProps} />)
    
    expect(screen.getByText(/LangGraph Agent/i)).toBeInTheDocument()
  })

  it('should display correct placeholder when no documents', () => {
    render(<ChatInput {...defaultProps} documentsCount={0} />)
    
    const textarea = screen.getByPlaceholderText(/Please upload documents first/i)
    expect(textarea).toBeInTheDocument()
  })

  it('should display correct placeholder with selected document', () => {
    render(
      <ChatInput
        {...defaultProps}
        selectedDocument="doc-123"
        selectedDocumentName="test.pdf"
      />
    )
    
    const textarea = screen.getByPlaceholderText(/Ask a question about test.pdf/i)
    expect(textarea).toBeInTheDocument()
  })

  it('should disable textarea when no documents', () => {
    render(<ChatInput {...defaultProps} documentsCount={0} />)
    
    const textarea = screen.getByRole('textbox')
    expect(textarea).toBeDisabled()
  })

  it('should disable textarea when loading', () => {
    render(<ChatInput {...defaultProps} isLoading={true} />)
    
    const textarea = screen.getByRole('textbox')
    expect(textarea).toBeDisabled()
  })

  it('should call setCurrentQuestion when typing', async () => {
    const user = userEvent.setup()
    const mockSetQuestion = vi.fn()
    
    render(<ChatInput {...defaultProps} setCurrentQuestion={mockSetQuestion} />)
    
    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'Test question')
    
    expect(mockSetQuestion).toHaveBeenCalled()
  })

  it('should call onSubmit when form is submitted', async () => {
    const user = userEvent.setup()
    const mockOnSubmit = vi.fn((e) => e.preventDefault())
    
    render(<ChatInput {...defaultProps} onSubmit={mockOnSubmit} />)
    
    const form = screen.getByRole('textbox').closest('form')
    if (form) {
      await user.click(form)
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    }
    
    expect(mockOnSubmit).toHaveBeenCalled()
  })

  it('should display help text about searching all documents', () => {
    render(<ChatInput {...defaultProps} />)
    
    expect(screen.getByText(/searching across all your uploaded documents/i)).toBeInTheDocument()
  })

  it('should display help text about selected document', () => {
    render(
      <ChatInput
        {...defaultProps}
        selectedDocument="doc-123"
        selectedDocumentName="test.pdf"
      />
    )
    
    expect(screen.getByText(/based on the selected document/i)).toBeInTheDocument()
  })

  it('should mention streaming in help text when enabled', () => {
    render(<ChatInput {...defaultProps} streamingEnabled={true} />)
    
    expect(screen.getByText(/with streaming/i)).toBeInTheDocument()
  })

  it('should not mention streaming in help text when disabled', () => {
    render(<ChatInput {...defaultProps} streamingEnabled={false} />)
    
    expect(screen.queryByText(/with streaming/i)).not.toBeInTheDocument()
  })

  it('should show send button', () => {
    render(<ChatInput {...defaultProps} />)
    
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeInTheDocument()
  })

  it('should disable send button when no documents', () => {
    render(<ChatInput {...defaultProps} documentsCount={0} />)
    
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeDisabled()
  })

  it('should disable send button when loading', () => {
    render(<ChatInput {...defaultProps} isLoading={true} />)
    
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeDisabled()
  })

  it('should disable send button when question is empty', () => {
    render(<ChatInput {...defaultProps} currentQuestion="" />)
    
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeDisabled()
  })

  it('should enable send button when question is provided', () => {
    render(<ChatInput {...defaultProps} currentQuestion="Test question" />)
    
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).not.toBeDisabled()
  })

  it('should show spinner in send button when streaming', () => {
    const { container } = render(<ChatInput {...defaultProps} isStreaming={true} />)
    
    const spinner = container.querySelector('.spinner-border')
    expect(spinner).toBeInTheDocument()
  })

  it('should call onKeyPress when key is pressed', async () => {
    const user = userEvent.setup()
    const mockOnKeyPress = vi.fn()
    
    render(<ChatInput {...defaultProps} onKeyPress={mockOnKeyPress} />)
    
    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '{Enter}')
    
    expect(mockOnKeyPress).toHaveBeenCalled()
  })

  it('should have proper textarea styling', () => {
    const { container } = render(<ChatInput {...defaultProps} />)
    
    const textarea = container.querySelector('textarea')
    expect(textarea).toHaveStyle({ resize: 'none' })
  })
})
