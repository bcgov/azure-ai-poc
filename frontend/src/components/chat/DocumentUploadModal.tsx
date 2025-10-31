import type { FC } from 'react'
import { useState } from 'react'
import { Modal, Button, Form, Alert, ProgressBar } from 'react-bootstrap'

interface DocumentUploadModalProps {
  show: boolean
  onHide: () => void
  onUpload: (file: File) => void
  isUploading: boolean
  uploadProgress: number
  error: string | null
  fileInputRef: React.RefObject<HTMLInputElement | null>
}

const DocumentUploadModal: FC<DocumentUploadModalProps> = ({
  show,
  onHide,
  onUpload,
  isUploading,
  uploadProgress,
  error,
  fileInputRef,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    setSelectedFile(file)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const file = fileInputRef.current?.files?.[0]
    if (file) {
      onUpload(file)
    }
  }

  const handleClose = () => {
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    onHide()
  }

  return (
    <Modal show={show} onHide={handleClose} centered>
      <Modal.Header closeButton>
        <Modal.Title>
          <i className="bi bi-cloud-upload me-2"></i>
          Upload Document
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3">
            <Form.Label>Select a document to upload</Form.Label>
            <Form.Control
              type="file"
              ref={fileInputRef}
              accept=".pdf,.md,.html,.htm"
              disabled={isUploading}
              onChange={handleFileChange}
            />
            <Form.Text className="text-muted">
              Supported formats: PDF, Markdown (.md), HTML
            </Form.Text>
          </Form.Group>

          {error && (
            <Alert variant="danger" className="mb-3">
              <i className="bi bi-exclamation-triangle me-2"></i>
              {error}
            </Alert>
          )}

          {isUploading && (
            <div className="mb-3">
              <div className="d-flex justify-content-between mb-1">
                <small className="text-muted">Uploading...</small>
                <small className="text-muted">{uploadProgress}%</small>
              </div>
              <ProgressBar now={uploadProgress} animated />
            </div>
          )}
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={handleClose} disabled={isUploading}>
          Cancel
        </Button>
        <Button
          variant="primary"
          onClick={handleSubmit}
          disabled={isUploading || !selectedFile}
        >
          {isUploading ? 'Uploading...' : 'Upload'}
        </Button>
      </Modal.Footer>
    </Modal>
  )
}

export default DocumentUploadModal
