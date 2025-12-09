"""Speech API endpoints for text-to-speech functionality."""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.logger import get_logger
from app.services.speech_service import get_speech_service

logger = get_logger(__name__)


router = APIRouter()


class TextToSpeechRequest(BaseModel):
    """Request model for text-to-speech conversion."""

    text: str = Field(..., description="Text to convert to speech", min_length=1, max_length=5000)
    voice: str = Field(
        default="en-CA-female",
        description="Voice to use (e.g., 'en-CA-female', 'en-US-male')",
    )


class VoicesResponse(BaseModel):
    """Response model for available voices."""

    voices: dict[str, str]


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

    if audio_data is None:
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
