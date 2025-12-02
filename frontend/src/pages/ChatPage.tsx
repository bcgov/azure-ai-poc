import apiService from '@/service/api-service'
import { chatAgentService, type ChatMessage as ChatAgentMessage } from '@/services/chatAgentService'
import { documentService } from '@/services/documentService'
import type { FC } from 'react'
import { useEffect, useRef, useState } from 'react'
import {
  Message,
  Input,
  DocumentUploadModal,
  DocumentDeleteConfirm,
  SessionsSidebar,
  type Document,
} from '@/components/chat'
import type { SourceInfo } from '@/services/chatAgentService'
import '@/styles/chat.css'

interface ChatMessageType {
  id: string
  type: 'user' | 'assistant'
  content: string
  sources?: SourceInfo[]
  hasSufficientInfo?: boolean
  isStreaming?: boolean
}

const ChatPage: FC = () => {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [sessionId, setSessionId] = useState<string>(`session_${Date.now()}`)
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [pendingDocumentSelection, setPendingDocumentSelection] = useState<string | null>(null)
  const [sessionRefreshTrigger, setSessionRefreshTrigger] = useState(0)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

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
    try {
      const result = await documentService.listDocuments()
      if (result.success && result.data) {
        setDocuments(result.data.documents)
      }
    } catch (err: any) {
      console.error('Error loading documents:', err)
    }
  }

  useEffect(() => {
    loadDocuments()
  }, [])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  useEffect(() => {
    if (
      pendingDocumentSelection &&
      documents.some((doc) => doc.id === pendingDocumentSelection)
    ) {
      setSelectedDocument(pendingDocumentSelection)
      setPendingDocumentSelection(null)
    }
  }, [documents, pendingDocumentSelection])

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
      const result = await documentService.deleteDocument(documentToDelete.id)
      if (!result.success) {
        throw new Error(result.error || 'Delete failed')
      }

      setDocuments((prev) => prev.filter((doc) => doc.id !== documentToDelete.id))

      if (selectedDocument === documentToDelete.id) {
        setSelectedDocument(null)
      }

      const successMessage: ChatMessageType = {
        id: Date.now().toString(),
        type: 'assistant',
        content: `Document "${documentToDelete.filename}" has been deleted successfully.`,
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

  const handleSubmit = async () => {
    if (!currentQuestion.trim() || isLoading) return

    const userMessage: ChatMessageType = {
      id: Date.now().toString(),
      type: 'user',
      content: currentQuestion,
    }

    const assistantMessageId = (Date.now() + 1).toString()
    const placeholderMessage: ChatMessageType = {
      id: assistantMessageId,
      type: 'assistant',
      content: '',
      isStreaming: true,
    }

    setMessages((prev) => [...prev, userMessage, placeholderMessage])
    const questionToSend = currentQuestion
    setCurrentQuestion('')
    setError(null)
    setIsLoading(true)

    // Build chat history
    const chatHistory: ChatAgentMessage[] = messages.map((msg) => ({
      role: msg.type === 'user' ? 'user' : 'assistant',
      content: msg.content,
    }))

    try {
      const onChunk = (chunk: string) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId 
              ? { ...msg, content: chunk, isStreaming: true } 
              : msg,
          ),
        )
      }

      const onError = (error: string) => {
        setError(error)
        setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId))
      }

      const streamResult = await chatAgentService.streamMessage(
        questionToSend,
        sessionId,
        chatHistory,
        onChunk,
        onError,
      )

      // Update message with sources after streaming completes
      if (streamResult) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  sources: streamResult.sources,
                  hasSufficientInfo: streamResult.hasSufficientInfo,
                  isStreaming: false,
                }
              : msg,
          ),
        )
        if (streamResult.sessionId) {
          setSessionId(streamResult.sessionId)
        }
        // Trigger sidebar refresh after successful message
        setSessionRefreshTrigger((prev) => prev + 1)
      } else {
        // Remove streaming flag even if no result
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, isStreaming: false }
              : msg,
          ),
        )
      }
    } catch (err: any) {
      console.error('Chat error:', err)
      setError(err.message || 'Failed to get response. Please try again.')
      setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId))
    } finally {
      setIsLoading(false)
    }
  }

  const handleSessionSelect = (
    newSessionId: string,
    historyMessages?: Array<{ role: string; content: string }>,
  ) => {
    setSessionId(newSessionId)
    if (historyMessages) {
      const loadedMessages: ChatMessageType[] = historyMessages.map((msg, index) => ({
        id: `loaded_${index}`,
        type: msg.role === 'user' ? 'user' : 'assistant',
        content: msg.content,
      }))
      setMessages(loadedMessages)
    } else {
      setMessages([])
    }
    setError(null)
  }

  const handleNewSession = () => {
    setSessionId(`session_${Date.now()}`)
    setMessages([])
    setError(null)
    setSelectedDocument(null)
  }

  return (
    <div className="chat-layout">
      <SessionsSidebar
        currentSessionId={sessionId}
        onSessionSelect={handleSessionSelect}
        onNewSession={handleNewSession}
        refreshTrigger={sessionRefreshTrigger}
      />
      <div className="chat-main">
        <div className="copilot-chat-container">
          {/* Error */}
          {error && (
            <div style={{ padding: '0.5rem 2rem' }}>
              <div 
                style={{ 
                  background: '#ffebe9', 
                  border: '1px solid #ff8182', 
                  borderRadius: '0.5rem',
                  padding: '0.75rem 1rem',
                  color: '#a40e26',
                  fontSize: '0.875rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}
              >
                <span>
                  <i className="bi bi-exclamation-triangle me-2"></i>
                  {error}
                </span>
                <button 
                  onClick={() => setError(null)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#a40e26' }}
                >
                  <i className="bi bi-x-lg"></i>
                </button>
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="copilot-messages">
        {messages.length === 0 ? (
          <div className="copilot-empty">
            <div className="copilot-empty-icon">
              <i className="bi bi-stars"></i>
            </div>
            <div className="copilot-empty-title">How can I help you today?</div>
            <div className="copilot-empty-subtitle">
              Ask me anything. I can help you with questions, analysis, coding, and more.
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <Message
                key={message.id}
                type={message.type}
                content={message.content}
                sources={message.sources}
                hasSufficientInfo={message.hasSufficientInfo}
                isStreaming={message.isStreaming}
              />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <Input
        value={currentQuestion}
        onChange={setCurrentQuestion}
        onSubmit={handleSubmit}
        isLoading={isLoading}
        placeholder="Ask anything"
        onUploadClick={() => setShowUploadModal(true)}
        selectedDocument={selectedDocument}
      />

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
        </div>
      </div>
    </div>
  )
}

export default ChatPage
