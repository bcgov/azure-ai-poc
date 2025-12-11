"""Azure Speech Services for text-to-speech and speech-to-text using SDK."""

import re
from typing import Literal

import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

# Pre-compiled regex patterns for text cleaning (performance optimization)
_RE_CODE_BLOCK = re.compile(r"```[\s\S]*?```")
_RE_INLINE_CODE = re.compile(r"`[^`]+`")
_RE_HEADERS = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_RE_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_RE_ITALIC_STAR = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_RE_BOLD_UNDERSCORE = re.compile(r"__([^_]+)__")
_RE_ITALIC_UNDERSCORE = re.compile(r"(?<!_)_([^_]+)_(?!_)")
_RE_LINKS = re.compile(r"\[([^\[\]]*)\]\([^()]*\)")
_RE_BULLET_DASH = re.compile(r"^[\-\*]\s+", re.MULTILINE)
_RE_BULLET_NUM = re.compile(r"^\d+\.\s+", re.MULTILINE)
_RE_HR = re.compile(r"^-{3,}$", re.MULTILINE)
_RE_MULTI_NEWLINE = re.compile(r"\n{3,}")


class SpeechService:
    """Service for text-to-speech and speech-to-text using Azure Speech SDK.

    Uses SDK with endpoint parameter as per MS documentation:
    https://learn.microsoft.com/en-us/azure/ai-services/speech-service/
    """

    # Available voices for different languages/styles
    VOICES = {
        "en-US-female": "en-US-AvaMultilingualNeural",
        "en-US-male": "en-US-AndrewMultilingualNeural",
        "en-CA-female": "en-CA-ClaraNeural",
        "en-CA-male": "en-CA-LiamNeural",
        "en-GB-female": "en-GB-SoniaNeural",
        "en-GB-male": "en-GB-RyanNeural",
    }

    def __init__(self):
        """Initialize the speech service."""
        self.speech_region = settings.azure_speech_region
        self.endpoint = settings.azure_speech_endpoint
        self.use_managed_identity = settings.use_managed_identity
        self._credential: DefaultAzureCredential | None = None

        if self.use_managed_identity:
            self._credential = DefaultAzureCredential()
            self.speech_key = settings.azure_speech_key  # added as managed identity not working.
            logger.info("Using managed identity for Azure Speech Services")
        else:
            self.speech_key = settings.azure_speech_key
            if not self.speech_key:
                logger.warning(
                    "speech_service_not_configured",
                    message="Azure Speech key not configured",
                )
            elif not self.endpoint:
                logger.warning(
                    "speech_service_not_configured",
                    message="Azure Speech endpoint not configured",
                )
            else:
                logger.info(
                    "speech_service_configured",
                    endpoint=self.endpoint,
                    message="Using API key for Azure Speech Services",
                )

    def is_configured(self) -> bool:
        """Check if the speech service is properly configured."""
        if self.use_managed_identity:
            return bool(self.endpoint and self._credential)
        return bool(getattr(self, "speech_key", None) and self.endpoint)

    def _get_auth_token(self) -> str | None:
        """Get an authentication token for managed identity."""
        if not self._credential:
            return None
        try:
            token = self._credential.get_token("https://cognitiveservices.azure.com/.default")
            return token.token
        except Exception as e:
            logger.error("speech_token_error", error=str(e))
            return None

    def _create_speech_config(self) -> speechsdk.SpeechConfig | None:
        """Create speech config with endpoint parameter as per MS docs."""
        try:
            if self.use_managed_identity:
                """ auth_token = self._get_auth_token()
                if not auth_token:
                    logger.error(
                        "speech_auth_failed",
                        message="Failed to get auth token for managed identity",
                    )
                    return None """
                # Create config with endpoint only, then set auth token separately
                # (SDK doesn't allow both auth_token and endpoint in constructor)
                # speech_key is needed
                speech_config = speechsdk.SpeechConfig(
                    subscription=self.speech_key, endpoint=self.endpoint
                )
            else:
                # Use endpoint parameter with subscription key (as per MS docs)
                speech_config = speechsdk.SpeechConfig(
                    subscription=self.speech_key,
                    endpoint=self.endpoint,
                )

            logger.info(
                "speech_config_created",
                endpoint=self.endpoint,
                auth_type="managed_identity" if self.use_managed_identity else "api_key",
            )
            return speech_config

        except Exception as e:
            logger.error("speech_config_error", error=str(e))
            return None

    async def text_to_speech_stream(
        self,
        text: str,
        voice: str = "en-CA-female",
        output_format: Literal[
            "audio-16khz-128kbitrate-mono-mp3",
            "audio-24khz-160kbitrate-mono-mp3",
            "raw-24khz-16bit-mono-pcm",
        ] = "audio-24khz-160kbitrate-mono-mp3",
        chunk_size: int = 4096,
    ):
        """
        Stream text to speech audio using Azure Speech SDK with real-time streaming.

        Args:
            text: The text to convert to speech
            voice: Voice identifier (e.g., "en-US-female", "en-CA-male")
            output_format: Audio output format (MP3 or raw PCM for streaming)
            chunk_size: Size of chunks to yield (used for buffering)

        Yields:
            Audio chunks as they are synthesized
        """
        import asyncio
        import queue

        if not self.is_configured():
            logger.error("speech_not_configured", message="Speech service not configured")
            return

        try:
            # Get the voice name
            voice_name = self.VOICES.get(voice, self.VOICES["en-CA-female"])

            # Create speech config
            speech_config = self._create_speech_config()
            if not speech_config:
                return

            # Set voice
            speech_config.speech_synthesis_voice_name = voice_name

            # Set output format
            if output_format == "audio-16khz-128kbitrate-mono-mp3":
                speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
                )
            elif output_format == "raw-24khz-16bit-mono-pcm":
                speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Raw24Khz16BitMonoPcm
                )
            else:
                speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3
                )

            # Use None for audio_config to get audio data in memory
            speech_synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=None,
            )

            # Clean text for speech
            clean_text = self._clean_text_for_speech(text)

            logger.debug(
                "tts_streaming_start",
                text_length=len(clean_text),
                voice=voice_name,
                endpoint=self.endpoint,
            )

            # Use a queue to collect audio chunks from the synthesizing event
            audio_queue: queue.Queue[bytes | None] = queue.Queue()
            total_bytes = 0
            synthesis_error: str | None = None

            def on_synthesizing(evt: speechsdk.SpeechSynthesisEventArgs) -> None:
                """Callback for when audio data is available."""
                nonlocal total_bytes
                if evt.result.audio_data:
                    audio_queue.put(evt.result.audio_data)
                    total_bytes += len(evt.result.audio_data)

            def on_completed(evt: speechsdk.SpeechSynthesisEventArgs) -> None:
                """Callback for when synthesis is complete."""
                audio_queue.put(None)  # Signal completion
                logger.info(
                    "tts_stream_completed",
                    text_length=len(text),
                    total_bytes=total_bytes,
                    voice=voice_name,
                )

            def on_canceled(evt: speechsdk.SpeechSynthesisEventArgs) -> None:
                """Callback for when synthesis is canceled."""
                nonlocal synthesis_error
                cancellation_details = evt.result.cancellation_details
                synthesis_error = cancellation_details.error_details
                logger.error(
                    "tts_stream_canceled",
                    reason=str(cancellation_details.reason),
                    error_details=synthesis_error,
                )
                audio_queue.put(None)  # Signal completion

            # Connect event handlers
            speech_synthesizer.synthesizing.connect(on_synthesizing)
            speech_synthesizer.synthesis_completed.connect(on_completed)
            speech_synthesizer.synthesis_canceled.connect(on_canceled)

            # Start synthesis (non-blocking)
            speech_synthesizer.speak_text_async(clean_text)

            # Yield audio chunks as they arrive
            while True:
                try:
                    # Wait for audio data with a timeout
                    chunk = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: audio_queue.get(timeout=30)
                    )

                    if chunk is None:
                        # Synthesis complete
                        break

                    yield chunk

                except queue.Empty:
                    logger.warning("tts_stream_timeout", message="Timeout waiting for audio data")
                    break

            if synthesis_error:
                logger.error("tts_stream_error", error=synthesis_error)

        except Exception as e:
            logger.error("tts_stream_error", error=str(e))

    async def text_to_speech(
        self,
        text: str,
        voice: str = "en-CA-female",
        output_format: Literal[
            "audio-16khz-128kbitrate-mono-mp3", "audio-24khz-160kbitrate-mono-mp3"
        ] = "audio-24khz-160kbitrate-mono-mp3",
    ) -> bytes | None:
        """
        Convert text to speech audio using Azure Speech SDK.

        Args:
            text: The text to convert to speech
            voice: Voice identifier (e.g., "en-US-female", "en-CA-male")
            output_format: Audio output format

        Returns:
            Audio bytes in MP3 format, or None if failed
        """
        if not self.is_configured():
            logger.error("speech_not_configured", message="Speech service not configured")
            return None

        try:
            # Get the voice name
            voice_name = self.VOICES.get(voice, self.VOICES["en-CA-female"])

            # Create speech config
            speech_config = self._create_speech_config()
            if not speech_config:
                return None

            # Set voice
            speech_config.speech_synthesis_voice_name = voice_name

            # Set output format
            if output_format == "audio-16khz-128kbitrate-mono-mp3":
                speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
                )
            else:
                speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3
                )

            # Use None for audio_config to get audio data in memory (no speaker output)
            speech_synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=None,
            )

            # Clean text for speech (remove markdown, etc.)
            clean_text = self._clean_text_for_speech(text)

            logger.debug(
                "tts_synthesizing",
                text_length=len(clean_text),
                voice=voice_name,
                endpoint=self.endpoint,
            )

            # Synthesize speech (SDK is synchronous)
            result = speech_synthesizer.speak_text_async(clean_text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.info(
                    "tts_success",
                    text_length=len(text),
                    audio_bytes=len(result.audio_data),
                    voice=voice_name,
                )
                return result.audio_data

            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                logger.error(
                    "tts_canceled",
                    reason=str(cancellation_details.reason),
                    error_details=cancellation_details.error_details,
                )
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    logger.error(
                        "tts_error_details",
                        error_details=cancellation_details.error_details,
                    )
                return None

            else:
                logger.error("tts_unexpected_result", reason=str(result.reason))
                return None

        except Exception as e:
            logger.error("tts_error", error=str(e))
            return None

    async def speech_to_text(
        self,
        audio_data: bytes,
        language: str = "en-US",
    ) -> str | None:
        """
        Convert speech audio to text using Azure Speech SDK.

        Args:
            audio_data: Audio bytes (WAV format expected)
            language: Recognition language (e.g., "en-US", "en-CA")

        Returns:
            Recognized text, or None if failed
        """
        if not self.is_configured():
            logger.error("speech_not_configured", message="Speech service not configured")
            return None

        try:
            # Create speech config
            speech_config = self._create_speech_config()
            if not speech_config:
                return None

            # Set recognition language
            speech_config.speech_recognition_language = language

            # Create audio config from audio data
            # The SDK expects a stream or file, so we use PushAudioInputStream
            audio_format = speechsdk.audio.AudioStreamFormat()
            push_stream = speechsdk.audio.PushAudioInputStream(audio_format)
            push_stream.write(audio_data)
            push_stream.close()

            audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

            # Create speech recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )

            logger.debug(
                "stt_recognizing",
                audio_bytes=len(audio_data),
                language=language,
                endpoint=self.endpoint,
            )

            # Recognize speech (SDK is synchronous)
            result = speech_recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logger.info(
                    "stt_success",
                    audio_bytes=len(audio_data),
                    text_length=len(result.text),
                )
                return result.text

            elif result.reason == speechsdk.ResultReason.NoMatch:
                no_match_details = result.no_match_details
                logger.warning(
                    "stt_no_match",
                    reason=str(no_match_details.reason) if no_match_details else "unknown",
                )
                return None

            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                logger.error(
                    "stt_canceled",
                    reason=str(cancellation_details.reason),
                    error_details=cancellation_details.error_details,
                )
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    logger.error(
                        "stt_error_details",
                        error_details=cancellation_details.error_details,
                    )
                return None

            else:
                logger.error("stt_unexpected_result", reason=str(result.reason))
                return None

        except Exception as e:
            logger.error("stt_error", error=str(e))
            return None

    def _clean_text_for_speech(self, text: str) -> str:
        """
        Clean text for speech synthesis by removing markdown and other formatting.

        Uses pre-compiled regex patterns for better performance.

        Args:
            text: Raw text that may contain markdown

        Returns:
            Cleaned text suitable for TTS
        """
        # Remove code blocks
        text = _RE_CODE_BLOCK.sub("", text)
        text = _RE_INLINE_CODE.sub("", text)

        # Remove markdown headers (keep the text)
        text = _RE_HEADERS.sub("", text)

        # Remove bold/italic markers
        text = _RE_BOLD.sub(r"\1", text)
        text = _RE_ITALIC_STAR.sub(r"\1", text)
        text = _RE_BOLD_UNDERSCORE.sub(r"\1", text)
        text = _RE_ITALIC_UNDERSCORE.sub(r"\1", text)

        # Remove links, keep text
        text = _RE_LINKS.sub(r"\1", text)

        # Remove bullet points
        text = _RE_BULLET_DASH.sub("", text)
        text = _RE_BULLET_NUM.sub("", text)

        # Remove horizontal rules
        text = _RE_HR.sub("", text)

        # Remove multiple newlines
        text = _RE_MULTI_NEWLINE.sub("\n\n", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def get_available_voices(self) -> dict[str, str]:
        """Get available voices for TTS."""
        return self.VOICES.copy()


# Singleton instance
_speech_service: SpeechService | None = None


def get_speech_service() -> SpeechService:
    """Get the singleton speech service instance."""
    global _speech_service
    if _speech_service is None:
        _speech_service = SpeechService()
    return _speech_service
