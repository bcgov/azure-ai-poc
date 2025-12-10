"""Speech API endpoints for text-to-speech functionality."""

import base64

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.logger import get_logger
from app.services.speech_service import get_speech_service

logger = get_logger(__name__)


router = APIRouter()


class TextToSpeechRequest(BaseModel):
    """Request model for text-to-speech conversion."""

    text: str = Field(..., description="Text to convert to speech", min_length=1, max_length=100000)
    voice: str = Field(
        default="en-CA-female",
        description="Voice to use (e.g., 'en-CA-female', 'en-US-male')",
    )


class SpeechToTextRequest(BaseModel):
    """Request model for speech-to-text conversion."""

    audio_data: str = Field(..., description="Base64-encoded audio data (WAV format)")
    language: str = Field(
        default="en-US",
        description="Recognition language (e.g., 'en-US', 'en-CA')",
    )


class SpeechToTextResponse(BaseModel):
    """Response model for speech-to-text conversion."""

    text: str = Field(..., description="Recognized text from speech")
    language: str = Field(..., description="Language used for recognition")


class VoicesResponse(BaseModel):
    """Response model for available voices."""

    voices: dict[str, str]


@router.post(
    "/tts/stream",
    summary="Stream text to speech",
    description="Stream text to speech audio using Azure Speech Services (real-time)",
)
async def text_to_speech_stream(request: TextToSpeechRequest):
    """
    Convert text to speech and stream MP3 audio in real-time.

    Args:
        request: Text and voice configuration

    Returns:
        Streaming MP3 audio response
    """
    speech_service = get_speech_service()

    if not speech_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Speech service is not configured. Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION.",
        )

    logger.info(
        "tts_stream_request",
        text_length=len(request.text),
        voice=request.voice,
    )

    return StreamingResponse(
        speech_service.text_to_speech_stream(
            text=request.text,
            voice=request.voice,
        ),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/tts",
    summary="Convert text to speech",
    description="Convert text to speech audio using Azure Speech Services",
    responses={
        200: {
            "content": {"audio/mpeg": {}},
            "description": "MP3 audio file",
        },
        400: {"description": "Invalid request"},
        503: {"description": "Speech service not configured"},
    },
)
async def text_to_speech(request: TextToSpeechRequest) -> Response:
    """
    Convert text to speech and return MP3 audio.

    Args:
        request: Text and voice configuration

    Returns:
        MP3 audio response
    """
    speech_service = get_speech_service()

    if not speech_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Speech service is not configured. Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION.",
        )

    logger.info(
        "tts_request",
        text_length=len(request.text),
        voice=request.voice,
    )

    audio_data = await speech_service.text_to_speech(
        text=request.text,
        voice=request.voice,
    )

    if audio_data is None or len(audio_data) == 0:
        raise HTTPException(
            status_code=500,
            detail="Failed to synthesize speech. Please try again.",
        )

    return Response(
        content=audio_data,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=speech.mp3",
        },
    )


@router.get(
    "/voices",
    summary="Get available voices",
    description="Get list of available TTS voices",
    response_model=VoicesResponse,
)
async def get_voices() -> VoicesResponse:
    """Get available TTS voices."""
    speech_service = get_speech_service()
    return VoicesResponse(voices=speech_service.get_available_voices())


@router.post(
    "/stt",
    summary="Convert speech to text",
    description="Convert speech audio to text using Azure Speech Services",
    response_model=SpeechToTextResponse,
    responses={
        200: {"description": "Successfully recognized speech"},
        400: {"description": "Invalid audio data"},
        503: {"description": "Speech service not configured"},
    },
)
async def speech_to_text(request: SpeechToTextRequest) -> SpeechToTextResponse:
    """
    Convert speech to text.

    Args:
        request: Audio data and language configuration

    Returns:
        Recognized text
    """
    speech_service = get_speech_service()

    if not speech_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Speech service is not configured. "
                "Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION."
            ),
        )

    try:
        # Decode base64 audio data
        audio_bytes = base64.b64decode(request.audio_data)
    except Exception as e:
        logger.error("stt_decode_error", error=str(e))
        raise HTTPException(
            status_code=400,
            detail="Invalid audio data. Must be base64-encoded.",
        ) from e

    logger.info(
        "stt_request",
        audio_bytes=len(audio_bytes),
        language=request.language,
    )

    recognized_text = await speech_service.speech_to_text(
        audio_data=audio_bytes,
        language=request.language,
    )

    if recognized_text is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to recognize speech. Please try again with clearer audio.",
        )

    return SpeechToTextResponse(
        text=recognized_text,
        language=request.language,
    )


@router.get(
    "/health",
    summary="Check speech service health",
    description="Check if the speech service is properly configured",
)
async def health_check() -> dict:
    """Check speech service health."""
    speech_service = get_speech_service()
    return {
        "status": "healthy" if speech_service.is_configured() else "not_configured",
        "service": "speech",
    }
