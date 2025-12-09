import type { FC } from 'react'
import { useRef, useEffect, useState } from 'react'
import { Form, Button, Badge, Spinner, OverlayTrigger, Tooltip, Collapse } from 'react-bootstrap'

interface ChatInputProps {
  currentQuestion: string
  setCurrentQuestion: (value: string) => void
  onSubmit: (e: React.FormEvent) => void
  isLoading: boolean
  isStreaming: boolean
  streamingEnabled: boolean
  setStreamingEnabled: (value: boolean) => void
  deepResearchEnabled: boolean
  setDeepResearchEnabled: (value: boolean) => void
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
  deepResearchEnabled,
  setDeepResearchEnabled,
  documentsCount,
  selectedDocument,
  selectedDocumentName,
  onKeyPress,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [showDeepResearchInfo, setShowDeepResearchInfo] = useState(false)

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
      return 'Please ask general questions...'
    }
    return 'Ask a question across all your documents...'
  }

  const getHelpText = () => {
    if (deepResearchEnabled) {
      return 'Deep Research mode: AI will perform multi-step research with human approval checkpoints'
    }
    if (documentsCount === 0) {
      return 'Please upload documents first to start asking questions'
    }
    if (selectedDocument) {
      return `Questions will be answered based on the selected document${streamingEnabled ? ' with streaming' : ''}`
    }
    return `Questions will be answered by searching across all your uploaded documents${streamingEnabled ? ' with streaming' : ''}`
  }

  const deepResearchTooltip = (
    <Tooltip id="deep-research-tooltip">
      Click the info icon for more details about Deep Research
    </Tooltip>
  )

  return (
    <div className="border-top pt-2 pt-md-3 chat-input-container flex-shrink-0">
      <Form onSubmit={onSubmit}>
        {/* Agent Controls */}
        <div className="mb-2 d-flex flex-wrap align-items-center gap-2">
          <div className="d-flex align-items-center">
            <Form.Check
              type="switch"
              id="streaming-toggle"
              label="Streaming"
              checked={streamingEnabled}
              onChange={(e) => setStreamingEnabled(e.target.checked)}
              className="small"
              disabled={deepResearchEnabled}
            />
          </div>

          <div className="d-flex align-items-center">
            <Form.Check
              type="switch"
              id="deep-research-toggle"
              checked={deepResearchEnabled}
              onChange={(e) => setDeepResearchEnabled(e.target.checked)}
              className="small me-1"
            />
            <label htmlFor="deep-research-toggle" className="small mb-0 me-1" style={{ cursor: 'pointer' }}>
              Deep Research
            </label>
            <OverlayTrigger placement="top" overlay={deepResearchTooltip}>
              <Button
                variant="link"
                size="sm"
                className="p-0 text-info"
                onClick={() => setShowDeepResearchInfo(!showDeepResearchInfo)}
                style={{ lineHeight: 1 }}
              >
                <i className="bi bi-info-circle"></i>
              </Button>
            </OverlayTrigger>
          </div>

          {deepResearchEnabled ? (
            <Badge bg="warning" text="dark" className="small">
              <i className="bi bi-search me-1"></i>
              Deep Research Mode
            </Badge>
          ) : (
            <Badge bg="info" className="small">
              AI Assistant - Powered by Microsoft Agent Framework
            </Badge>
          )}
        </div>

        {/* Deep Research Info Panel */}
        <Collapse in={showDeepResearchInfo}>
          <div className="mb-2">
            <div className="alert alert-info py-2 mb-2" style={{ fontSize: '0.85rem' }}>
              <h6 className="alert-heading mb-1">
                <i className="bi bi-lightbulb me-1"></i>
                What is Deep Research?
              </h6>
              <p className="mb-2">
                Deep Research is an advanced AI-powered research workflow that performs <strong>multi-step, 
                comprehensive analysis</strong> of complex topics. Unlike regular chat, it:
              </p>
              <ul className="mb-2 ps-3">
                <li><strong>Searches the web</strong> - Fetches <em>current data</em> from the internet for up-to-date information</li>
                <li><strong>Creates a research plan</strong> - Breaks down your topic into subtopics and research questions</li>
                <li><strong>Gathers findings</strong> - Systematically researches each aspect with confidence scoring</li>
                <li><strong>Synthesizes a report</strong> - Produces a comprehensive final report with citations & source URLs</li>
              </ul>
              <p className="mb-0 text-muted">
                <i className="bi bi-globe me-1"></i>
                <em>Deep Research goes outbound to the web to fetch current data, ensuring your results are up-to-date.</em>
              </p>
            </div>
          </div>
        </Collapse>

        <div className="position-relative">
          <Form.Control
            as="textarea"
            ref={textareaRef}
            value={currentQuestion}
            onChange={(e) => setCurrentQuestion(e.target.value)}
            onKeyDown={onKeyPress}
            placeholder={getPlaceholder()}
            disabled={isLoading}
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
              isStreaming
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
