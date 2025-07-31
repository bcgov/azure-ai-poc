import type { FC } from 'react'
import { useState, useRef, useEffect } from 'react'
import {
  Container,
  Row,
  Col,
  Form,
  Button,
  Card,
  Alert,
  Spinner,
} from 'react-bootstrap'
import apiService from '@/service/api-service'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const ChatInterface: FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [currentQuestion])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!currentQuestion.trim() || isLoading) {
      return
    }

    const questionText = currentQuestion.trim()
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: questionText,
      timestamp: new Date(),
    }

    // Add user message to chat
    setMessages((prev) => [...prev, userMessage])
    setCurrentQuestion('')
    setIsLoading(true)
    setError(null)

    try {
      // Make API call to backend
      const response = await apiService
        .getAxiosInstance()
        .post('/api/v1/chat/ask', {
          question: questionText,
        })

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.data.answer || 'No response received',
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (err: any) {
      console.error('Chat API error:', err)
      setError(
        err.response?.data?.message ||
          'Failed to get response. Please try again.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as any)
    }
  }

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <Container fluid className="h-100 d-flex flex-column">
      <Row className="flex-grow-1 overflow-hidden">
        <Col xs={12} lg={8} xl={6} className="mx-auto d-flex flex-column h-100">
          {/* Chat Header */}
          <div className="py-3 border-bottom">
            <h4 className="mb-0 text-center">
              <i className="bi bi-chat-dots me-2"></i>
              AI Assistant
            </h4>
            <p className="text-muted text-center mb-0 small">
              Ask me anything about your data or get help with your questions
            </p>
          </div>

          {/* Messages Container */}
          <div
            className="flex-grow-1 overflow-auto py-3"
            style={{ minHeight: '400px' }}
          >
            {messages.length === 0 ? (
              <div className="text-center text-muted py-5">
                <i className="bi bi-chat-quote display-4 mb-3"></i>
                <h5>Welcome to AI Assistant</h5>
                <p>Start a conversation by typing your question below</p>
              </div>
            ) : (
              <div className="space-y-3">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`d-flex ${
                      message.type === 'user'
                        ? 'justify-content-end'
                        : 'justify-content-start'
                    } mb-3`}
                  >
                    <div
                      className={`position-relative ${
                        message.type === 'user' ? 'ms-5' : 'me-5'
                      }`}
                      style={{ maxWidth: '80%' }}
                    >
                      <Card
                        className={`${
                          message.type === 'user'
                            ? 'bg-primary text-white'
                            : 'bg-light'
                        }`}
                      >
                        <Card.Body className="py-2 px-3">
                          <div className="d-flex align-items-start">
                            {message.type === 'assistant' && (
                              <i
                                className="bi bi-robot me-2 mt-1"
                                style={{ fontSize: '1.1em' }}
                              ></i>
                            )}
                            <div className="flex-grow-1">
                              <div
                                style={{
                                  whiteSpace: 'pre-wrap',
                                  wordBreak: 'break-word',
                                }}
                              >
                                {message.content}
                              </div>
                              <small
                                className={`d-block mt-1 ${
                                  message.type === 'user'
                                    ? 'text-white-50'
                                    : 'text-muted'
                                }`}
                              >
                                {formatTimestamp(message.timestamp)}
                              </small>
                            </div>
                            {message.type === 'user' && (
                              <i
                                className="bi bi-person-fill ms-2 mt-1"
                                style={{ fontSize: '1.1em' }}
                              ></i>
                            )}
                          </div>
                        </Card.Body>
                      </Card>
                    </div>
                  </div>
                ))}

                {/* Loading indicator */}
                {isLoading && (
                  <div className="d-flex justify-content-start mb-3">
                    <div className="me-5" style={{ maxWidth: '80%' }}>
                      <Card className="bg-light">
                        <Card.Body className="py-2 px-3">
                          <div className="d-flex align-items-center">
                            <i className="bi bi-robot me-2"></i>
                            <Spinner
                              animation="grow"
                              size="sm"
                              className="me-2"
                            />
                            <span className="text-muted">Thinking...</span>
                          </div>
                        </Card.Body>
                      </Card>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Error Alert */}
          {error && (
            <Alert
              variant="danger"
              className="mb-2"
              dismissible
              onClose={() => setError(null)}
            >
              <i className="bi bi-exclamation-triangle me-2"></i>
              {error}
            </Alert>
          )}

          {/* Input Form */}
          <div className="border-top pt-3">
            <Form onSubmit={handleSubmit}>
              <div className="d-flex align-items-end gap-2">
                <div className="flex-grow-1">
                  <Form.Control
                    as="textarea"
                    ref={textareaRef}
                    value={currentQuestion}
                    onChange={(e) => setCurrentQuestion(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Type your question here... (Press Enter to send, Shift+Enter for new line)"
                    disabled={isLoading}
                    style={{
                      minHeight: '44px',
                      maxHeight: '200px',
                      resize: 'none',
                      overflow: 'hidden',
                    }}
                    className="form-control"
                  />
                </div>
                <Button
                  type="submit"
                  variant="primary"
                  disabled={!currentQuestion.trim() || isLoading}
                  className="d-flex align-items-center px-3"
                  style={{ height: '44px' }}
                >
                  {isLoading ? (
                    <Spinner animation="border" size="sm" />
                  ) : (
                    <>
                      <i className="bi bi-send me-1"></i>
                      Send
                    </>
                  )}
                </Button>
              </div>
              <small className="text-muted">
                <i className="bi bi-info-circle me-1"></i>
                Your messages are secured with Keycloak authentication
              </small>
            </Form>
          </div>
        </Col>
      </Row>
    </Container>
  )
}

export default ChatInterface
