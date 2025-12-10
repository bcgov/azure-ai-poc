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
   * Convert text to speech and stream audio in real-time
   */
  async textToSpeechStream(text: string, voice: VoiceId = 'en-CA-female'): Promise<Blob | null> {
    try {
      const response = await httpClient.post(
        '/api/v1/speech/tts/stream',
        { text, voice },
        { responseType: 'blob' }
      )

      console.log('TTS stream started:', {
        status: response.status,
        blobSize: response.data.size,
        contentType: response.headers['content-type']
      })

      return response.data as Blob
    } catch (error) {
      console.error('TTS stream error:', error)
      return null
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
      
      const blob = response.data as Blob
      console.log('TTS response:', {
        blobSize: blob.size,
        blobType: blob.type,
        status: response.status
      })
      
      if (blob.size === 0) {
        console.error('TTS returned empty blob')
        return null
      }
      
      return blob
    } catch (error) {
      console.error('TTS error:', error)
      return null
    }
  }

  /**
   * Play text as speech (using streaming endpoint)
   */
  async speak(text: string, voice: VoiceId = 'en-CA-female'): Promise<void> {
    // Stop any current playback
    this.stop()

    const audioBlob = await this.textToSpeechStream(text, voice)
    if (!audioBlob) {
      throw new Error('Failed to generate speech')
    }

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

      this.audioElement.onerror = (e) => {
        console.error('Audio playback error:', e)
        this.cleanup()
        reject(new Error('Audio playback error'))
      }

      this.audioElement.play().catch((e) => {
        console.error('Audio play() failed:', e)
        this.cleanup()
        reject(e)
      })
    })
  }

  /**
   * Convert speech to text using Azure Speech Services
   */
  async speechToText(audioBlob: Blob, language: string = 'en-US'): Promise<string | null> {
    try {
      // Convert blob to base64
      const arrayBuffer = await audioBlob.arrayBuffer()
      const base64Audio = btoa(
        new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
      )

      const response = await httpClient.post<{ text: string; language: string }>(
        '/api/v1/speech/stt',
        {
          audio_data: base64Audio,
          language,
        }
      )

      console.log('STT response:', {
        textLength: response.data.text.length,
        language: response.data.language,
      })

      return response.data.text
    } catch (error) {
      console.error('STT error:', error)
      return null
    }
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

/**
 * Audio recording service for capturing microphone input
 */
class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null
  private audioChunks: Blob[] = []
  private stream: MediaStream | null = null

  /**
   * Start recording audio from microphone
   */
  async startRecording(): Promise<boolean> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: 'audio/webm',
      })

      this.audioChunks = []

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data)
        }
      }

      this.mediaRecorder.start()
      console.log('Audio recording started')
      return true
    } catch (error) {
      console.error('Failed to start audio recording:', error)
      return false
    }
  }

  /**
   * Stop recording and return audio blob converted to WAV format
   */
  async stopRecording(): Promise<Blob | null> {
    return new Promise((resolve) => {
      if (!this.mediaRecorder) {
        resolve(null)
        return
      }

      this.mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' })
        
        // Convert WebM to WAV format for Azure Speech Service
        try {
          const wavBlob = await this.convertToWav(audioBlob)
          this.cleanup()
          resolve(wavBlob)
        } catch (error) {
          console.error('Failed to convert audio to WAV:', error)
          this.cleanup()
          resolve(audioBlob) // Fallback to original blob
        }
      }

      this.mediaRecorder.stop()
    })
  }

  /**
   * Convert audio blob to WAV format
   */
  private async convertToWav(blob: Blob): Promise<Blob> {
    const audioContext = new AudioContext({ sampleRate: 16000 })
    const arrayBuffer = await blob.arrayBuffer()
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
    
    // Convert to mono if stereo
    const channelData = audioBuffer.numberOfChannels === 1 
      ? audioBuffer.getChannelData(0)
      : this.mergeChannels(audioBuffer)
    
    // Create WAV file
    const wavBuffer = this.encodeWav(channelData, audioBuffer.sampleRate)
    await audioContext.close()
    
    return new Blob([wavBuffer], { type: 'audio/wav' })
  }

  /**
   * Merge stereo channels to mono
   */
  private mergeChannels(audioBuffer: AudioBuffer): Float32Array {
    const left = audioBuffer.getChannelData(0)
    const right = audioBuffer.getChannelData(1)
    const mono = new Float32Array(left.length)
    
    for (let i = 0; i < left.length; i++) {
      mono[i] = (left[i] + right[i]) / 2
    }
    
    return mono
  }

  /**
   * Encode Float32Array to WAV format
   */
  private encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
    const buffer = new ArrayBuffer(44 + samples.length * 2)
    const view = new DataView(buffer)

    // WAV header
    const writeString = (offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i))
      }
    }

    writeString(0, 'RIFF')
    view.setUint32(4, 36 + samples.length * 2, true)
    writeString(8, 'WAVE')
    writeString(12, 'fmt ')
    view.setUint32(16, 16, true) // PCM format
    view.setUint16(20, 1, true) // PCM
    view.setUint16(22, 1, true) // Mono
    view.setUint32(24, sampleRate, true)
    view.setUint32(28, sampleRate * 2, true) // Byte rate
    view.setUint16(32, 2, true) // Block align
    view.setUint16(34, 16, true) // Bits per sample
    writeString(36, 'data')
    view.setUint32(40, samples.length * 2, true)

    // Convert float samples to 16-bit PCM
    const offset = 44
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]))
      view.setInt16(offset + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    }

    return buffer
  }

  /**
   * Check if currently recording
   */
  isRecording(): boolean {
    return this.mediaRecorder?.state === 'recording'
  }

  /**
   * Cleanup resources
   */
  private cleanup(): void {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop())
      this.stream = null
    }
    this.mediaRecorder = null
    this.audioChunks = []
  }
}

class SpeechRecognitionService {
  private recognition: WebSpeechRecognition | null = null
  private isListening = false
  private audioRecorder: AudioRecorder = new AudioRecorder()
  private useAzureBackend = false
  private silenceTimer: number | null = null
  private silenceDetectionTimeout = 4500 // 4.5 seconds of silence
  private audioContext: AudioContext | null = null
  private analyser: AnalyserNode | null = null
  private silenceThreshold = -50 // dB threshold for silence detection

  /**
   * Check if speech recognition is supported
   */
  isSupported(): boolean {
    return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window
  }

  /**
   * Set whether to use Azure backend for STT
   */
  setUseAzureBackend(useAzure: boolean): void {
    this.useAzureBackend = useAzure
  }

  /**
   * Start listening for speech input (Web Speech API)
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
   * Start listening for speech input using Azure backend
   */
  async startListeningAzure(
    onResult: SpeechRecognitionCallback,
    onError?: SpeechRecognitionErrorCallback,
    language: string = 'en-US'
  ): Promise<boolean> {
    if (this.isListening) {
      await this.stopListeningAzure()
    }

    const started = await this.audioRecorder.startRecording()
    if (!started) {
      onError?.('Failed to access microphone')
      return false
    }

    this.isListening = true

    // Set up audio context for silence detection
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      this.audioContext = new AudioContext()
      const source = this.audioContext.createMediaStreamSource(stream)
      this.analyser = this.audioContext.createAnalyser()
      this.analyser.fftSize = 2048
      this.analyser.smoothingTimeConstant = 0.8
      source.connect(this.analyser)

      // Start monitoring for silence
      this.startSilenceDetection(async () => {
        console.log('Silence detected, stopping recording')
        if (this.isListening) {
          const audioBlob = await this.audioRecorder.stopRecording()
          this.isListening = false
          this.cleanupSilenceDetection()

          if (audioBlob) {
            const text = await speechService.speechToText(audioBlob, language)
            if (text) {
              onResult({
                transcript: text,
                isFinal: true,
              })
            } else {
              onError?.('Failed to recognize speech')
            }
          }
        }
      })
    } catch (error) {
      console.error('Failed to set up silence detection:', error)
      // Continue without silence detection as fallback
    }

    return true
  }

  /**
   * Start monitoring audio levels for silence detection
   */
  private startSilenceDetection(onSilence: () => void): void {
    if (!this.analyser) return

    const bufferLength = this.analyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    let isSilent = false

    const checkAudioLevel = () => {
      if (!this.analyser || !this.isListening) return

      this.analyser.getByteFrequencyData(dataArray)
      
      // Calculate average volume
      const average = dataArray.reduce((sum, value) => sum + value, 0) / bufferLength
      const dB = 20 * Math.log10(average / 255)

      if (dB < this.silenceThreshold) {
        // Silence detected
        if (!isSilent) {
          isSilent = true
          // Start silence timer
          this.silenceTimer = window.setTimeout(() => {
            onSilence()
          }, this.silenceDetectionTimeout)
        }
      } else {
        // Sound detected, reset silence detection
        if (isSilent) {
          isSilent = false
          if (this.silenceTimer) {
            clearTimeout(this.silenceTimer)
            this.silenceTimer = null
          }
        }
      }

      // Continue monitoring
      requestAnimationFrame(checkAudioLevel)
    }

    checkAudioLevel()
  }

  /**
   * Clean up silence detection resources
   */
  private cleanupSilenceDetection(): void {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer)
      this.silenceTimer = null
    }
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
    this.analyser = null
  }

  /**
   * Stop listening for speech input (Azure backend)
   */
  async stopListeningAzure(
    onResult?: SpeechRecognitionCallback,
    onError?: SpeechRecognitionErrorCallback,
    language: string = 'en-US'
  ): Promise<void> {
    if (!this.isListening) return

    this.cleanupSilenceDetection()
    const audioBlob = await this.audioRecorder.stopRecording()
    this.isListening = false

    if (audioBlob && onResult) {
      const text = await speechService.speechToText(audioBlob, language)
      if (text) {
        onResult({
          transcript: text,
          isFinal: true,
        })
      } else if (onError) {
        onError('Failed to recognize speech')
      }
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
