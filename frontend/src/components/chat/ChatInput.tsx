import type { FC } from 'react'
import { useRef, useEffect } from 'react'
import { Form, Button, Badge, Spinner } from 'react-bootstrap'

interface ChatInputProps {
  currentQuestion: string
  setCurrentQuestion: (value: string) => void
  onSubmit: (e: React.FormEvent) => void
  isLoading: boolean
  isStreaming: boolean
  streamingEnabled: boolean
  setStreamingEnabled: (value: boolean) => void
  documentsCount: number
  selectedDocument: string | null
  selectedDocumentName: string | null
  onKeyPress: (e: React.KeyboardEvent) => void
}

const ChatInput: FC<ChatInputProps> = ({
  currentQuestion,
  setCurrentQuestion,
  onSubmit,
  isLoading,
  isStreaming,
  streamingEnabled,
  setStreamingEnabled,
  documentsCount,
  selectedDocument,
  selectedDocumentName,
  onKeyPress,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [currentQuestion])

  const getPlaceholder = () => {
    if (selectedDocument && selectedDocumentName) {
      return `Ask a question about ${selectedDocumentName}...`
    }
    if (selectedDocument) {
      return 'Ask a question about the selected document...'
    }
    if (documentsCount === 0) {
      return 'Please upload documents first to start asking questions...'
    }
    return 'Ask a question across all your documents...'
  }

  const getHelpText = () => {
    if (documentsCount === 0) {
      return 'Please upload documents first to start asking questions'
    }
    if (selectedDocument) {
      return `Questions will be answered based on the selected document${streamingEnabled ? ' with streaming' : ''}`
    }
    return `Questions will be answered by searching across all your uploaded documents${streamingEnabled ? ' with streaming' : ''}`
  }

  return (
    <div className="border-top pt-2 pt-md-3 chat-input-container flex-shrink-0">
      <Form onSubmit={onSubmit}>
        {/* LangGraph Agent and Controls */}
        <div className="mb-2 d-flex flex-wrap align-items-center gap-2">
          <div className="d-flex align-items-center">
            <Form.Check
              type="switch"
              id="streaming-toggle"
              label="Streaming"
              checked={streamingEnabled}
              onChange={(e) => setStreamingEnabled(e.target.checked)}
              className="small"
            />
          </div>

          <Badge bg="info" className="small">
            LangGraph Agent - Multi-step reasoning & citations
          </Badge>
        </div>

        <div className="position-relative">
          <Form.Control
            as="textarea"
            ref={textareaRef}
            value={currentQuestion}
            onChange={(e) => setCurrentQuestion(e.target.value)}
            onKeyDown={onKeyPress}
            placeholder={getPlaceholder()}
            disabled={isLoading || documentsCount === 0}
            style={{
              minHeight: 'clamp(2.5rem, 2.75rem, 3rem)',
              maxHeight: 'clamp(6rem, 8rem, 10rem)',
              resize: 'none',
              overflow: 'hidden',
              paddingRight: 'clamp(3rem, 3.5rem, 4rem)',
            }}
            className="form-control"
          />
          <Button
            type="submit"
            variant="primary"
            disabled={
              !currentQuestion.trim() ||
              isLoading ||
              isStreaming ||
              documentsCount === 0
            }
            className="position-absolute d-flex align-items-center justify-content-center p-0 border-0"
            style={{
              right: '0.75rem',
              bottom: '0.5rem',
              width: 'clamp(2rem, 2.25rem, 2.5rem)',
              height: 'clamp(2rem, 2.25rem, 2.5rem)',
              borderRadius: '50%',
              transition: 'all 0.2s ease',
            }}
            title="Send message (Enter)"
          >
            {isLoading || isStreaming ? (
              <Spinner
                animation="border"
                size="sm"
                style={{ width: '1rem', height: '1rem' }}
              />
            ) : (
              <i
                className="bi bi-send"
                style={{
                  fontSize: 'clamp(0.875rem, 1rem, 1.125rem)',
                  fontWeight: 'bold',
                }}
              ></i>
            )}
          </Button>
        </div>
        <small className="text-muted">
          <i className="bi bi-info-circle me-1"></i>
          {getHelpText()}
        </small>
      </Form>
    </div>
  )
}

export default ChatInput
