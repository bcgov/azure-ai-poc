/**
 * Speech Service - Text-to-Speech and Speech-to-Text functionality
 */

import httpClient from '@/services/httpClient'

// Available TTS voices
export const TTS_VOICES = {
  'en-CA-female': 'Clara (Canadian English, Female)',
  'en-CA-male': 'Liam (Canadian English, Male)',
  'en-US-female': 'Jenny (US English, Female)',
  'en-US-male': 'Guy (US English, Male)',
  'en-GB-female': 'Sonia (British English, Female)',
  'en-GB-male': 'Ryan (British English, Male)',
} as const

export type VoiceId = keyof typeof TTS_VOICES

interface SpeechHealthResponse {
  status: 'healthy' | 'not_configured'
  service: string
}

interface VoicesResponse {
  voices: Record<string, string>
}

class SpeechService {
  private audioElement: HTMLAudioElement | null = null
  private currentAudioUrl: string | null = null
  private isPlaying = false

  /**
   * Check if the speech service is available
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await httpClient.get<SpeechHealthResponse>('/api/v1/speech/health')
      return response.data.status === 'healthy'
    } catch {
      return false
    }
  }

  /**
   * Get available TTS voices from the backend
   */
  async getVoices(): Promise<Record<string, string>> {
    try {
      const response = await httpClient.get<VoicesResponse>('/api/v1/speech/voices')
      return response.data.voices
    } catch {
      return TTS_VOICES
    }
  }

  /**
   * Convert text to speech and return audio blob
   */
  async textToSpeech(text: string, voice: VoiceId = 'en-CA-female'): Promise<Blob | null> {
    try {
      const response = await httpClient.post(
        '/api/v1/speech/tts',
        { text, voice },
        { responseType: 'blob' }
      )
      return response.data as Blob
    } catch (error) {
      console.error('TTS error:', error)
      return null
    }
  }

  /**
   * Play text as speech
   */
  async speak(text: string, voice: VoiceId = 'en-CA-female'): Promise<void> {
    // Stop any current playback
    this.stop()

    const audioBlob = await this.textToSpeech(text, voice)
    if (!audioBlob) {
      throw new Error('Failed to generate speech')
    }

    // Create audio URL and play
    this.currentAudioUrl = URL.createObjectURL(audioBlob)
    this.audioElement = new Audio(this.currentAudioUrl)
    this.isPlaying = true

    return new Promise((resolve, reject) => {
      if (!this.audioElement) {
        reject(new Error('Audio element not created'))
        return
      }

      this.audioElement.onended = () => {
        this.cleanup()
        resolve()
      }

      this.audioElement.onerror = () => {
        this.cleanup()
        reject(new Error('Audio playback error'))
      }

      this.audioElement.play().catch((e) => {
        this.cleanup()
        reject(e)
      })
    })
  }

  /**
   * Stop current audio playback
   */
  stop(): void {
    if (this.audioElement) {
      this.audioElement.pause()
      this.audioElement.currentTime = 0
    }
    this.cleanup()
  }

  /**
   * Check if audio is currently playing
   */
  getIsPlaying(): boolean {
    return this.isPlaying
  }

  /**
   * Cleanup audio resources
   */
  private cleanup(): void {
    if (this.currentAudioUrl) {
      URL.revokeObjectURL(this.currentAudioUrl)
      this.currentAudioUrl = null
    }
    this.audioElement = null
    this.isPlaying = false
  }
}

// Singleton instance
export const speechService = new SpeechService()

// ============ Speech-to-Text (STT) using Web Speech API ============

// Web Speech API type definitions
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
}

interface SpeechRecognitionResultList {
  length: number
  item(index: number): SpeechRecognitionResult
  [index: number]: SpeechRecognitionResult
}

interface SpeechRecognitionResult {
  isFinal: boolean
  length: number
  item(index: number): SpeechRecognitionAlternative
  [index: number]: SpeechRecognitionAlternative
}

interface SpeechRecognitionAlternative {
  transcript: string
  confidence: number
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string
  message: string
}

interface WebSpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
  abort(): void
}

interface WebSpeechRecognitionConstructor {
  new (): WebSpeechRecognition
}

export interface SpeechRecognitionResultOutput {
  transcript: string
  isFinal: boolean
}

export type SpeechRecognitionCallback = (result: SpeechRecognitionResultOutput) => void
export type SpeechRecognitionErrorCallback = (error: string) => void

class SpeechRecognitionService {
  private recognition: WebSpeechRecognition | null = null
  private isListening = false

  /**
   * Check if speech recognition is supported
   */
  isSupported(): boolean {
    return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window
  }

  /**
   * Start listening for speech input
   */
  startListening(
    onResult: SpeechRecognitionCallback,
    onError?: SpeechRecognitionErrorCallback,
    language: string = 'en-CA'
  ): boolean {
    if (!this.isSupported()) {
      onError?.('Speech recognition is not supported in this browser')
      return false
    }

    if (this.isListening) {
      this.stopListening()
    }

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const SpeechRecognitionClass = (window as any).SpeechRecognition || 
        (window as any).webkitSpeechRecognition as WebSpeechRecognitionConstructor
      
      const recognition = new SpeechRecognitionClass()
      this.recognition = recognition

      recognition.continuous = false
      recognition.interimResults = true
      recognition.lang = language

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const result = event.results[event.results.length - 1]
        onResult({
          transcript: result[0].transcript,
          isFinal: result.isFinal,
        })
      }

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.error('Speech recognition error:', event.error)
        this.isListening = false
        
        let errorMessage = 'Speech recognition error'
        switch (event.error) {
          case 'not-allowed':
            errorMessage = 'Microphone access denied. Please allow microphone access.'
            break
          case 'no-speech':
            errorMessage = 'No speech detected. Please try again.'
            break
          case 'audio-capture':
            errorMessage = 'No microphone found. Please check your microphone.'
            break
          case 'network':
            errorMessage = 'Network error. Please check your connection.'
            break
        }
        onError?.(errorMessage)
      }

      recognition.onend = () => {
        this.isListening = false
      }

      recognition.start()
      this.isListening = true
      return true
    } catch (error) {
      console.error('Failed to start speech recognition:', error)
      onError?.('Failed to start speech recognition')
      return false
    }
  }

  /**
   * Stop listening for speech input
   */
  stopListening(): void {
    if (this.recognition) {
      this.recognition.stop()
      this.recognition = null
    }
    this.isListening = false
  }

  /**
   * Check if currently listening
   */
  getIsListening(): boolean {
    return this.isListening
  }
}

// Singleton instance
export const speechRecognitionService = new SpeechRecognitionService()
