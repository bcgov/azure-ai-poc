import type { FC } from 'react'
import { useRef, useEffect } from 'react'

interface InputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  isLoading: boolean
  placeholder?: string
  onUploadClick?: () => void
  selectedDocument?: string | null
}

const Input: FC<InputProps> = ({
  value,
  onChange,
  onSubmit,
  isLoading,
  placeholder = 'Ask anything',
  onUploadClick,
  selectedDocument,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const newHeight = Math.min(textareaRef.current.scrollHeight, 200)
      textareaRef.current.style.height = `${newHeight}px`
    }
  }, [value])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim() && !isLoading) {
        onSubmit()
      }
    }
  }

  const handleSubmit = () => {
    if (value.trim() && !isLoading) {
      onSubmit()
    }
  }

  return (
    <div className="copilot-input-area">
      <div className="copilot-input-wrapper">
        <textarea
          ref={textareaRef}
          className="copilot-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading}
          rows={1}
        />
        <div className="copilot-input-controls">
          <div className="copilot-input-left">
            {onUploadClick && (
              <button
                type="button"
                className="copilot-icon-btn"
                onClick={onUploadClick}
                title="Add files"
              >
                <i className="bi bi-plus-lg"></i>
                Add files
              </button>
            )}
            {selectedDocument && (
              <span className="copilot-attachment">
                <i className="bi bi-file-text"></i>
                Document selected
              </span>
            )}
          </div>
          <div className="copilot-input-right">
            <div className="copilot-model-select">
              GPT-4o mini
              <i className="bi bi-chevron-down"></i>
            </div>
            <button
              type="button"
              className={`copilot-send-btn ${value.trim() ? 'ready' : ''}`}
              onClick={handleSubmit}
              disabled={!value.trim() || isLoading}
              title="Send message"
            >
              {isLoading ? (
                <i className="bi bi-hourglass-split"></i>
              ) : (
                <i className="bi bi-send"></i>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Input
