import apiService from '@/service/api-service'
import { langGraphAgentService } from '@/services/langGraphAgentService'
import type { FC } from 'react'
import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Col, Container, Row } from 'react-bootstrap'
import {
  ChatMessage,
  ChatInput,
  DocumentList,
  DocumentUploadModal,
  DocumentDeleteConfirm,
  ChatEmptyState,
  type Document,
} from '@/components/chat'

interface ChatMessageType {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  documentId?: string
}

const ChatPage: FC = () => {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingEnabled, setStreamingEnabled] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true)
  const [pendingDocumentSelection, setPendingDocumentSelection] = useState<string | null>(null)

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
      const response = await apiService.getAxiosInstance().get('/api/v1/documents')
      setDocuments(response.data)
      return response.data
    } catch (err: any) {
      console.error('Error loading documents:', err)
      return []
    } finally {
      setIsLoadingDocuments(false)
    }
  }

  useEffect(() => {
    loadDocuments()
  }, [])

  useEffect(() => {
    if (
      pendingDocumentSelection &&
      documents.some((doc) => doc.id === pendingDocumentSelection)
    ) {
      setSelectedDocument(pendingDocumentSelection)
      setPendingDocumentSelection(null)
    }
  }, [documents, pendingDocumentSelection])

  useEffect(() => {
    if (messages.length > previousMessageCount.current && shouldAutoScrollOnNewMessage.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
    previousMessageCount.current = messages.length
  }, [messages])

  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container
      const distanceFromBottom = scrollHeight - (scrollTop + clientHeight)
      shouldAutoScrollOnNewMessage.current = distanceFromBottom < 100
    }

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [])

  const handleUploadDocument = async (file: File) => {
    setIsUploading(true)
    setError(null)
    setUploadProgress(0)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await apiService
        .getAxiosInstance()
        .post('/api/v1/documents/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
              setUploadProgress(progress)
            }
          },
        })

      const newDocument: Document = {
        id: response.data.id,
        filename: response.data.filename || file.name,
        uploadedAt: response.data.uploadedAt || new Date().toISOString(),
        totalPages: response.data.totalPages,
      }

      setDocuments((prev) => [...prev, newDocument])
      setSelectedDocument(response.data.id)
      setPendingDocumentSelection(response.data.id)

      const successMessage: ChatMessageType = {
        id: Date.now().toString(),
        type: 'assistant',
        content: `Document "${file.name}" uploaded successfully! You can now ask questions about this document.`,
        timestamp: new Date(),
        documentId: response.data.id,
      }
      setMessages((prev) => [...prev, successMessage])

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
      await apiService.getAxiosInstance().delete(`/api/v1/documents/${documentToDelete.id}`)

      setDocuments((prev) => prev.filter((doc) => doc.id !== documentToDelete.id))

      if (selectedDocument === documentToDelete.id) {
        setSelectedDocument(null)
      }

      const successMessage: ChatMessageType = {
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
    if (!currentQuestion.trim() || isLoading || documents.length === 0) return

    const userMessage: ChatMessageType = {
      id: Date.now().toString(),
      type: 'user',
      content: currentQuestion,
      timestamp: new Date(),
      documentId: selectedDocument || undefined,
    }

    setMessages((prev) => [...prev, userMessage])
    setCurrentQuestion('')
    setError(null)

    if (streamingEnabled) {
      setIsStreaming(true)
      const assistantMessageId = (Date.now() + 1).toString()
      const placeholderMessage: ChatMessageType = {
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
          setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId))
        }

        await langGraphAgentService.streamDocumentQuery(
          currentQuestion,
          selectedDocument ? [selectedDocument] : undefined,
          `session_${Date.now()}`,
          onChunk,
          onError,
        )
      } catch (err: any) {
        console.error('LangGraph streaming error:', err)
        setError(err.message || 'Failed to stream response. Please try again.')
        setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId))
      } finally {
        setIsStreaming(false)
      }
    } else {
      setIsLoading(true)
      try {
        const result = await langGraphAgentService.queryDocuments(
          currentQuestion,
          selectedDocument ? [selectedDocument] : undefined,
          `session_${Date.now()}`,
          selectedDocument ? `Document: ${selectedDocumentName}` : undefined,
        )

        let assistantContent = ''
        if (result.success && result.data) {
          assistantContent = result.data.answer
        } else {
          throw new Error(result.error || 'Failed to get response from LangGraph agent')
        }

        const assistantMessage: ChatMessageType = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: assistantContent,
          timestamp: new Date(),
          documentId: selectedDocument || undefined,
        }

        setMessages((prev) => [...prev, assistantMessage])
      } catch (err: any) {
        console.error('LangGraph API error:', err)
        setError(err.message || 'Failed to get response. Please try again.')
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

  const selectedDocumentName = selectedDocument
    ? documents.find((doc) => doc.id === selectedDocument)?.filename ?? null
    : null

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
              <DocumentList
                documents={documents}
                selectedDocument={selectedDocument}
                onSelectDocument={setSelectedDocument}
                onDeleteDocument={handleDeleteDocument}
                isLoadingDocuments={isLoadingDocuments}
                getFileIcon={getFileIcon}
              />
            </div>
          </div>

          {/* Error Alert */}
          {error && (
            <Alert variant="danger" onClose={() => setError(null)} dismissible>
              <i className="bi bi-exclamation-triangle me-2"></i>
              {error}
            </Alert>
          )}

          {/* Messages Area */}
          <div
            ref={messagesContainerRef}
            className="chat-messages flex-grow-1 overflow-auto px-1 px-md-2"
          >
            {messages.length === 0 ? (
              <ChatEmptyState
                documentsCount={documents.length}
                onUploadClick={() => setShowUploadModal(true)}
              />
            ) : (
              <div className="space-y-3">
                {messages.map((message) => (
                  <ChatMessage
                    key={message.id}
                    type={message.type}
                    content={message.content}
                    timestamp={message.timestamp}
                    documentId={message.documentId}
                    documentName={
                      message.documentId
                        ? documents.find((doc) => doc.id === message.documentId)?.filename
                        : undefined
                    }
                    getFileIcon={getFileIcon}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Chat Input */}
          <ChatInput
            currentQuestion={currentQuestion}
            setCurrentQuestion={setCurrentQuestion}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            isStreaming={isStreaming}
            streamingEnabled={streamingEnabled}
            setStreamingEnabled={setStreamingEnabled}
            documentsCount={documents.length}
            selectedDocument={selectedDocument}
            selectedDocumentName={selectedDocumentName}
            onKeyPress={handleKeyPress}
          />
        </Col>
      </Row>

      {/* Upload Modal */}
      <DocumentUploadModal
        show={showUploadModal}
        onHide={() => setShowUploadModal(false)}
        onUpload={handleUploadDocument}
        isUploading={isUploading}
        uploadProgress={uploadProgress}
        error={error}
        fileInputRef={fileInputRef}
      />

      {/* Delete Confirmation Modal */}
      <DocumentDeleteConfirm
        show={showDeleteConfirm}
        document={documentToDelete}
        onConfirm={confirmDeleteDocument}
        onCancel={cancelDeleteDocument}
        isDeleting={isDeleting}
        getFileIcon={getFileIcon}
      />
    </Container>
  )
}

export default ChatPage
