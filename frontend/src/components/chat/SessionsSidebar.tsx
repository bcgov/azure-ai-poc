import type { FC } from 'react'
import { useState, useEffect, useCallback } from 'react'
import { chatAgentService, type Session } from '@/services/chatAgentService'

interface SessionsSidebarProps {
  currentSessionId: string
  onSessionSelect: (sessionId: string, messages?: Array<{ role: string; content: string }>) => void
  onNewSession: () => void
  refreshTrigger?: number // Increment to trigger refresh
}

export const SessionsSidebar: FC<SessionsSidebarProps> = ({
  currentSessionId,
  onSessionSelect,
  onNewSession,
  refreshTrigger = 0,
}) => {
  const [sessions, setSessions] = useState<Session[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCollapsed, setIsCollapsed] = useState(false)

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

  // Reload sessions when refreshTrigger changes (after sending a message)
  useEffect(() => {
    if (refreshTrigger > 0) {
      const timer = setTimeout(() => {
        loadSessions()
      }, 500) // Short delay to allow backend to process
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
      <div className="sessions-sidebar collapsed">
        <button
          className="sessions-toggle"
          onClick={() => setIsCollapsed(false)}
          title="Show conversations"
        >
          <i className="bi bi-chat-left-text"></i>
        </button>
      </div>
    )
  }

  return (
    <div className="sessions-sidebar">
      <div className="sessions-header">
        <h3>Conversations</h3>
        <div className="sessions-actions">
          <button
            className="sessions-new-btn"
            onClick={onNewSession}
            title="New conversation"
          >
            <i className="bi bi-plus-lg"></i>
          </button>
          <button
            className="sessions-toggle"
            onClick={() => setIsCollapsed(true)}
            title="Hide sidebar"
          >
            <i className="bi bi-chevron-left"></i>
          </button>
        </div>
      </div>

      <div className="sessions-list">
        {isLoading ? (
          <div className="sessions-loading">
            <i className="bi bi-arrow-repeat spinning"></i>
            Loading...
          </div>
        ) : sessions.length === 0 ? (
          <div className="sessions-empty">
            <i className="bi bi-chat-left-dots"></i>
            <p>No conversations yet</p>
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.session_id}
              className={`session-item ${session.session_id === currentSessionId ? 'active' : ''}`}
              onClick={() => handleSessionClick(session)}
            >
              <div className="session-icon">
                <i className="bi bi-chat-left"></i>
              </div>
              <div className="session-info">
                <div className="session-title">{session.title}</div>
                <div className="session-meta">
                  {session.message_count} messages · {formatDate(session.last_updated)}
                </div>
              </div>
              <button
                className="session-delete"
                onClick={(e) => handleDeleteSession(e, session.session_id)}
                title="Delete conversation"
              >
                <i className="bi bi-trash"></i>
              </button>
            </div>
          ))
        )}
      </div>

      <button className="sessions-refresh" onClick={loadSessions} title="Refresh">
        <i className="bi bi-arrow-clockwise"></i>
        Refresh
      </button>
    </div>
  )
}

export default SessionsSidebar
