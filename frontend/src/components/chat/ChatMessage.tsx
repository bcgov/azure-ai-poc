import type { FC } from 'react'
import { Badge, Card, OverlayTrigger, Tooltip } from 'react-bootstrap'
import type { SourceInfo } from '@/services/chatAgentService'
import {
  sortSourcesByConfidence,
  getSourceIcon,
  getConfidenceBadgeVariant,
  formatSourceType,
} from '@/utils/sourceUtils'

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
  // Sort sources by confidence (highest first)
  const sortedSources = sources ? sortSourcesByConfidence(sources) : []

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    })
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
                {type === 'assistant' && sortedSources && sortedSources.length > 0 && (
                  <div className="mt-2 pt-2 border-top">
                    <small className="text-muted d-block mb-1">
                      <i className="bi bi-info-circle me-1"></i>
                      Sources ({sortedSources.length}):
                    </small>
                    <div className="d-flex flex-wrap gap-1">
                      {sortedSources.slice(0, 3).map((source, index) => (
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
                            as={source.url ? 'a' : 'span'}
                            href={source.url || undefined}
                            target={source.url ? '_blank' : undefined}
                            rel={source.url ? 'noopener noreferrer' : undefined}
                          >
                            <i className={`${getSourceIcon(source.source_type)} me-1`}></i>
                            {formatSourceType(source.source_type)}
                            {source.url && <i className="bi bi-box-arrow-up-right ms-1" style={{ fontSize: '0.7em' }}></i>}
                          </Badge>
                        </OverlayTrigger>
                      ))}
                      {sortedSources.length > 3 && (
                        <Badge bg="secondary" className="opacity-75">
                          +{sortedSources.length - 3} more
                        </Badge>
                      )}
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
