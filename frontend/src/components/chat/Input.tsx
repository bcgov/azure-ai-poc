import type { FC } from 'react'
import { useRef, useEffect, useState } from 'react'

interface InputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  isLoading: boolean
  placeholder?: string
  onUploadClick?: () => void
  selectedDocument?: string | null
  deepResearchEnabled?: boolean
  onDeepResearchChange?: (enabled: boolean) => void
}

const Input: FC<InputProps> = ({
  value,
  onChange,
  onSubmit,
  isLoading,
  placeholder = 'Ask anything',
  onUploadClick,
  selectedDocument,
  deepResearchEnabled = false,
  onDeepResearchChange,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [showResearchInfo, setShowResearchInfo] = useState(false)

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
      {/* Deep Research Info Panel */}
      {showResearchInfo && (
        <div 
          style={{
            background: 'linear-gradient(135deg, #003366 0%, #1a5a96 100%)',
            borderRadius: '0.75rem',
            padding: '1rem 1.25rem',
            marginBottom: '0.75rem',
            color: 'white',
            fontSize: '0.875rem',
            boxShadow: '0 4px 15px rgba(0, 51, 102, 0.3)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <i className="bi bi-search-heart"></i>
                About Deep Research
              </div>
              <p style={{ margin: '0 0 0.75rem 0', opacity: 0.95, lineHeight: 1.5 }}>
                Deep Research uses an AI-powered multi-phase workflow for comprehensive analysis:
              </p>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', opacity: 0.9, lineHeight: 1.6 }}>
                <li><strong>Planning:</strong> Creates a research plan with questions and methodology</li>
                <li><strong>Research:</strong> Gathers findings on each subtopic with confidence levels</li>
                <li><strong>Synthesis:</strong> Produces a comprehensive report with conclusions</li>
              </ul>
              <p style={{ margin: '0.75rem 0 0 0', opacity: 0.85, fontSize: '0.8rem' }}>
                <i className="bi bi-clock me-1"></i>
                Takes 30-60 seconds for thorough, well-structured answers.
              </p>
            </div>
            <button
              onClick={() => setShowResearchInfo(false)}
              style={{
                background: 'rgba(255,255,255,0.2)',
                border: 'none',
                borderRadius: '50%',
                width: '24px',
                height: '24px',
                color: 'white',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <i className="bi bi-x"></i>
            </button>
          </div>
        </div>
      )}
      <div className="copilot-input-wrapper">
        <textarea
          ref={textareaRef}
          className="copilot-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={deepResearchEnabled ? 'Ask a research question...' : placeholder}
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
            {onDeepResearchChange && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => onDeepResearchChange(!deepResearchEnabled)}
                  style={{
                    background: deepResearchEnabled 
                      ? 'linear-gradient(135deg, #003366 0%, #1a5a96 100%)' 
                      : 'transparent',
                    border: deepResearchEnabled ? 'none' : '1px solid #d0d7de',
                    borderRadius: '1rem',
                    padding: '0.35rem 0.75rem',
                    fontSize: '0.8rem',
                    color: deepResearchEnabled ? 'white' : '#656d76',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.375rem',
                    transition: 'all 0.2s ease',
                    fontWeight: deepResearchEnabled ? 500 : 400,
                  }}
                  title={deepResearchEnabled ? 'Deep Research enabled' : 'Enable Deep Research'}
                >
                  <i className={`bi ${deepResearchEnabled ? 'bi-search-heart-fill' : 'bi-search-heart'}`}></i>
                  Deep Research
                </button>
                <button
                  type="button"
                  onClick={() => setShowResearchInfo(!showResearchInfo)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    padding: '0.25rem',
                    color: '#656d76',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  title="Learn about Deep Research"
                >
                  <i className="bi bi-info-circle"></i>
                </button>
              </div>
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
