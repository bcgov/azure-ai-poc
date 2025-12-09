import apiService from '@/service/api-service'
import { chatAgentService, type ChatMessage as ChatServiceMessage } from '@/services/chatAgentService'
import { documentService, type DocumentItem } from '@/services/documentService'
import type { FC } from 'react'
import { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Collapse,
  Container,
  Form,
  Modal,
  OverlayTrigger,
  ProgressBar,
  Row,
  Spinner,
  Tooltip,
} from 'react-bootstrap'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  documentId?: string
}

// Use DocumentItem from documentService for consistency
type Document = DocumentItem

const ChatInterface: FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string>(`session_${Date.now()}`)
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingEnabled, setStreamingEnabled] = useState(true)
  const [deepResearchEnabled, setDeepResearchEnabled] = useState(false)
  const [deepResearchRunId, setDeepResearchRunId] = useState<string | null>(null)
  const [showDeepResearchInfo, setShowDeepResearchInfo] = useState(false)
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
  const [pendingDocumentSelection, setPendingDocumentSelection] = useState<
    string | null
  >(null)

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
      const result = await documentService.listDocuments()
      if (result.success && result.data) {
        setDocuments(result.data.documents)
        return result.data.documents
      }
      return []
    } catch (err: any) {
      console.error('Error loading documents:', err)
      return []
    } finally {
      setIsLoadingDocuments(false)
    }
  }
  // Load documents on component mount
  useEffect(() => {
    loadDocuments()
  }, [])

  // Handle pending document selection after documents are loaded (backup mechanism)
  useEffect(() => {
    if (
      pendingDocumentSelection &&
      !isLoadingDocuments &&
      documents.length > 0
    ) {
      const documentExists = documents.some(
        (doc) => doc.id === pendingDocumentSelection,
      )

      if (documentExists) {
        setSelectedDocument(pendingDocumentSelection)
        setPendingDocumentSelection(null)
      }
    }
  }, [documents, isLoadingDocuments, pendingDocumentSelection])

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
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'application/vnd.ms-powerpoint',
      'image/jpeg',
      'image/png',
      'image/bmp',
      'image/tiff',
    ]
    const allowedExtensions = [
      '.pdf', '.md', '.markdown', '.html', '.htm', '.txt',
      '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',
      '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'
    ]
    const fileExtension = '.' + file.name.toLowerCase().split('.').pop()

    const isValidType =
      allowedTypes.includes(file.type) ||
      allowedExtensions.includes(fileExtension)

    if (!isValidType) {
      setError(
        'Unsupported file format. Supported: PDF, Word, Excel, PowerPoint, HTML, Markdown, TXT, and images (JPEG, PNG, BMP, TIFF)',
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
      const newDocument: Document = {
        id: response.data.id,
        document_id: response.data.document_id || response.data.id,
        title: response.data.title || response.data.filename || file.name,
        created_at: response.data.created_at || new Date().toISOString(),
        chunk_count: response.data.chunk_count || 0,
      }
      // Add the new document to the state immediately
      setDocuments((prev) => [...prev, newDocument])

      // Now select the document - it exists in state
      setSelectedDocument(response.data.id)
      setPendingDocumentSelection(response.data.id)

      // Add success message
      const successMessage: ChatMessage = {
        id: Date.now().toString(),
        type: 'assistant',
        content: `Document "${file.name}" uploaded successfully! You can now ask questions about this document.`,
        timestamp: new Date(),
        documentId: response.data.id,
      }
      setMessages((prev) => [...prev, successMessage])

      // Reload documents list and then select the uploaded document
      loadDocuments()
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
      const result = await documentService.deleteDocument(documentToDelete.id)
      if (!result.success) throw new Error(result.error || 'Delete failed')

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
        content: `Document "${documentToDelete.title}" has been deleted successfully.`,
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

  const selectedDocumentName = selectedDocument
    ? documents.find((doc) => doc.id === selectedDocument)?.title
    : null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!currentQuestion.trim() || isLoading || isStreaming) {
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
    setError(null)

    // Handle Deep Research mode
    if (deepResearchEnabled) {
      setIsLoading(true)

      try {
        // Start deep research workflow
        const startResult = await chatAgentService.startDeepResearch(questionText)

        if (!startResult.success || !startResult.data) {
          throw new Error(startResult.error || 'Failed to start deep research')
        }

        const runId = startResult.data.run_id
        setDeepResearchRunId(runId)

        // Add initial status message
        const statusMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: `🔬 **Deep Research Started**\n\nResearching: "${questionText}"\n\nPhase: ${startResult.data.current_phase}\n\n_This may take a few moments as the AI creates a research plan, gathers findings, and synthesizes a comprehensive report..._`,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, statusMessage])

        // Run the research workflow
        const runResult = await chatAgentService.runDeepResearch(runId)

        if (!runResult.success || !runResult.data) {
          throw new Error(runResult.error || 'Failed to run deep research')
        }

        // Create the final response message
        let finalContent = ''
        if (runResult.data.final_report) {
          finalContent = `## 📊 Deep Research Report\n\n${runResult.data.final_report}`
        } else if (runResult.data.findings && runResult.data.findings.length > 0) {
          finalContent = `## 📊 Research Findings\n\n`
          runResult.data.findings.forEach((finding: any, index: number) => {
            finalContent += `### ${index + 1}. ${finding.subtopic || 'Finding'}\n`
            finalContent += `${finding.content || JSON.stringify(finding)}\n\n`
          })
        } else {
          finalContent = `Research completed but no findings were generated. Status: ${runResult.data.status}`
        }

        // Sources are displayed in the structured Message component
        const sourcesForMessage = runResult.data.sources || []

        // Update the status message with the final report
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === statusMessage.id
              ? { ...msg, content: finalContent, sources: sourcesForMessage }
              : msg,
          ),
        )
      } catch (err: any) {
        console.error('Deep Research error:', err)
        setError(err.message || 'Failed to complete deep research. Please try again.')
      } finally {
        setIsLoading(false)
        setDeepResearchRunId(null)
      }
      return
    }

    // Build chat history from messages for context
    const chatHistory: ChatServiceMessage[] = messages.map((msg) => ({
      role: msg.type === 'user' ? 'user' : 'assistant',
      content: msg.content,
    }))

    if (streamingEnabled) {
      // Handle streaming response with Chat Agent
      setIsStreaming(true)

      // Create placeholder assistant message for streaming
      const assistantMessageId = (Date.now() + 1).toString()
      const placeholderMessage: ChatMessage = {
        id: assistantMessageId,
        type: 'assistant',
        content: '',
        timestamp: new Date(),
        documentId: selectedDocument || undefined,
      }
      setMessages((prev) => [...prev, placeholderMessage])

      try {
        const onChunk = (chunk: string) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, content: chunk } : msg,
            ),
          )
        }

        const onError = (error: string) => {
          setError(error)
          // Remove the placeholder message on error
          setMessages((prev) =>
            prev.filter((msg) => msg.id !== assistantMessageId),
          )
        }

        // Use Chat Agent for streaming
        await chatAgentService.streamMessage(
          questionText,
          sessionId,
          chatHistory,
          onChunk,
          onError,
        )
      } catch (err: any) {
        console.error('Chat Agent streaming error:', err)
        setError(err.message || 'Failed to stream response. Please try again.')

        // Remove the placeholder message on error
        setMessages((prev) =>
          prev.filter((msg) => msg.id !== assistantMessageId),
        )
      } finally {
        setIsStreaming(false)
      }
    } else {
      // Handle non-streaming response with Chat Agent
      setIsLoading(true)

      try {
        // Use Chat Agent
        const result = await chatAgentService.sendMessage(
          questionText,
          sessionId,
          chatHistory,
        )

        let assistantContent = ''
        if (result.success && result.data) {
          assistantContent = result.data.response
          // Update session ID if returned
          if (result.data.session_id) {
            setSessionId(result.data.session_id)
          }
        } else {
          throw new Error(
            result.error || 'Failed to get response from chat agent',
          )
        }

        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: assistantContent,
          timestamp: new Date(),
          documentId: selectedDocument || undefined,
        }

        setMessages((prev) => [...prev, assistantMessage])
      } catch (err: any) {
        console.error('Chat Agent API error:', err)
        setError(
          err.response?.data?.message ||
            'Failed to get response. Please try again.',
        )
      } finally {
        setIsLoading(false)
      }
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

  // Debug logging for selectedDocumentName
  useEffect(() => {
    if (selectedDocument) {
      console.log('Selected document ID:', selectedDocument)
      console.log(
        'Available documents:',
        documents.map((d) => ({ id: d.id, title: d.title })),
      )
      console.log('Selected document name:', selectedDocumentName)
    }
  }, [selectedDocument, documents, selectedDocumentName])

  return (
    <Container fluid className="chat-interface-container p-0">
      <Row className="flex-grow-1 overflow-hidden g-0 h-100">
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
          <div className="chat-header py-2 py-md-3 border-bottom flex-shrink-0">
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
                  disabled={documents.length === 0}
                >
                  Across All Docs
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
                      className={`document-chip d-flex align-items-center ${selectedDocument === doc.id ? 'selected' : ''}`}
                      style={{
                        backgroundColor:
                          selectedDocument === doc.id
                            ? 'rgba(0, 51, 102, 0.1)'
                            : '#f8f9fa',
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
                          fontWeight: selectedDocument === doc.id ? '600' : '400',
                        }}
                      >
                        <i className={`${getFileIcon(doc.title)} me-1`}></i>
                        {doc.title}
                      </Button>
                      <Button
                        variant="link"
                        size="sm"
                        onClick={() => handleDeleteDocument(doc)}
                        className="document-delete-btn border-0 p-1 d-flex align-items-center justify-content-center text-danger"
                        style={{ width: '1.75rem', height: '1.75rem' }}
                        title={`Remove ${doc.title}`}
                      >
                        <i
                          className="bi bi-x-circle-fill"
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
              <div className="empty-state">
                {isLoadingDocuments ? (
                  <>
                    <Spinner animation="border" className="mb-3" />
                    <h5>Loading documents...</h5>
                    <p>Please wait while we fetch your documents.</p>
                  </>
                ) : documents.length === 0 ? (
                  <>
                    <i className="bi bi-file-earmark-plus empty-state-icon"></i>
                    <h5>Get Started with Document Q&A</h5>
                    <p>
                      Upload your documents to start asking questions and get
                      AI-powered answers with source citations.
                    </p>
                    <Button
                      variant="primary"
                      onClick={() => setShowUploadModal(true)}
                      className="mb-3"
                      style={{ 
                        borderRadius: '0.75rem', 
                        fontWeight: '600',
                        padding: '0.5rem 1.5rem'
                      }}
                    >
                      <i className="bi bi-cloud-upload me-2"></i>
                      Upload Your First Document
                    </Button>
                    <div className="d-flex gap-3 justify-content-center flex-wrap small text-muted">
                      <span>
                        <i className="bi bi-check-circle-fill text-success me-1"></i>
                        PDF, Word, Excel, PowerPoint
                      </span>
                      <span>
                        <i className="bi bi-lightning-fill text-warning me-1"></i>
                        AI-Powered Search
                      </span>
                    </div>
                  </>
                ) : (
                  <>
                    <i className="bi bi-chat-quote empty-state-icon d-block"></i>
                    <h5>Welcome to AI Document Assistant</h5>
                    <p>
                      Upload documents (PDF, Word, Excel, PowerPoint, HTML, Markdown, or images) and ask
                      questions about them, or search across all your uploaded
                      documents.
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
                                style={{ fontSize: '1.1em', color: '#003366' }}
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
                                        )?.title || '',
                                      )} me-1`}
                                    ></i>
                                    {documents.find(
                                      (doc) => doc.id === message.documentId,
                                    )?.title || 'Document'}
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
                {(isLoading || isStreaming) && (
                  <div className="d-flex justify-content-start mb-2 mb-md-3">
                    <div
                      className="me-3 me-md-5"
                      style={{ maxWidth: 'min(80%, 50rem)' }}
                    >
                      <Card className="bg-light">
                        <Card.Body className="py-2 px-3">
                          <div className="d-flex align-items-center">
                            <i className="bi bi-robot me-2" style={{ color: '#003366' }}></i>
                            {isStreaming ? (
                              <>
                                <div
                                  className="spinner-grow spinner-grow-sm me-2"
                                  role="status"
                                  aria-hidden="true"
                                  style={{
                                    width: '0.75rem',
                                    height: '0.75rem',
                                  }}
                                ></div>
                                <span className="text-muted">
                                  {selectedDocument
                                    ? 'Streaming response...'
                                    : 'Streaming response...'}
                                </span>
                              </>
                            ) : (
                              <>
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
                              </>
                            )}
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
              <div className="d-flex justify-content-between align-items-start">
                <div>
                  <i className="bi bi-exclamation-triangle me-2"></i>
                  {error}
                </div>
                {streamingEnabled && (
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => {
                      setError(null)
                      // Retry the last question if available
                      if (messages.length > 0) {
                        const lastUserMessage = [...messages]
                          .reverse()
                          .find((msg) => msg.type === 'user')
                        if (lastUserMessage) {
                          setCurrentQuestion(lastUserMessage.content)
                        }
                      }
                    }}
                    className="ms-2"
                  >
                    <i className="bi bi-arrow-clockwise me-1"></i>
                    Retry
                  </Button>
                )}
              </div>
            </Alert>
          )}

          {/* Input Form */}
          <div className="border-top pt-2 pt-md-3 chat-input-container flex-shrink-0">
            <Form onSubmit={handleSubmit}>
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
                  <OverlayTrigger
                    placement="top"
                    overlay={<Tooltip id="deep-research-tooltip">Click for more info about Deep Research</Tooltip>}
                  >
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
                  <Alert variant="info" className="py-2 mb-2" style={{ fontSize: '0.85rem' }}>
                    <Alert.Heading as="h6" className="mb-1">
                      <i className="bi bi-lightbulb me-1"></i>
                      What is Deep Research?
                    </Alert.Heading>
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
                  </Alert>
                </div>
              </Collapse>

              <div className="position-relative">
                <Form.Control
                  as="textarea"
                  ref={textareaRef}
                  value={currentQuestion}
                  onChange={(e) => setCurrentQuestion(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder={
                    deepResearchEnabled
                      ? 'Enter a topic or complex question for deep research...'
                      : selectedDocument && selectedDocumentName
                        ? `Ask a question about ${selectedDocumentName}...`
                        : selectedDocument
                          ? 'Ask a question about the selected document...'
                          : documents.length === 0
                            ? 'Ask a general question or upload documents...'
                            : 'Ask a question across all your documents...'
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
                  variant={deepResearchEnabled ? 'warning' : 'primary'}
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
                  title={deepResearchEnabled ? 'Start Deep Research (Enter)' : 'Send message (Enter)'}
                >
                  {isLoading || isStreaming ? (
                    <Spinner
                      animation="border"
                      size="sm"
                      style={{ width: '1rem', height: '1rem' }}
                    />
                  ) : deepResearchEnabled ? (
                    <i
                      className="bi bi-search"
                      style={{
                        fontSize: 'clamp(0.875rem, 1rem, 1.125rem)',
                        fontWeight: 'bold',
                      }}
                    ></i>
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
                {deepResearchEnabled
                  ? 'Deep Research: AI will create a plan, gather findings, and synthesize a comprehensive report'
                  : documents.length === 0
                    ? 'Upload documents to search them, or ask general questions'
                    : selectedDocument
                      ? `Questions will be answered based on the selected document${streamingEnabled ? ' with streaming' : ''}`
                      : `Questions will be answered by searching across all your uploaded documents${streamingEnabled ? ' with streaming' : ''}`}
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
              accept=".pdf,.md,.markdown,.html,.htm,.txt,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.jpg,.jpeg,.png,.bmp,.tiff,.tif"
              style={{ display: 'none' }}
            />

            {!isUploading ? (
              <div>
                <i className="bi bi-files display-4 text-primary mb-3"></i>
                <h5>Select a document to upload</h5>
                <p className="text-muted">
                  Supported formats: PDF, Word, Excel, PowerPoint, HTML, Markdown, TXT, Images
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
                  ? getFileIcon(documentToDelete.title)
                  : 'bi-file-text'
              } display-4 text-danger mb-3`}
            ></i>
            <h5>Delete Document</h5>
            <p className="text-muted">
              Are you sure you want to delete "{documentToDelete?.title}"?
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
