import type { FC } from 'react'
import { Badge, Card } from 'react-bootstrap'

interface ChatMessageProps {
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  documentId?: string
  documentName?: string
  getFileIcon: (filename: string) => string
}

const ChatMessage: FC<ChatMessageProps> = ({
  type,
  content,
  timestamp,
  documentId,
  documentName,
  getFileIcon,
}) => {
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
                  style={{ fontSize: '1.1em' }}
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
