import type { FC } from 'react'
import { Modal, Button, Spinner } from 'react-bootstrap'
import type { Document } from './DocumentList'

interface DocumentDeleteConfirmProps {
  show: boolean
  document: Document | null
  onConfirm: () => void
  onCancel: () => void
  isDeleting: boolean
  getFileIcon: (filename: string) => string
}

const DocumentDeleteConfirm: FC<DocumentDeleteConfirmProps> = ({
  show,
  document,
  onConfirm,
  onCancel,
  isDeleting,
  getFileIcon,
}) => {
  return (
    <Modal show={show} onHide={onCancel} centered>
      <Modal.Header closeButton>
        <Modal.Title>
          <i className="bi bi-exclamation-triangle text-warning me-2"></i>
          Confirm Delete
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div className="text-center py-3">
          <i
            className={`${
              document ? getFileIcon(document.filename) : 'bi-file-text'
            } display-4 text-danger mb-3`}
          ></i>
          <h5>Delete Document</h5>
          <p className="text-muted">
            Are you sure you want to delete "{document?.filename}"?
          </p>
          <p className="text-warning small">
            <i className="bi bi-exclamation-triangle me-1"></i>
            This action cannot be undone. The document and all associated data
            will be permanently removed.
          </p>
        </div>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onCancel} disabled={isDeleting}>
          Cancel
        </Button>
        <Button variant="danger" onClick={onConfirm} disabled={isDeleting}>
          {isDeleting ? (
            <>
              <Spinner animation="border" size="sm" className="me-2" />
              Deleting...
            </>
          ) : (
            <>
              <i className="bi bi-trash me-1"></i>
              Delete Document
            </>
          )}
        </Button>
      </Modal.Footer>
    </Modal>
  )
}

export default DocumentDeleteConfirm
