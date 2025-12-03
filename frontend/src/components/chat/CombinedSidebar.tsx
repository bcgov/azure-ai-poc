import type { FC } from 'react'
import { useState, useEffect, useCallback } from 'react'
import { chatAgentService, type Session } from '@/services/chatAgentService'
import { documentService, type DocumentItem } from '@/services/documentService'
import type { Document } from './DocumentList'

interface CombinedSidebarProps {
  currentSessionId: string
  onSessionSelect: (sessionId: string, messages?: Array<{ role: string; content: string }>) => void
  onNewSession: () => void
  refreshTrigger?: number
  // Document props
  documents: Document[]
  selectedDocument: string | null
  onSelectDocument: (documentId: string | null) => void
  onDeleteDocument: (document: Document) => void
  onUploadClick: () => void
  isLoadingDocuments?: boolean
  getFileIcon: (filename: string) => string
  onDocumentsRefresh?: () => void
}

export const CombinedSidebar: FC<CombinedSidebarProps> = ({
  currentSessionId,
  onSessionSelect,
  onNewSession,
  refreshTrigger = 0,
  documents,
  selectedDocument,
  onSelectDocument,
  onDeleteDocument,
  onUploadClick,
  isLoadingDocuments = false,
  getFileIcon,
  onDocumentsRefresh,
}) => {
  const [sessions, setSessions] = useState<Session[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [activeTab, setActiveTab] = useState<'conversations' | 'documents'>('conversations')

  const loadSessions = useCallback(async () => {
    setIsLoading(true)
    try {
      const result = await chatAgentService.listSessions(20)
      if (result.success && result.data) {
        setSessions(result.data.sessions)
      }
    } catch (error) {
      console.error('Failed to load sessions:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  useEffect(() => {
    if (refreshTrigger > 0) {
      const timer = setTimeout(() => {
        loadSessions()
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [refreshTrigger, loadSessions])

  const handleSessionClick = async (session: Session) => {
    if (session.session_id === currentSessionId) return

    try {
      const result = await chatAgentService.getSessionHistory(session.session_id)
      if (result.success && result.data) {
        const messages = result.data.messages.map((msg) => ({
          role: msg.role,
          content: msg.content,
        }))
        onSessionSelect(session.session_id, messages)
      } else {
        onSessionSelect(session.session_id)
      }
    } catch (error) {
      console.error('Failed to load session history:', error)
      onSessionSelect(session.session_id)
    }
  }

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    if (!confirm('Delete this conversation?')) return

    try {
      await chatAgentService.deleteSession(sessionId)
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId))
      if (sessionId === currentSessionId) {
        onNewSession()
      }
    } catch (error) {
      console.error('Failed to delete session:', error)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  if (isCollapsed) {
    return (
      <div className="combined-sidebar collapsed">
        <button
          className="sidebar-toggle"
          onClick={() => setIsCollapsed(false)}
          title="Show sidebar"
        >
          <i className="bi bi-layout-sidebar"></i>
        </button>
      </div>
    )
  }

  return (
    <div className="combined-sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-tabs">
          <button
            className={`sidebar-tab ${activeTab === 'conversations' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('conversations')
              onSelectDocument(null)
            }}
          >
            <i className="bi bi-chat-left-text me-1"></i>
            Chats
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveTab('documents')}
          >
            <i className="bi bi-file-earmark-text me-1"></i>
            Docs
            {selectedDocument && (
              <span className="doc-indicator" title="Document selected">•</span>
            )}
          </button>
        </div>
        <button
          className="sidebar-toggle"
          onClick={() => setIsCollapsed(true)}
          title="Hide sidebar"
        >
          <i className="bi bi-chevron-left"></i>
        </button>
      </div>

      {/* Content */}
      <div className="sidebar-content">
        {activeTab === 'conversations' ? (
          <>
            {/* New Chat Button */}
            <button className="new-item-btn" onClick={onNewSession}>
              <i className="bi bi-plus-lg me-2"></i>
              New Conversation
            </button>

            {/* Sessions List */}
            <div className="items-list">
              {isLoading ? (
                <div className="items-loading">
                  <i className="bi bi-arrow-repeat spinning"></i>
                  Loading...
                </div>
              ) : sessions.length === 0 ? (
                <div className="items-empty">
                  <i className="bi bi-chat-left-dots"></i>
                  <p>No conversations yet</p>
                </div>
              ) : (
                sessions.map((session) => (
                  <div
                    key={session.session_id}
                    className={`list-item ${session.session_id === currentSessionId ? 'active' : ''}`}
                    onClick={() => handleSessionClick(session)}
                  >
                    <div className="item-icon">
                      <i className="bi bi-chat-left"></i>
                    </div>
                    <div className="item-info">
                      <div className="item-title">{session.title}</div>
                      <div className="item-meta">
                        {session.message_count} msgs · {formatDate(session.last_updated)}
                      </div>
                    </div>
                    <button
                      className="item-delete"
                      onClick={(e) => handleDeleteSession(e, session.session_id)}
                      title="Delete"
                    >
                      <i className="bi bi-trash"></i>
                    </button>
                  </div>
                ))
              )}
            </div>
          </>
        ) : (
          <>
            {/* Upload Button */}
            <button className="new-item-btn" onClick={onUploadClick}>
              <i className="bi bi-cloud-upload me-2"></i>
              Upload Document
            </button>

            {/* Clear Selection */}
            {selectedDocument && (
              <button
                className="clear-selection-btn"
                onClick={() => onSelectDocument(null)}
              >
                <i className="bi bi-x-circle me-2"></i>
                Clear Document Selection
              </button>
            )}

            {/* Documents List */}
            <div className="items-list">
              {isLoadingDocuments ? (
                <div className="items-loading">
                  <i className="bi bi-arrow-repeat spinning"></i>
                  Loading...
                </div>
              ) : documents.length === 0 ? (
                <div className="items-empty">
                  <i className="bi bi-file-earmark"></i>
                  <p>No documents uploaded</p>
                  <p className="items-empty-hint">Upload a document to ask questions about it</p>
                </div>
              ) : (
                documents.map((doc) => (
                  <div
                    key={doc.id}
                    className={`list-item ${selectedDocument === doc.id ? 'active selected-doc' : ''}`}
                    onClick={() => onSelectDocument(selectedDocument === doc.id ? null : doc.id)}
                  >
                    <div className="item-icon doc-icon">
                      <i className={`bi ${getFileIcon(doc.title)}`}></i>
                    </div>
                    <div className="item-info">
                      <div className="item-title">{doc.title}</div>
                      <div className="item-meta">
                        {doc.chunk_count ? `${doc.chunk_count} chunks` : 'Document'}
                        {selectedDocument === doc.id && (
                          <span className="selected-badge">Selected</span>
                        )}
                      </div>
                    </div>
                    <button
                      className="item-delete"
                      onClick={(e) => {
                        e.stopPropagation()
                        onDeleteDocument(doc)
                      }}
                      title="Delete"
                    >
                      <i className="bi bi-trash"></i>
                    </button>
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </div>

      {/* Footer with refresh */}
      <div className="sidebar-footer">
        <button
          className="refresh-btn"
          onClick={() => {
            if (activeTab === 'conversations') {
              loadSessions()
            } else if (onDocumentsRefresh) {
              onDocumentsRefresh()
            }
          }}
          title="Refresh"
        >
          <i className="bi bi-arrow-clockwise"></i>
          Refresh
        </button>
      </div>
    </div>
  )
}

export default CombinedSidebar
