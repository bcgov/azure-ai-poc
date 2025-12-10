"""Azure Speech Services for text-to-speech and speech-to-text using SDK."""

import re
from typing import Literal

import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


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
                auth_token = self._get_auth_token()
                if not auth_token:
                    logger.error(
                        "speech_auth_failed",
                        message="Failed to get auth token for managed identity",
                    )
                    return None
                # Create config with endpoint only, then set auth token separately
                # (SDK doesn't allow both auth_token and endpoint in constructor)
                speech_config = speechsdk.SpeechConfig(endpoint=self.endpoint)
                speech_config.authorization_token = auth_token
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

        Args:
            text: Raw text that may contain markdown

        Returns:
            Cleaned text suitable for TTS
        """
        # Remove code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`[^`]+`", "", text)

        # Remove markdown headers (keep the text)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Remove bold/italic markers
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)

        # Remove links, keep text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Remove bullet points
        text = re.sub(r"^[\-\*]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)

        # Remove horizontal rules
        text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)

        # Remove multiple newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

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
