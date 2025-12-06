import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DocumentUploadModal from '@/components/chat/DocumentUploadModal'
import { createRef } from 'react'

describe('DocumentUploadModal', () => {
  const fileInputRef = createRef<HTMLInputElement>()

  const defaultProps = {
    show: true,
    onHide: vi.fn(),
    onUpload: vi.fn(),
    isUploading: false,
    uploadProgress: 0,
    error: null,
    fileInputRef,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should not render when show is false', () => {
    render(<DocumentUploadModal {...defaultProps} show={false} />)
    
    expect(screen.queryByText('Upload Document')).not.toBeInTheDocument()
  })

  it('should render modal when show is true', () => {
    render(<DocumentUploadModal {...defaultProps} />)
    
    expect(screen.getByText('Upload Document')).toBeInTheDocument()
  })

  it('should render cloud upload icon in title', () => {
    const { container } = render(<DocumentUploadModal {...defaultProps} />)
    
    const modal = within(document.body)
    const title = modal.getByText('Upload Document')
    const icon = title.parentElement?.querySelector('.bi-cloud-upload')
    expect(icon).toBeInTheDocument()
  })

  it('should render file input with correct accept attribute', () => {
    render(<DocumentUploadModal {...defaultProps} />)
    
    const fileInput = document.body.querySelector('input[type="file"]')
    expect(fileInput).toHaveAttribute('accept', '.pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.md,.html,.htm,.txt,.jpg,.jpeg,.png,.bmp,.tiff,.heif')
  })

  it('should display supported formats text', () => {
    render(<DocumentUploadModal {...defaultProps} />)
    
    expect(screen.getByText(/Supported formats: PDF, Word, Excel, PowerPoint, Markdown, HTML, Text, Images/i)).toBeInTheDocument()
  })

  it('should render Cancel button', () => {
    render(<DocumentUploadModal {...defaultProps} />)
    
    const cancelButton = screen.getByRole('button', { name: /Cancel/i })
    expect(cancelButton).toBeInTheDocument()
  })

  it('should render Upload button', () => {
    render(<DocumentUploadModal {...defaultProps} />)
    
    const uploadButton = screen.getByRole('button', { name: /^Upload$/i })
    expect(uploadButton).toBeInTheDocument()
  })

  it('should call onHide when Cancel button clicked', async () => {
    const user = userEvent.setup()
    const mockOnHide = vi.fn()
    
    render(<DocumentUploadModal {...defaultProps} onHide={mockOnHide} />)
    
    const cancelButton = screen.getByRole('button', { name: /Cancel/i })
    await user.click(cancelButton)
    
    expect(mockOnHide).toHaveBeenCalledTimes(1)
  })

  it('should disable file input when uploading', () => {
    render(<DocumentUploadModal {...defaultProps} isUploading={true} />)
    
    const fileInput = document.body.querySelector('input[type="file"]')
    expect(fileInput).toBeDisabled()
  })

  it('should disable Cancel button when uploading', () => {
    render(<DocumentUploadModal {...defaultProps} isUploading={true} />)
    
    const cancelButton = screen.getByRole('button', { name: /Cancel/i })
    expect(cancelButton).toBeDisabled()
  })

  it('should disable Upload button when uploading', () => {
    render(<DocumentUploadModal {...defaultProps} isUploading={true} />)
    
    const uploadButton = screen.getByRole('button', { name: /Uploading.../i })
    expect(uploadButton).toBeDisabled()
  })

  it('should show "Uploading..." text on button when uploading', () => {
    render(<DocumentUploadModal {...defaultProps} isUploading={true} />)
    
    expect(screen.getByRole('button', { name: /Uploading.../i })).toBeInTheDocument()
  })

  it('should render error alert when error exists', () => {
    render(<DocumentUploadModal {...defaultProps} error="Upload failed" />)
    
    expect(screen.getByText('Upload failed')).toBeInTheDocument()
  })

  it('should render error alert with danger variant', () => {
    const { container } = render(<DocumentUploadModal {...defaultProps} error="Upload failed" />)
    
    const alert = document.body.querySelector('.alert-danger')
    expect(alert).toBeInTheDocument()
  })

  it('should render error icon in alert', () => {
    const { container } = render(<DocumentUploadModal {...defaultProps} error="Upload failed" />)
    
    const icon = document.body.querySelector('.bi-exclamation-triangle')
    expect(icon).toBeInTheDocument()
  })

  it('should not render error alert when no error', () => {
    render(<DocumentUploadModal {...defaultProps} error={null} />)
    
    const alert = document.body.querySelector('.alert-danger')
    expect(alert).not.toBeInTheDocument()
  })

  it('should render progress bar when uploading', () => {
    const { container } = render(<DocumentUploadModal {...defaultProps} isUploading={true} uploadProgress={50} />)
    
    const progressBar = document.body.querySelector('.progress-bar')
    expect(progressBar).toBeInTheDocument()
  })

  it('should display upload progress percentage', () => {
    render(<DocumentUploadModal {...defaultProps} isUploading={true} uploadProgress={75} />)
    
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('should not render progress bar when not uploading', () => {
    const { container } = render(<DocumentUploadModal {...defaultProps} isUploading={false} />)
    
    const progressBar = document.body.querySelector('.progress-bar')
    expect(progressBar).not.toBeInTheDocument()
  })

  it('should render modal with centered prop', () => {
    const { container } = render(<DocumentUploadModal {...defaultProps} />)
    
    const modal = document.body.querySelector('.modal')
    expect(modal).toBeInTheDocument()
  })

  it('should render close button in header', () => {
    render(<DocumentUploadModal {...defaultProps} />)
    
    const closeButton = document.body.querySelector('.btn-close')
    expect(closeButton).toBeInTheDocument()
  })

  it('should have proper form structure', () => {
    render(<DocumentUploadModal {...defaultProps} />)
    
    const form = document.body.querySelector('form')
    expect(form).toBeInTheDocument()
  })

  it('should render file input label', () => {
    render(<DocumentUploadModal {...defaultProps} />)
    
    expect(screen.getByText('Select a document to upload')).toBeInTheDocument()
  })
})
