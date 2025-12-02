import type { FC } from 'react'
import { useState } from 'react'
import type { SourceInfo } from '@/services/chatAgentService'

interface MessageProps {
  type: 'user' | 'assistant'
  content: string
  sources?: SourceInfo[]
  hasSufficientInfo?: boolean
  isStreaming?: boolean
}

const Message: FC<MessageProps> = ({
  type,
  content,
  sources,
  hasSufficientInfo,
  isStreaming,
}) => {
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set())

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

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType) {
      case 'llm_knowledge':
        return 'bi-cpu'
      case 'document':
        return 'bi-file-text'
      case 'web':
        return 'bi-globe'
      case 'api':
        return 'bi-code-square'
      default:
        return 'bi-question-circle'
    }
  }

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return '#16a34a'
      case 'medium':
        return '#ca8a04'
      case 'low':
        return '#dc2626'
      default:
        return '#6b7280'
    }
  }

  if (type === 'user') {
    return (
      <div className="copilot-message user">
        <div className="message-content">{content}</div>
      </div>
    )
  }

  return (
    <div className="copilot-message assistant">
      <div className="message-avatar">
        <i className="bi bi-stars"></i>
      </div>
      <div className="message-content">
        {content ? (
          <div style={{ whiteSpace: 'pre-wrap' }}>{content}</div>
        ) : isStreaming ? (
          <div className="copilot-streaming">
            <span className="copilot-streaming-dot"></span>
            <span className="copilot-streaming-dot"></span>
            <span className="copilot-streaming-dot"></span>
          </div>
        ) : null}

        {/* Sources */}
        {sources && sources.length > 0 && (
          <div className="copilot-sources">
            <div className="copilot-sources-label">
              <i className="bi bi-info-circle me-1"></i>
              Sources ({sources.length}):
            </div>
            <div className="sources-list">
              {sources.map((source, index) => (
                <div key={index} className="source-item">
                  <div
                    className={`copilot-source-badge ${source.confidence}`}
                    onClick={() => toggleSource(index)}
                    style={{ cursor: 'pointer' }}
                    title="Click to expand details"
                  >
                    <i className={`${getSourceIcon(source.source_type)} me-1`}></i>
                    <span>{source.source_type.replace('_', ' ')}</span>
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
      </div>
    </div>
  )
}

export default Message
