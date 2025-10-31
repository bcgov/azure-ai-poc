import type { FC } from 'react'
import { Button } from 'react-bootstrap'
import EmptyState from '../common/EmptyState'

interface ChatEmptyStateProps {
  documentsCount: number
  onUploadClick: () => void
}

const ChatEmptyState: FC<ChatEmptyStateProps> = ({
  documentsCount,
  onUploadClick,
}) => {
  if (documentsCount === 0) {
    return (
      <EmptyState
        icon="bi bi-cloud-upload"
        title="Get Started with Document Q&A"
        description="Upload your first document to start asking questions and getting AI-powered answers."
      >
        <Button
          variant="primary"
          onClick={onUploadClick}
          className="mb-3"
          style={{
            borderRadius: '0.75rem',
            fontWeight: '600',
            padding: '0.5rem 1.5rem',
          }}
        >
          <i className="bi bi-cloud-upload me-2"></i>
          Upload Your First Document
        </Button>
        <p className="text-muted small mb-0">
          Supported formats:{' '}
          <span className="badge bg-secondary mx-1">
            <i className="bi bi-file-pdf me-1"></i>PDF
          </span>
          <span className="badge bg-secondary mx-1">
            <i className="bi bi-file-text me-1"></i>Markdown
          </span>
          <span className="badge bg-secondary mx-1">
            <i className="bi bi-file-code me-1"></i>HTML
          </span>
        </p>
      </EmptyState>
    )
  }

  return (
    <EmptyState
      icon="bi bi-chat-quote"
      title="Welcome to AI Document Assistant"
      description="Upload documents (PDF, Markdown, or HTML) and ask questions about them, or search across all your uploaded documents."
    />
  )
}

export default ChatEmptyState
