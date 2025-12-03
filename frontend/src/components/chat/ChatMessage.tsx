import type { FC } from 'react'
import { Badge, Card, OverlayTrigger, Tooltip } from 'react-bootstrap'
import type { SourceInfo } from '@/services/chatAgentService'

interface ChatMessageProps {
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  documentId?: string
  documentName?: string
  getFileIcon: (filename: string) => string
  sources?: SourceInfo[]
  hasSufficientInfo?: boolean
}

const ChatMessage: FC<ChatMessageProps> = ({
  type,
  content,
  timestamp,
  documentId,
  documentName,
  getFileIcon,
  sources,
  hasSufficientInfo,
}) => {
  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getConfidenceBadgeVariant = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return 'success'
      case 'medium':
        return 'warning'
      case 'low':
        return 'danger'
      default:
        return 'secondary'
    }
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

  return (
    <div
      className={`d-flex ${
        type === 'user' ? 'justify-content-end' : 'justify-content-start'
      } mb-2 mb-md-3`}
    >
      <div
        className={`position-relative ${
          type === 'user' ? 'ms-3 ms-md-5' : 'me-3 me-md-5'
        }`}
        style={{ maxWidth: 'min(80%, 50rem)' }}
      >
        <Card
          className={`${
            type === 'user' ? 'bg-primary text-white' : 'bg-light'
          }`}
        >
          <Card.Body className="py-2 px-3">
            <div className="d-flex align-items-start">
              {type === 'assistant' && (
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
                  {content}
                </div>
                {documentId && documentName && (
                  <div className="mt-1">
                    <Badge
                      bg={type === 'user' ? 'light' : 'secondary'}
                      text={type === 'user' ? 'dark' : 'light'}
                    >
                      <i className={`${getFileIcon(documentName)} me-1`}></i>
                      {documentName}
                    </Badge>
                  </div>
                )}
                {/* Source Attribution Section */}
                {type === 'assistant' && sources && sources.length > 0 && (
                  <div className="mt-2 pt-2 border-top">
                    <small className="text-muted d-block mb-1">
                      <i className="bi bi-info-circle me-1"></i>
                      Sources ({sources.length}):
                    </small>
                    <div className="d-flex flex-wrap gap-1">
                      {sources.map((source, index) => (
                        <OverlayTrigger
                          key={index}
                          placement="top"
                          overlay={
                            <Tooltip id={`source-tooltip-${index}`}>
                              {source.description}
                              {source.url && (
                                <span className="d-block mt-1">
                                  <i className="bi bi-link-45deg me-1"></i>
                                  {source.url}
                                </span>
                              )}
                            </Tooltip>
                          }
                        >
                          <Badge
                            bg={getConfidenceBadgeVariant(source.confidence)}
                            className="cursor-pointer"
                            style={{ cursor: 'pointer' }}
                          >
                            <i className={`${getSourceIcon(source.source_type)} me-1`}></i>
                            {source.source_type.replace('_', ' ')}
                            <span className="ms-1 opacity-75">({source.confidence})</span>
                          </Badge>
                        </OverlayTrigger>
                      ))}
                    </div>
                  </div>
                )}
                {/* Insufficient Info Warning */}
                {type === 'assistant' && hasSufficientInfo === false && (
                  <div className="mt-2">
                    <Badge bg="warning" text="dark">
                      <i className="bi bi-exclamation-triangle me-1"></i>
                      Limited information available
                    </Badge>
                  </div>
                )}
                <small
                  className={`d-block mt-1 ${
                    type === 'user' ? 'text-white-50' : 'text-muted'
                  }`}
                >
                  {formatTimestamp(timestamp)}
                </small>
              </div>
              {type === 'user' && (
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
  )
}

export default ChatMessage
