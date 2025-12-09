import type { FC } from 'react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { SourceInfo } from '@/services/chatAgentService'
import {
  sortSourcesByConfidence,
  getSourceIcon,
  getConfidenceColor,
  formatSourceType,
} from '@/utils/sourceUtils'

interface MessageProps {
  type: 'user' | 'assistant'
  content: string
  sources?: SourceInfo[]
  hasSufficientInfo?: boolean
  isStreaming?: boolean
  onRetry?: () => void
  onThumbsUp?: () => void
  onThumbsDown?: () => void
}

const Message: FC<MessageProps> = ({
  type,
  content,
  sources,
  hasSufficientInfo,
  isStreaming,
  onRetry,
  onThumbsUp,
  onThumbsDown,
}) => {
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set())
  const [showAllSources, setShowAllSources] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const [copiedMessage, setCopiedMessage] = useState(false)
  const [feedbackGiven, setFeedbackGiven] = useState<'up' | 'down' | null>(null)

  // Sort sources by confidence (highest first)
  const sortedSources = sources ? sortSourcesByConfidence(sources) : []

  const toggleSource = (index: number) => {
    setExpandedSources((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedMessage(true)
      setTimeout(() => setCopiedMessage(false), 2000)
    } catch (err) {
      console.error('Failed to copy message:', err)
    }
  }

  const handleThumbsUp = () => {
    setFeedbackGiven('up')
    onThumbsUp?.()
  }

  const handleThumbsDown = () => {
    setFeedbackGiven('down')
    onThumbsDown?.()
  }

  if (type === 'user') {
    return (
      <div
        className="copilot-message user"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className="message-content">
          <div className={`message-actions user-actions ${isHovered ? 'visible' : ''}`}>
            <button
              className="action-btn"
              onClick={handleCopy}
              title={copiedMessage ? 'Copied!' : 'Copy message'}
            >
              <i className={`bi ${copiedMessage ? 'bi-check' : 'bi-clipboard'}`}></i>
            </button>
          </div>
          {content}
        </div>
      </div>
    )
  }

  return (
    <div className="copilot-message assistant">
      <div className="message-avatar">
        <i className="bi bi-robot"></i>
      </div>
      <div className="message-content">
        {content ? (
          <div className="markdown-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        ) : isStreaming ? (
          <div className="copilot-streaming">
            <span className="copilot-streaming-dot"></span>
            <span className="copilot-streaming-dot"></span>
            <span className="copilot-streaming-dot"></span>
          </div>
        ) : null}

        {/* Sources */}
        {sortedSources && sortedSources.length > 0 && (
          <div className="copilot-sources">
            <div className="copilot-sources-label">
              <i className="bi bi-info-circle me-1"></i>
              Sources ({sortedSources.length}):
            </div>
            <div className="sources-list">
              {(showAllSources ? sortedSources : sortedSources.slice(0, 3)).map((source, index) => (
                <div key={index} className="source-item">
                  <div
                    className={`copilot-source-badge ${source.confidence}`}
                    onClick={() => toggleSource(index)}
                    style={{ cursor: 'pointer' }}
                    title="Click to expand details"
                  >
                    <i className={`${getSourceIcon(source.source_type)} me-1`}></i>
                    <span>{formatSourceType(source.source_type)}</span>
                    <span
                      className="confidence-dot"
                      style={{
                        backgroundColor: getConfidenceColor(source.confidence),
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        display: 'inline-block',
                        marginLeft: '6px',
                      }}
                      title={`${source.confidence} confidence`}
                    ></span>
                    <i
                      className={`bi ${expandedSources.has(index) ? 'bi-chevron-up' : 'bi-chevron-down'} ms-1`}
                      style={{ fontSize: '0.65rem' }}
                    ></i>
                  </div>
                  {expandedSources.has(index) && (
                    <div
                      className="source-details"
                      style={{
                        marginTop: '0.5rem',
                        padding: '0.75rem',
                        backgroundColor: '#f8fafc',
                        borderRadius: '0.5rem',
                        fontSize: '0.8rem',
                        border: '1px solid #e2e8f0',
                      }}
                    >
                      <div style={{ marginBottom: '0.5rem' }}>
                        <strong>Description:</strong>
                        <div style={{ color: '#475569', marginTop: '0.25rem' }}>
                          {source.description}
                        </div>
                      </div>
                      {source.url && (
                        <div style={{ marginBottom: '0.5rem' }}>
                          <strong>URL:</strong>
                          <div style={{ marginTop: '0.25rem' }}>
                            <a
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                color: '#0969da',
                                wordBreak: 'break-all',
                                fontSize: '0.75rem',
                              }}
                            >
                              {source.url}
                            </a>
                          </div>
                        </div>
                      )}
                      {source.api_endpoint && (
                        <div style={{ marginBottom: '0.5rem' }}>
                          <strong>Endpoint:</strong>
                          <code
                            style={{
                              backgroundColor: '#e2e8f0',
                              padding: '0.125rem 0.375rem',
                              borderRadius: '0.25rem',
                              fontSize: '0.75rem',
                              marginLeft: '0.5rem',
                            }}
                          >
                            {source.api_endpoint}
                          </code>
                        </div>
                      )}
                      {source.api_params && Object.keys(source.api_params).length > 0 && (
                        <div>
                          <strong>Parameters:</strong>
                          <div
                            style={{
                              marginTop: '0.25rem',
                              backgroundColor: '#e2e8f0',
                              padding: '0.5rem',
                              borderRadius: '0.25rem',
                              fontFamily: 'monospace',
                              fontSize: '0.7rem',
                            }}
                          >
                            {Object.entries(source.api_params).map(([key, value]) => (
                              <div key={key}>
                                <span style={{ color: '#0969da' }}>{key}</span>: {value}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      <div
                        style={{
                          marginTop: '0.5rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                        }}
                      >
                        <strong>Confidence:</strong>
                        <span
                          style={{
                            color: getConfidenceColor(source.confidence),
                            fontWeight: 600,
                            textTransform: 'capitalize',
                          }}
                        >
                          {source.confidence}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {/* Show toggle when more than 3 sources */}
              {sortedSources.length > 3 && (
                <button
                  onClick={() => setShowAllSources(!showAllSources)}
                  style={{
                    marginTop: '0.5rem',
                    padding: '0.25rem 0.5rem',
                    background: 'transparent',
                    border: '1px solid #6c757d',
                    borderRadius: '4px',
                    color: '#6c757d',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                  }}
                >
                  {showAllSources
                    ? 'Show less'
                    : `+${sortedSources.length - 3} more sources`}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Insufficient Info Warning */}
        {hasSufficientInfo === false && (
          <div className="copilot-warning">
            <i className="bi bi-exclamation-triangle me-1"></i>
            Limited information available
          </div>
        )}

        {/* Action Bar - GitHub Copilot Chat style */}
        {!isStreaming && content && (
          <div className="message-actions assistant-actions">
            {onRetry && (
              <button
                className="action-btn"
                onClick={onRetry}
                title="Retry"
              >
                <i className="bi bi-arrow-clockwise"></i>
              </button>
            )}
            <button
              className={`action-btn ${feedbackGiven === 'up' ? 'active' : ''}`}
              onClick={handleThumbsUp}
              title="Good response"
              disabled={feedbackGiven !== null}
            >
              <i className={`bi ${feedbackGiven === 'up' ? 'bi-hand-thumbs-up-fill' : 'bi-hand-thumbs-up'}`}></i>
            </button>
            <button
              className={`action-btn ${feedbackGiven === 'down' ? 'active' : ''}`}
              onClick={handleThumbsDown}
              title="Bad response"
              disabled={feedbackGiven !== null}
            >
              <i className={`bi ${feedbackGiven === 'down' ? 'bi-hand-thumbs-down-fill' : 'bi-hand-thumbs-down'}`}></i>
            </button>
            <button
              className="action-btn"
              onClick={handleCopy}
              title={copiedMessage ? 'Copied!' : 'Copy response'}
            >
              <i className={`bi ${copiedMessage ? 'bi-check' : 'bi-clipboard'}`}></i>
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default Message
