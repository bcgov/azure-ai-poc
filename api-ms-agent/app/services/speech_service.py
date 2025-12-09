"""Azure Speech Services for text-to-speech functionality."""

import io
from typing import Literal

import azure.cognitiveservices.speech as speechsdk

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


class SpeechService:
    """Service for text-to-speech using Azure Speech Services."""

    # Available voices for different languages/styles
    VOICES = {
        "en-US-female": "en-US-JennyNeural",
        "en-US-male": "en-US-GuyNeural",
        "en-CA-female": "en-CA-ClaraNeural",
        "en-CA-male": "en-CA-LiamNeural",
        "en-GB-female": "en-GB-SoniaNeural",
        "en-GB-male": "en-GB-RyanNeural",
    }

    def __init__(self):
        """Initialize the speech service."""
        self.speech_key = settings.azure_speech_key
        self.speech_region = settings.azure_speech_region

        if not self.speech_key or not self.speech_region:
            logger.warning(
                "speech_service_not_configured",
                message="Azure Speech credentials not configured",
            )

    def is_configured(self) -> bool:
        """Check if the speech service is properly configured."""
        return bool(self.speech_key and self.speech_region)

    async def text_to_speech(
        self,
        text: str,
        voice: str = "en-CA-female",
        output_format: Literal[
            "audio-16khz-128kbitrate-mono-mp3", "audio-24khz-160kbitrate-mono-mp3"
        ] = "audio-24khz-160kbitrate-mono-mp3",
    ) -> bytes | None:
        """
        Convert text to speech audio.

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

            # Configure speech synthesis
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.speech_region,
            )
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

            # Use in-memory audio output
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=None,  # No audio output, we want bytes
            )

            # Clean text for speech (remove markdown, etc.)
            clean_text = self._clean_text_for_speech(text)

            # Synthesize speech
            result = synthesizer.speak_text_async(clean_text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.info(
                    "tts_success",
                    text_length=len(text),
                    audio_bytes=len(result.audio_data),
                    voice=voice_name,
                )
                return result.audio_data

            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                logger.error(
                    "tts_canceled",
                    reason=str(cancellation.reason),
                    error_details=cancellation.error_details,
                )
                return None

        except Exception as e:
            logger.error("tts_error", error=str(e))
            return None

    def _clean_text_for_speech(self, text: str) -> str:
        """
        Clean text for speech synthesis by removing markdown and other formatting.

        Args:
            text: Raw text that may contain markdown

        Returns:
            Cleaned text suitable for TTS
        """
        import re

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
