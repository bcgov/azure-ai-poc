import type { FC } from 'react'
import { useEffect, useRef, useState } from 'react'
import { Message, Input } from '@/components/chat'
import type { SourceInfo } from '@/services/chatAgentService'
import {
  queryOrchestrator,
  getOrchestratorHealth,
  type OrchestratorHealthStatus,
} from '@/services/orchestratorService'
import '@/styles/chat.css'

interface ChatMessageType {
  id: string
  type: 'user' | 'assistant'
  content: string
  sources?: SourceInfo[]
  hasSufficientInfo?: boolean
  isStreaming?: boolean
  originalQuery?: string // For assistant messages, stores the user's query for retry
}

const EXAMPLE_QUERIES: string[] = [
]

const OrchestratorPage: FC = () => {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [sessionId] = useState<string>(`orch_${Date.now()}`)
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastFailedQuestion, setLastFailedQuestion] = useState<string | null>(null)
  const [healthStatus, setHealthStatus] = useState<OrchestratorHealthStatus | null>(null)
  const [selectedModel, setSelectedModel] = useState<string>('gpt-4o-mini')

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Check health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const status = await getOrchestratorHealth()
        setHealthStatus(status)
      } catch (err) {
        console.error('Failed to check orchestrator health:', err)
      }
    }
    checkHealth()
  }, [])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

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
      originalQuery: question,
    }

    setMessages((prev) => [...prev, userMessage, placeholderMessage])
    const questionToSend = question
    setCurrentQuestion('')
    setError(null)
    setLastFailedQuestion(null)
    setIsLoading(true)

    try {
      const response = await queryOrchestrator(questionToSend, sessionId, selectedModel)

      // Update placeholder with actual response
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content: response.response,
                sources: response.sources,
                hasSufficientInfo: response.has_sufficient_info,
                isStreaming: false,
              }
            : msg
        )
      )
    } catch (err: unknown) {
      console.error('Orchestrator query failed:', err)
      const errorMessage =
        err instanceof Error
          ? err.message
          : 'Failed to process query. Please try again.'
      setError(errorMessage)
      setLastFailedQuestion(questionToSend)
      // Remove placeholder message on error
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

  const handleExampleClick = (example: string) => {
    setCurrentQuestion(example)
  }

  const getHealthBadgeClass = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'copilot-source-badge high'
      case 'degraded':
        return 'copilot-source-badge medium'
      case 'unhealthy':
        return 'copilot-source-badge low'
      default:
        return 'copilot-source-badge'
    }
  }

  return (
    <div className="chat-layout">
      <div className="chat-main">
        <div className="copilot-chat-container">
          {/* Health Status Bar */}
          {healthStatus && (
            <div style={{ padding: '0.5rem 2rem', borderBottom: '1px solid #d0d7de' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.75rem', color: '#656d76' }}>
                  <i className="bi bi-diagram-3 me-1"></i>
                  Services:
                </span>
                <span className={getHealthBadgeClass(healthStatus.services.orgbook_api)}>
                  <i className="bi bi-building me-1"></i>
                  OrgBook
                </span>
                <span className={getHealthBadgeClass(healthStatus.services.geocoder_api)}>
                  <i className="bi bi-geo-alt me-1"></i>
                  Geocoder
                </span>
                <span className={getHealthBadgeClass(healthStatus.services.parks_api)}>
                  <i className="bi bi-tree me-1"></i>
                  Parks
                </span>
              </div>
            </div>
          )}

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
                  justifyContent: 'space-between',
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
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: '#a40e26',
                    }}
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
                  <i className="bi bi-diagram-3"></i>
                </div>
                <div className="copilot-empty-title">
                  Query BC Government Data Sources
                </div>
                <div className="copilot-empty-subtitle">
                  Ask about BC businesses (OrgBook), locations (Geocoder), or parks (BC Parks).
                  <br />
                  All responses include citations from official sources.
                </div>
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                    marginTop: '1.5rem',
                    justifyContent: 'center',
                  }}
                >
                  {EXAMPLE_QUERIES.map((example, i) => (
                    <button
                      key={i}
                      onClick={() => handleExampleClick(example)}
                      style={{
                        padding: '0.5rem 1rem',
                        borderRadius: '1rem',
                        border: '1px solid #d0d7de',
                        background: '#f6f8fa',
                        color: '#003366',
                        fontSize: '0.875rem',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                      onMouseOver={(e) => {
                        e.currentTarget.style.background = '#003366'
                        e.currentTarget.style.color = '#ffffff'
                      }}
                      onMouseOut={(e) => {
                        e.currentTarget.style.background = '#f6f8fa'
                        e.currentTarget.style.color = '#003366'
                      }}
                    >
                      {example}
                    </button>
                  ))}
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
            placeholder="Ask about BC businesses, locations, or parks..."
            selectedModel={selectedModel}
            onModelChange={setSelectedModel}
          />
        </div>
      </div>
    </div>
  )
}

export default OrchestratorPage
