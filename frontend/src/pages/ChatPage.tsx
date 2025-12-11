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
  CombinedSidebar,
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
  isResearchPhase?: boolean
  researchPhase?: string
  originalQuery?: string // For assistant messages, stores the user's query for retry
}

const ChatPage: FC = () => {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [sessionId, setSessionId] = useState<string>(`session_${Date.now()}`)
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastFailedQuestion, setLastFailedQuestion] = useState<string | null>(null)
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
  const [deepResearchEnabled, setDeepResearchEnabled] = useState(false)
  const [deepResearchRunId, setDeepResearchRunId] = useState<string | null>(null)
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false)
  const [selectedModel, setSelectedModel] = useState<'gpt-4o-mini' | 'gpt-41-nano'>('gpt-4o-mini')

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const getFileIcon = (filename: string | undefined | null): string => {
    if (!filename) return 'bi-file-text'
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
        // Use documents directly - they are already DocumentItem type
        setDocuments(result.data.documents)
      }
    } catch (err: any) {
      console.error('Error loading documents:', err)
    } finally {
      setIsLoadingDocuments(false)
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
        document_id: response.data.document_id || response.data.id,
        title: response.data.title || response.data.filename || file.name,
        created_at: response.data.created_at || new Date().toISOString(),
        chunk_count: response.data.chunk_count || 0,
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
        content: `Document "${documentToDelete.title}" has been deleted successfully.`,
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

  const handleSubmit = async (overrideQuestion?: string) => {
    const question = (overrideQuestion ?? currentQuestion).trim()
    if (!question || isLoading) return

    const userMessage: ChatMessageType = {
      id: Date.now().toString(),
      type: 'user',
      content: question,
    }

    const assistantMessageId = (Date.now() + 1).toString()
    const placeholderMessage: ChatMessageType = {
      id: assistantMessageId,
      type: 'assistant',
      content: '',
      isStreaming: true,
      isResearchPhase: deepResearchEnabled,
      researchPhase: deepResearchEnabled ? 'Starting research...' : undefined,
      originalQuery: question,
    }

    setMessages((prev) => [...prev, userMessage, placeholderMessage])
    const questionToSend = question
    setCurrentQuestion('')
    setError(null)
    setLastFailedQuestion(null)
    setIsLoading(true)

    // Build chat history
    const chatHistory: ChatAgentMessage[] = messages.map((msg) => ({
      role: msg.type === 'user' ? 'user' : 'assistant',
      content: msg.content,
    }))

    try {
      if (deepResearchEnabled) {
        // Deep Research Mode - pass document_id if selected
        await handleDeepResearch(questionToSend, assistantMessageId, chatHistory)
      } else {
        // Regular chat mode - pass document_id if selected
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
          selectedDocument || undefined, // Pass document ID for RAG
          selectedModel, // Pass selected model
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
      }
    } catch (err: any) {
      console.error('Chat error:', err)
      setError(err.message || 'Failed to get response. Please try again.')
      setLastFailedQuestion(questionToSend)
      setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId))
    } finally {
      setIsLoading(false)
    }
  }

  const handleRetry = () => {
    if (lastFailedQuestion) {
      setCurrentQuestion(lastFailedQuestion)
      void handleSubmit(lastFailedQuestion)
    }
  }

  // Retry a specific assistant message by re-sending its original query
  const handleRetryMessage = (messageId: string, originalQuery: string) => {
    if (isLoading || !originalQuery) return
    
    // Remove the assistant message being retried (keep the user message)
    setMessages((prev) => prev.filter((msg) => msg.id !== messageId))
    
    // Re-submit the original query
    void handleSubmit(originalQuery)
  }

  // Placeholder for thumbs up/down feedback - can be connected to analytics later
  const handleThumbsUp = (messageId: string) => {
    console.log('Thumbs up feedback for message:', messageId)
    // TODO: Send feedback to analytics/backend
  }

  const handleThumbsDown = (messageId: string) => {
    console.log('Thumbs down feedback for message:', messageId)
    // TODO: Send feedback to analytics/backend
  }

  const handleDeepResearch = async (
    question: string,
    messageId: string,
    chatHistory: ChatAgentMessage[],
  ) => {
    try {
      // Start the deep research - pass document_id if selected for thorough scanning
      const startResult = await chatAgentService.startDeepResearch(
        question,
        undefined, // userId handled by backend auth
        selectedDocument || undefined, // Pass document ID for document-based research
      )
      
      if (!startResult.success || !startResult.data?.run_id) {
        throw new Error(startResult.error || 'Failed to start deep research')
      }
      
      setDeepResearchRunId(startResult.data.run_id)
      
      // Update message with initial status - indicate if document is being scanned
      const statusMessage = selectedDocument 
        ? '🔬 **Deep Research Started**\n\n📄 Scanning document thoroughly...'
        : '🔬 **Deep Research Started**\n\nPlanning research strategy...'
      
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? { 
                ...msg, 
                content: statusMessage, 
                researchPhase: selectedDocument ? 'Scanning Document' : 'Planning',
              }
            : msg,
        ),
      )

      // Run the research (non-streaming for now)
      const runResult = await chatAgentService.runDeepResearch(startResult.data.run_id)
      
      if (!runResult.success || !runResult.data) {
        throw new Error(runResult.error || 'Failed to run deep research')
      }

      // Update with final result
      let finalContent = ''
      if (runResult.data.final_report) {
        finalContent = runResult.data.final_report
      } else if (runResult.data.message) {
        finalContent = runResult.data.message
      } else if (runResult.data.findings && runResult.data.findings.length > 0) {
        finalContent = '## Research Findings\n\n' + runResult.data.findings
          .map((f, i) => `### Finding ${i + 1}\n${JSON.stringify(f, null, 2)}`)
          .join('\n\n---\n\n')
      } else {
        finalContent = 'Research completed but no results were returned.'
      }

      // Append sources if available (show top 3 + count)
      // Sources are now displayed in the structured Message component, not in markdown
      const sourcesForMessage = runResult.data.sources || []

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                content: finalContent,
                sources: sourcesForMessage,
                isStreaming: false,
                isResearchPhase: false,
                researchPhase: undefined,
              }
            : msg,
        ),
      )

      setDeepResearchRunId(null)
      setSessionRefreshTrigger((prev) => prev + 1)
    } catch (err: any) {
      console.error('Deep research error:', err)
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                content: `❌ **Research Failed**\n\n${err.message || 'An error occurred during research.'}`,
                isStreaming: false,
                isResearchPhase: false,
              }
            : msg,
        ),
      )
      setDeepResearchRunId(null)
      throw err
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
      <CombinedSidebar
        currentSessionId={sessionId}
        onSessionSelect={handleSessionSelect}
        onNewSession={handleNewSession}
        refreshTrigger={sessionRefreshTrigger}
        documents={documents}
        selectedDocument={selectedDocument}
        onSelectDocument={setSelectedDocument}
        onDeleteDocument={handleDeleteDocument}
        onUploadClick={() => setShowUploadModal(true)}
        isLoadingDocuments={isLoadingDocuments}
        getFileIcon={getFileIcon}
        onDocumentsRefresh={loadDocuments}
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
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  {lastFailedQuestion && (
                    <button
                      onClick={handleRetry}
                      style={{
                        background: '#a40e26',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '0.375rem',
                        padding: '0.35rem 0.75rem',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                      }}
                      disabled={isLoading}
                    >
                      Retry
                    </button>
                  )}
                  <button 
                    onClick={() => setError(null)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#a40e26' }}
                  >
                    <i className="bi bi-x-lg"></i>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="copilot-messages">
        {messages.length === 0 ? (
          <div className="copilot-empty">
            <div className="copilot-empty-icon">
              <i className="bi bi-robot"></i>
            </div>
            <div className="copilot-empty-title">How can I help you today?</div>
            <div className="copilot-empty-subtitle">
              {selectedDocument 
                ? 'Ask questions about the selected document, or use Deep Research for thorough analysis.'
                : 'Ask me anything. Select a document from the sidebar to ask questions about it.'
              }
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
                onRetry={message.type === 'assistant' && message.originalQuery 
                  ? () => handleRetryMessage(message.id, message.originalQuery!) 
                  : undefined}
                onThumbsUp={message.type === 'assistant' 
                  ? () => handleThumbsUp(message.id) 
                  : undefined}
                onThumbsDown={message.type === 'assistant' 
                  ? () => handleThumbsDown(message.id) 
                  : undefined}
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
        placeholder={selectedDocument ? "Ask about the selected document..." : "Ask anything"}
        onUploadClick={() => setShowUploadModal(true)}
        selectedDocument={selectedDocument}
        selectedDocumentName={selectedDocument ? documents.find(d => d.id === selectedDocument)?.title : null}
        onClearDocument={() => setSelectedDocument(null)}
        deepResearchEnabled={deepResearchEnabled}
        onDeepResearchChange={setDeepResearchEnabled}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
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
