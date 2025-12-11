import type { FC } from 'react'
import { useRef, useEffect, useState } from 'react'
import { speechRecognitionService } from '@/services/speechService'

// Available models for the dropdown
const MODELS = [
  { id: 'gpt-4o-mini', name: 'GPT-4o mini' },
  { id: 'gpt-41-nano', name: 'GPT-4.1 Nano' },
] as const

type ModelId = (typeof MODELS)[number]['id']

interface InputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  isLoading: boolean
  placeholder?: string
  onUploadClick?: () => void
  selectedDocument?: string | null
  selectedDocumentName?: string | null
  onClearDocument?: () => void
  deepResearchEnabled?: boolean
  onDeepResearchChange?: (enabled: boolean) => void
  selectedModel?: ModelId
  onModelChange?: (model: ModelId) => void
}

const Input: FC<InputProps> = ({
  value,
  onChange,
  onSubmit,
  isLoading,
  placeholder = 'Ask anything',
  onUploadClick,
  selectedDocument,
  selectedDocumentName,
  onClearDocument,
  deepResearchEnabled = false,
  onDeepResearchChange,
  selectedModel = 'gpt-4o-mini',
  onModelChange,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [showResearchInfo, setShowResearchInfo] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(false)
  const [useAzureSpeech, setUseAzureSpeech] = useState(false)
  const [showModelDropdown, setShowModelDropdown] = useState(false)

  useEffect(() => {
    // Check if speech recognition is supported
    setSpeechSupported(speechRecognitionService.isSupported())
  }, [])

  // Handle escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showResearchInfo) {
        setShowResearchInfo(false)
      }
    }
    if (showResearchInfo) {
      document.addEventListener('keydown', handleEscape)
    }
    return () => document.removeEventListener('keydown', handleEscape)
  }, [showResearchInfo])

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

  const handleVoiceInput = async () => {
    if (isListening) {
      if (useAzureSpeech) {
        await speechRecognitionService.stopListeningAzure(
          (result) => onChange(result.transcript),
          undefined,
          'en-US'
        )
      } else {
        speechRecognitionService.stopListening()
      }
      setIsListening(false)
      return
    }

    if (useAzureSpeech) {
      const started = await speechRecognitionService.startListeningAzure(
        (result) => {
          onChange(result.transcript)
          if (result.isFinal) setIsListening(false)
        },
        () => setIsListening(false),
        'en-US'
      )
      setIsListening(started)
    } else {
      const started = speechRecognitionService.startListening(
        (result) => {
          onChange(result.transcript)
          if (result.isFinal) setIsListening(false)
        },
        () => setIsListening(false),
        'en-US'
      )
      setIsListening(started)
    }
  }

  return (
    <div className="copilot-input-area">
      {/* Deep Research Info Modal */}
      {showResearchInfo && (
        <div 
          onClick={() => setShowResearchInfo(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'linear-gradient(135deg, #003366 0%, #1a5a96 100%)',
              borderRadius: '1rem',
              padding: '1.5rem 2rem',
              color: 'white',
              fontSize: '0.9rem',
              boxShadow: '0 8px 32px rgba(0, 51, 102, 0.4)',
              maxWidth: '500px',
              width: '90%',
              position: 'relative',
            }}
          >
            <button
              onClick={() => setShowResearchInfo(false)}
              style={{
                position: 'absolute',
                top: '1rem',
                right: '1rem',
                background: 'rgba(255,255,255,0.2)',
                border: 'none',
                borderRadius: '50%',
                width: '28px',
                height: '28px',
                color: 'white',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              title="Close (Esc)"
            >
              <i className="bi bi-x-lg"></i>
            </button>
            <div style={{ fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.1rem' }}>
              <i className="bi bi-search-heart"></i>
              About Deep Research
            </div>
            <p style={{ margin: '0 0 1rem 0', opacity: 0.95, lineHeight: 1.6 }}>
              Deep Research uses an AI-powered multi-phase workflow for comprehensive analysis:
            </p>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', opacity: 0.9, lineHeight: 1.8 }}>
              <li><strong>Web Search:</strong> Fetches <em>current data</em> from the internet for up-to-date information</li>
              <li><strong>Planning:</strong> Creates a research plan with questions and methodology</li>
              <li><strong>Research:</strong> Gathers findings on each subtopic with confidence levels</li>
              <li><strong>Synthesis:</strong> Produces a comprehensive report with citations & source URLs</li>
            </ul>
            <p style={{ margin: '1rem 0 0 0', opacity: 0.85, fontSize: '0.8rem' }}>
              <i className="bi bi-globe me-1"></i>
              Goes outbound to the web for current data, ensuring results are up-to-date.
            </p>
            <p style={{ margin: '0.75rem 0 0 0', opacity: 0.6, fontSize: '0.75rem', textAlign: 'center' }}>
              Press <kbd style={{ background: 'rgba(255,255,255,0.2)', padding: '0.125rem 0.375rem', borderRadius: '0.25rem' }}>Esc</kbd> to close
            </p>
          </div>
        </div>
      )}
      <div className="copilot-input-wrapper" style={{ position: 'relative' }}>
        <textarea
          ref={textareaRef}
          className="copilot-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isListening ? 'Listening...' : (deepResearchEnabled ? 'Ask a research question...' : placeholder)}
          disabled={isLoading || isListening}
          rows={1}
          style={{
            paddingRight: value.trim() && !isLoading ? '3rem' : undefined,
          }}
        />
        {value.trim() && !isLoading && (
          <button
            type="button"
            onClick={() => onChange('')}
            style={{
              position: 'absolute',
              right: '0.75rem',
              top: '50%',
              transform: 'translateY(-50%)',
              background: 'transparent',
              border: 'none',
              color: '#656d76',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '0.25rem',
              borderRadius: '50%',
              width: '1.5rem',
              height: '1.5rem',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#f0f0f0'
              e.currentTarget.style.color = '#333'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = '#656d76'
            }}
            title="Clear text"
          >
            <i className="bi bi-x-lg" style={{ fontSize: '0.875rem' }}></i>
          </button>
        )}
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
            {selectedDocument && selectedDocumentName && (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.375rem',
                padding: '0.35rem 0.75rem',
                background: 'linear-gradient(135deg, #003366 0%, #1a5a96 100%)',
                border: 'none',
                borderRadius: '1rem',
                fontSize: '0.8rem',
                color: 'white',
                fontWeight: 500,
                maxWidth: '200px',
              }}>
                <i className="bi bi-file-text" style={{ flexShrink: 0 }}></i>
                <span style={{ 
                  overflow: 'hidden', 
                  textOverflow: 'ellipsis', 
                  whiteSpace: 'nowrap' 
                }}>
                  {selectedDocumentName}
                </span>
                {onClearDocument && (
                  <button
                    type="button"
                    onClick={onClearDocument}
                    title="Clear document selection"
                    style={{
                      background: 'none',
                      border: 'none',
                      padding: '0.125rem',
                      cursor: 'pointer',
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '50%',
                      flexShrink: 0,
                    }}
                  >
                    <i className="bi bi-x-lg" style={{ fontSize: '0.625rem' }}></i>
                  </button>
                )}
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
                    outline: 'none',
                  }}
                  title="Learn about Deep Research"
                >
                  <i className="bi bi-info-circle"></i>
                </button>
              </div>
            )}
          </div>
          <div className="copilot-input-right">
            {speechSupported && (
              <button
                type="button"
                onClick={handleVoiceInput}
                disabled={isLoading}
                style={{
                  background: isListening ? '#dc3545' : 'transparent',
                  border: isListening ? 'none' : '1px solid #d0d7de',
                  borderRadius: '50%',
                  width: '2.25rem',
                  height: '2.25rem',
                  color: isListening ? 'white' : '#656d76',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.2s ease',
                  marginRight: '0.5rem',
                }}
                title={isListening ? 'Stop listening' : 'Voice input'}
              >
                <i 
                  className={`bi ${isListening ? 'bi-mic-fill' : 'bi-mic'}`}
                  style={{
                    fontSize: '1rem',
                    animation: isListening ? 'pulse 1s infinite' : 'none',
                  }}
                ></i>
              </button>
            )}
            <div 
              className="copilot-model-select"
              onClick={() => setShowModelDropdown(!showModelDropdown)}
              style={{ position: 'relative', cursor: 'pointer' }}
            >
              {MODELS.find((m) => m.id === selectedModel)?.name || 'GPT-4o mini'}
              <i className="bi bi-chevron-down"></i>
              {showModelDropdown && (
                <div
                  style={{
                    position: 'absolute',
                    bottom: '100%',
                    right: 0,
                    marginBottom: '0.5rem',
                    background: 'white',
                    borderRadius: '0.5rem',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                    overflow: 'hidden',
                    minWidth: '140px',
                    zIndex: 1000,
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {MODELS.map((model) => (
                    <div
                      key={model.id}
                      onClick={() => {
                        onModelChange?.(model.id)
                        setShowModelDropdown(false)
                      }}
                      style={{
                        padding: '0.5rem 0.75rem',
                        cursor: 'pointer',
                        background: selectedModel === model.id ? '#f0f4ff' : 'transparent',
                        color: selectedModel === model.id ? '#003366' : '#333',
                        fontWeight: selectedModel === model.id ? 600 : 400,
                        fontSize: '0.85rem',
                        transition: 'background 0.15s ease',
                      }}
                      onMouseEnter={(e) => {
                        if (selectedModel !== model.id) {
                          e.currentTarget.style.background = '#f5f5f5'
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background =
                          selectedModel === model.id ? '#f0f4ff' : 'transparent'
                      }}
                    >
                      {model.name}
                    </div>
                  ))}
                </div>
              )}
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
