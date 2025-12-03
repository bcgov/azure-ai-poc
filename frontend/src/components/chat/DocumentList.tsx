import type { FC } from 'react'
import { Button } from 'react-bootstrap'
import LoadingSpinner from '../common/LoadingSpinner'
import type { DocumentItem } from '@/services/documentService'

// Re-export DocumentItem as Document for backward compatibility
export type Document = DocumentItem

interface DocumentListProps {
  documents: Document[]
  selectedDocument: string | null
  onSelectDocument: (documentId: string | null) => void
  onDeleteDocument: (document: Document) => void
  isLoadingDocuments: boolean
  getFileIcon: (filename: string) => string
}

const DocumentList: FC<DocumentListProps> = ({
  documents,
  selectedDocument,
  onSelectDocument,
  onDeleteDocument,
  isLoadingDocuments,
  getFileIcon,
}) => {
  if (isLoadingDocuments) {
    return <LoadingSpinner size="sm" message="Loading documents..." />
  }

  if (documents.length === 0) {
    return null
  }

  return (
    <>
      <div className="d-flex flex-wrap gap-2 align-items-center mb-2">
        <small className="text-muted">Ask about:</small>
        <Button
          variant={!selectedDocument ? 'primary' : 'outline-secondary'}
          size="sm"
          onClick={() => onSelectDocument(null)}
          disabled={documents.length === 0}
        >
          Across All Docs
        </Button>
      </div>

      <div className="d-flex flex-wrap gap-2">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className={`document-chip d-flex align-items-center ${selectedDocument === doc.id ? 'selected' : ''}`}
            style={{
              backgroundColor:
                selectedDocument === doc.id
                  ? 'rgba(0, 51, 102, 0.1)'
                  : 'transparent',
              border:
                selectedDocument === doc.id
                  ? '0.125rem solid #003366'
                  : '0.125rem solid #dee2e6',
            }}
          >
            <Button
              variant={selectedDocument === doc.id ? 'primary' : 'outline-secondary'}
              size="sm"
              onClick={() => onSelectDocument(doc.id)}
              className="btn-sm d-flex align-items-center gap-1"
              style={{
                border: 'none',
                background: 'transparent',
                color: selectedDocument === doc.id ? '#003366' : '#6c757d',
                padding: '0.25rem 0.5rem',
              }}
            >
              <i className={`${getFileIcon(doc.title)}`}></i>
              <span
                className="text-truncate"
                style={{ maxWidth: '9.375rem' }}
                title={doc.title}
              >
                {doc.title}
              </span>
            </Button>
            <Button
              variant="link"
              size="sm"
              onClick={() => onDeleteDocument(doc)}
              className="p-0 ms-1 text-danger"
              style={{ minWidth: 'auto' }}
              title="Delete document"
            >
              <i className="bi bi-x-circle"></i>
            </Button>
          </div>
        ))}
      </div>
    </>
  )
}

export default DocumentList
