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
  Modal,
  Badge,
  ProgressBar,
} from 'react-bootstrap'
import apiService from '@/service/api-service'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  documentId?: string
}

interface Document {
  id: string
  filename: string
  uploadedAt: string
  totalPages?: number
}

const ChatInterface: FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const loadDocuments = async () => {
    try {
      const response = await apiService
        .getAxiosInstance()
        .get('/api/v1/documents')
      setDocuments(response.data)
    } catch (err: any) {
      console.error('Error loading documents:', err)
    }
  }
  // Load documents on component mount
  useEffect(() => {
    loadDocuments()
  }, [])

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

  const handleFileUpload = async (file: File) => {
    if (!file) return

    if (file.type !== 'application/pdf') {
      setError('Only PDF files are supported')
      return
    }

    if (file.size > 100 * 1024 * 1024) {
      setError('File size must be less than 100MB')
      return
    }

    setIsUploading(true)
    setUploadProgress(0)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await apiService
        .getAxiosInstance()
        .post('/api/v1/documents/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const progress = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total,
              )
              setUploadProgress(progress)
            }
          },
        })

      // Add success message
      const successMessage: ChatMessage = {
        id: Date.now().toString(),
        type: 'assistant',
        content: `Document "${file.name}" uploaded successfully! You can now ask questions about this document.`,
        timestamp: new Date(),
        documentId: response.data.id,
      }
      setMessages((prev) => [...prev, successMessage])

      // Reload documents list
      await loadDocuments()

      // Select the newly uploaded document
      setSelectedDocument(response.data.id)
      setShowUploadModal(false)
    } catch (err: any) {
      console.error('Upload error:', err)
      setError(err.response?.data?.message || 'Failed to upload document')
    } finally {
      setIsUploading(false)
      setUploadProgress(0)
    }
  }

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
      documentId: selectedDocument || undefined,
    }

    // Add user message to chat
    setMessages((prev) => [...prev, userMessage])
    setCurrentQuestion('')
    setIsLoading(true)
    setError(null)

    try {
      let response

      if (selectedDocument) {
        // Ask question about specific document
        response = await apiService
          .getAxiosInstance()
          .post('/api/v1/documents/ask', {
            question: questionText,
            documentId: selectedDocument,
          })
      } else {
        // General chat
        response = await apiService
          .getAxiosInstance()
          .post('/api/v1/chat/ask', {
            question: questionText,
          })
      }

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.data.answer || 'No response received',
        timestamp: new Date(),
        documentId: selectedDocument || undefined,
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

  const selectedDocumentName = selectedDocument
    ? documents.find((doc) => doc.id === selectedDocument)?.filename ||
      'Unknown Document'
    : null

  return (
    <Container fluid className="h-100 d-flex flex-column">
      <Row className="flex-grow-1 overflow-hidden">
        <Col xs={12} lg={8} xl={6} className="mx-auto d-flex flex-column h-100">
          {/* Chat Header */}
          <div className="py-3 border-bottom">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <h4 className="mb-0">
                <i className="bi bi-chat-dots me-2"></i>
                AI Document Assistant
              </h4>
              <Button
                variant="outline-primary"
                size="sm"
                onClick={() => setShowUploadModal(true)}
              >
                <i className="bi bi-cloud-upload me-1"></i>
                Upload PDF
              </Button>
            </div>

            {/* Document Selection */}
            <div className="d-flex flex-wrap gap-2 align-items-center">
              <small className="text-muted">Ask about:</small>
              <Button
                variant={!selectedDocument ? 'primary' : 'outline-secondary'}
                size="sm"
                onClick={() => setSelectedDocument(null)}
              >
                General Questions
              </Button>
              {documents.map((doc) => (
                <Button
                  key={doc.id}
                  variant={
                    selectedDocument === doc.id
                      ? 'primary'
                      : 'outline-secondary'
                  }
                  size="sm"
                  onClick={() => setSelectedDocument(doc.id)}
                  className="text-truncate"
                  style={{ maxWidth: '200px' }}
                >
                  <i className="bi bi-file-pdf me-1"></i>
                  {doc.filename}
                </Button>
              ))}
            </div>

            {selectedDocumentName && (
              <div className="mt-2">
                <Badge bg="info">
                  <i className="bi bi-file-pdf me-1"></i>
                  Currently asking about: {selectedDocumentName}
                </Badge>
              </div>
            )}
          </div>

          {/* Messages Container */}
          <div
            className="flex-grow-1 overflow-auto py-3"
            style={{ minHeight: '400px' }}
          >
            {messages.length === 0 ? (
              <div className="text-center text-muted py-5">
                <i className="bi bi-chat-quote display-4 mb-3"></i>
                <h5>Welcome to AI Document Assistant</h5>
                <p>
                  Upload a PDF document and ask questions about it, or ask
                  general questions.
                </p>
                <Button
                  variant="primary"
                  onClick={() => setShowUploadModal(true)}
                  className="mt-2"
                >
                  <i className="bi bi-cloud-upload me-2"></i>
                  Upload Your First Document
                </Button>
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
                              {message.documentId && (
                                <div className="mt-1">
                                  <Badge
                                    bg={
                                      message.type === 'user'
                                        ? 'light'
                                        : 'secondary'
                                    }
                                    text={
                                      message.type === 'user' ? 'dark' : 'light'
                                    }
                                  >
                                    <i className="bi bi-file-pdf me-1"></i>
                                    {documents.find(
                                      (doc) => doc.id === message.documentId,
                                    )?.filename || 'Document'}
                                  </Badge>
                                </div>
                              )}
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
                            <span className="text-muted">
                              {selectedDocument
                                ? 'Analyzing document...'
                                : 'Thinking...'}
                            </span>
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
                    placeholder={
                      selectedDocument
                        ? `Ask a question about ${selectedDocumentName}...`
                        : 'Ask a general question or upload a document first...'
                    }
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
                {selectedDocument
                  ? `Questions will be answered based on the selected document`
                  : 'Upload a PDF to ask questions about it, or ask general questions'}
              </small>
            </Form>
          </div>
        </Col>
      </Row>

      {/* Upload Modal */}
      <Modal
        show={showUploadModal}
        onHide={() => setShowUploadModal(false)}
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>
            <i className="bi bi-cloud-upload me-2"></i>
            Upload PDF Document
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="text-center py-4">
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleFileUpload(file)
              }}
              accept=".pdf"
              style={{ display: 'none' }}
            />

            {!isUploading ? (
              <div>
                <i className="bi bi-file-pdf display-4 text-primary mb-3"></i>
                <h5>Select a PDF file to upload</h5>
                <p className="text-muted">Maximum file size: 100MB</p>
                <Button
                  variant="primary"
                  onClick={() => fileInputRef.current?.click()}
                  size="lg"
                >
                  <i className="bi bi-folder-open me-2"></i>
                  Choose File
                </Button>
              </div>
            ) : (
              <div>
                <Spinner animation="border" className="mb-3" />
                <h5>Uploading and processing document...</h5>
                <ProgressBar
                  now={uploadProgress}
                  label={`${uploadProgress}%`}
                  className="mt-3"
                />
              </div>
            )}
          </div>
        </Modal.Body>
      </Modal>
    </Container>
  )
}

export default ChatInterface
