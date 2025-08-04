import apiService from '@/service/api-service'
import type { FC } from 'react'
import { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Container,
  Form,
  Modal,
  ProgressBar,
  Row,
  Spinner,
} from 'react-bootstrap'

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
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(
    null,
  )
  const [isDeleting, setIsDeleting] = useState(false)
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true)

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const previousMessageCount = useRef(0)
  const shouldAutoScrollOnNewMessage = useRef(true)

  // Helper function to get appropriate icon for file type
  const getFileIcon = (filename: string): string => {
    const extension = filename.toLowerCase().split('.').pop() || ''
    switch (extension) {
      case 'pdf':
        return 'bi-file-pdf'
      case 'md':
      case 'markdown':
        return 'bi-file-text'
      case 'html':
      case 'htm':
        return 'bi-file-code'
      default:
        return 'bi-file-text'
    }
  }
  const loadDocuments = async () => {
    setIsLoadingDocuments(true)
    try {
      const response = await apiService
        .getAxiosInstance()
        .get('/api/v1/documents')
      setDocuments(response.data)
    } catch (err: any) {
      console.error('Error loading documents:', err)
    } finally {
      setIsLoadingDocuments(false)
    }
  }
  // Load documents on component mount
  useEffect(() => {
    loadDocuments()
  }, [])

  // Auto-scroll to bottom when new messages are added - SMART VERSION
  useEffect(() => {
    // Check if we have new messages (increased count)
    if (messages.length > previousMessageCount.current) {
      // Only auto-scroll if enabled and we're adding new messages
      if (shouldAutoScrollOnNewMessage.current) {
        const scrollToBottom = () => {
          if (messagesContainerRef.current) {
            // Scroll only the chat container, not the entire page
            messagesContainerRef.current.scrollTop =
              messagesContainerRef.current.scrollHeight
          }
        }

        // Small delay to ensure DOM has updated
        setTimeout(scrollToBottom, 100)
      }

      // Update the count
      previousMessageCount.current = messages.length
    }
  }, [messages])

  // Handle scroll detection within chat container
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement
    const { scrollTop, scrollHeight, clientHeight } = target

    // Check if user is near the bottom of the chat container (within 3.125rem)
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 50
    // Check if user is near the top of the chat container (within 3.125rem)

    // Enable auto-scroll when near bottom, disable when scrolled up
    shouldAutoScrollOnNewMessage.current = isNearBottom
  }

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [currentQuestion])

  const handleFileUpload = async (file: File) => {
    if (!file) return

    const allowedTypes = [
      'application/pdf',
      'text/markdown',
      'text/x-markdown',
      'text/html',
      'text/plain',
    ]
    const allowedExtensions = ['.pdf', '.md', '.markdown', '.html', '.htm']
    const fileExtension = '.' + file.name.toLowerCase().split('.').pop()

    const isValidType =
      allowedTypes.includes(file.type) ||
      allowedExtensions.includes(fileExtension)

    if (!isValidType) {
      setError(
        'Only PDF, Markdown (.md), and HTML (.html, .htm) files are supported',
      )
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

  const handleDeleteDocument = async (document: Document) => {
    setDocumentToDelete(document)
    setShowDeleteConfirm(true)
  }

  const confirmDeleteDocument = async () => {
    if (!documentToDelete) return

    setIsDeleting(true)
    setError(null)

    try {
      await apiService
        .getAxiosInstance()
        .delete(`/api/v1/documents/${documentToDelete.id}`)

      // Remove from documents list
      setDocuments((prev) =>
        prev.filter((doc) => doc.id !== documentToDelete.id),
      )

      // Clear selection if deleted document was selected
      if (selectedDocument === documentToDelete.id) {
        setSelectedDocument(null)
      }

      // Add success message
      const successMessage: ChatMessage = {
        id: Date.now().toString(),
        type: 'assistant',
        content: `Document "${documentToDelete.filename}" has been deleted successfully.`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, successMessage])

      setShowDeleteConfirm(false)
      setDocumentToDelete(null)
    } catch (err: any) {
      console.error('Delete error:', err)
      setError(err.response?.data?.message || 'Failed to delete document')
    } finally {
      setIsDeleting(false)
    }
  }

  const cancelDeleteDocument = () => {
    setShowDeleteConfirm(false)
    setDocumentToDelete(null)
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
    <Container fluid className="vh-100 d-flex flex-column p-0">
      <Row className="flex-grow-1 overflow-hidden g-0">
        <Col
          xs={12}
          sm={12}
          md={11}
          lg={10}
          xl={8}
          xxl={7}
          className="mx-auto d-flex flex-column h-100 position-relative px-2 px-md-3"
        >
          {/* Chat Header */}
          <div className="py-2 py-md-3 border-bottom flex-shrink-0">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <h4 className="mb-0">
                <i className="bi bi-chat-dots me-2"></i>
                AI Document Assistant
              </h4>
              <Button
                variant="primary"
                size="sm"
                onClick={() => setShowUploadModal(true)}
              >
                <i className="bi bi-cloud-upload me-1"></i>
                Upload Document
              </Button>
            </div>

            {/* Document Selection */}
            <div className="mb-2">
              <div className="d-flex flex-wrap gap-2 align-items-center mb-2">
                <small className="text-muted">Ask about:</small>
                <Button
                  variant={!selectedDocument ? 'primary' : 'outline-secondary'}
                  size="sm"
                  onClick={() => setSelectedDocument(null)}
                >
                  General Questions
                </Button>
              </div>

              {/* Uploaded Documents */}
              {isLoadingDocuments ? (
                <div className="d-flex align-items-center text-muted">
                  <Spinner animation="border" size="sm" className="me-2" />
                  <small>Loading documents...</small>
                </div>
              ) : documents.length > 0 ? (
                <div className="d-flex flex-wrap gap-2">
                  {documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="d-flex align-items-center border rounded p-1"
                      style={{
                        backgroundColor:
                          selectedDocument === doc.id
                            ? 'var(--bs-info-bg-subtle, #e3f2fd)'
                            : 'var(--bs-gray-100, #f8f9fa)',
                      }}
                    >
                      <Button
                        variant={
                          selectedDocument === doc.id
                            ? 'primary'
                            : 'outline-secondary'
                        }
                        size="sm"
                        onClick={() => setSelectedDocument(doc.id)}
                        className="text-truncate border-0 me-1"
                        style={{
                          maxWidth: 'clamp(8rem, 11.25rem, 15rem)',
                        }}
                      >
                        <i className={`${getFileIcon(doc.filename)} me-1`}></i>
                        {doc.filename}
                      </Button>
                      <Button
                        variant="outline-danger"
                        size="sm"
                        onClick={() => handleDeleteDocument(doc)}
                        className="border-0 p-1 d-flex align-items-center justify-content-center"
                        style={{ width: '1.75rem', height: '1.75rem' }}
                        title={`Remove ${doc.filename}`}
                      >
                        <i
                          className="bi bi-x"
                          style={{ fontSize: '1.1em' }}
                        ></i>
                      </Button>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>

            {selectedDocumentName && (
              <div className="mt-2">
                <Badge bg="info">
                  <i
                    className={`${getFileIcon(selectedDocumentName)} me-1`}
                  ></i>
                  Currently asking about: {selectedDocumentName}
                </Badge>
              </div>
            )}
          </div>

          {/* Messages Container - Made responsive with proper scrolling */}
          <div
            ref={messagesContainerRef}
            className="flex-grow-1 overflow-auto py-2 py-md-3 chat-messages"
            style={{
              minHeight: '0',
              height: '100%',
            }}
            onScroll={handleScroll}
          >
            {messages.length === 0 ? (
              <div className="text-center text-muted py-5">
                {isLoadingDocuments ? (
                  <>
                    <Spinner animation="border" className="mb-3" />
                    <h5>Loading documents...</h5>
                    <p>Please wait while we fetch your documents.</p>
                  </>
                ) : (
                  <>
                    <i className="bi bi-chat-quote display-4 mb-3"></i>
                    <h5>Welcome to AI Document Assistant</h5>
                    <p>
                      Upload a document (PDF, Markdown, or HTML) and ask
                      questions about it, or ask general questions.
                    </p>
                  </>
                )}
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
                    } mb-2 mb-md-3`}
                  >
                    <div
                      className={`position-relative ${
                        message.type === 'user'
                          ? 'ms-3 ms-md-5'
                          : 'me-3 me-md-5'
                      }`}
                      style={{ maxWidth: 'min(80%, 50rem)' }}
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
                                    <i
                                      className={`${getFileIcon(
                                        documents.find(
                                          (doc) =>
                                            doc.id === message.documentId,
                                        )?.filename || '',
                                      )} me-1`}
                                    ></i>
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
                  <div className="d-flex justify-content-start mb-2 mb-md-3">
                    <div
                      className="me-3 me-md-5"
                      style={{ maxWidth: 'min(80%, 50rem)' }}
                    >
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
          <div className="border-top pt-2 pt-md-3 chat-input-container flex-shrink-0">
            <Form onSubmit={handleSubmit} style={{ marginBottom: '5em' }}>
              <div className="position-relative">
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
                  disabled={!currentQuestion.trim() || isLoading}
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
                  {isLoading ? (
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
                {selectedDocument
                  ? `Questions will be answered based on the selected document`
                  : 'Upload a document (PDF, Markdown, HTML) to ask questions about it, or ask general questions'}
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
            Upload Document
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
              accept=".pdf,.md,.markdown,.html,.htm"
              style={{ display: 'none' }}
            />

            {!isUploading ? (
              <div>
                <i className="bi bi-files display-4 text-primary mb-3"></i>
                <h5>Select a document to upload</h5>
                <p className="text-muted">
                  Supported formats: PDF, Markdown (.md), HTML (.html, .htm)
                  <br />
                  Maximum file size: 100MB
                </p>
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

      {/* Delete Confirmation Modal */}
      <Modal show={showDeleteConfirm} onHide={cancelDeleteDocument} centered>
        <Modal.Header closeButton>
          <Modal.Title>
            <i className="bi bi-exclamation-triangle text-warning me-2"></i>
            Confirm Delete
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="text-center py-3">
            <i
              className={`${
                documentToDelete
                  ? getFileIcon(documentToDelete.filename)
                  : 'bi-file-text'
              } display-4 text-danger mb-3`}
            ></i>
            <h5>Delete Document</h5>
            <p className="text-muted">
              Are you sure you want to delete "{documentToDelete?.filename}"?
            </p>
            <p className="text-warning small">
              <i className="bi bi-exclamation-triangle me-1"></i>
              This action cannot be undone. The document and all associated data
              will be permanently removed.
            </p>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button
            variant="secondary"
            onClick={cancelDeleteDocument}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={confirmDeleteDocument}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                Deleting...
              </>
            ) : (
              <>
                <i className="bi bi-trash me-1"></i>
                Delete Document
              </>
            )}
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  )
}

export default ChatInterface
