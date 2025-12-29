"""
Speech API Router
- STT: /speech/transcribe (Whisper large-v3)
- TTS: /speech/synthesize (MeloTTS-Korean)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/speech", tags=["speech"])


class TranscribeRequest(BaseModel):
    """Request for speech-to-text"""
    audio: str  # Base64 encoded audio (WAV/MP3)
    language: str = "ko"  # Default Korean


class TranscribeResponse(BaseModel):
    """Response from speech-to-text"""
    text: str
    segments: list
    language: str
    confidence: float
    error: Optional[str] = None


class SynthesizeRequest(BaseModel):
    """Request for text-to-speech"""
    text: str
    speed: float = 1.0
    emotion: str = "neutral"  # neutral, happy, sad, angry


class SynthesizeResponse(BaseModel):
    """Response from text-to-speech"""
    audio: str  # Base64 encoded WAV
    duration_seconds: float
    sample_rate: int
    error: Optional[str] = None


class ConversationTurnRequest(BaseModel):
    """Request for full conversation turn (STT -> AI -> TTS)"""
    user_audio: str  # Base64 encoded audio
    language: str = "ko"
    response_speed: float = 1.0
    response_emotion: str = "neutral"


class ConversationTurnResponse(BaseModel):
    """Response from conversation turn"""
    user_text: str
    ai_text: str
    ai_audio: str  # Base64 encoded WAV
    ai_audio_duration: float
    error: Optional[str] = None


# These will be set by modal_deploy.py
_speech_processor = None


def set_speech_processor(processor):
    """Called by modal_deploy.py to inject the processor"""
    global _speech_processor
    _speech_processor = processor


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(request: TranscribeRequest):
    """
    Convert speech to text using Whisper large-v3
    
    Best for:
    - User voice input during avatar conversation
    - Profile questionnaire answers by voice
    
    Audio formats supported: WAV, MP3, M4A, FLAC
    """
    if _speech_processor is None:
        raise HTTPException(500, "Speech processor not initialized")
    
    result = _speech_processor.speech_to_text(
        audio_base64=request.audio,
        language=request.language
    )
    
    return TranscribeResponse(**result)


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(request: SynthesizeRequest):
    """
    Convert text to speech using MeloTTS-Korean
    
    Best for:
    - Avatar voice responses
    - Question narration
    - Match explanations by voice
    
    Returns WAV audio at 24kHz
    """
    if _speech_processor is None:
        raise HTTPException(500, "Speech processor not initialized")
    
    if not request.text.strip():
        raise HTTPException(400, "Text cannot be empty")
    
    if len(request.text) > 2000:
        raise HTTPException(400, "Text too long (max 2000 characters)")
    
    result = _speech_processor.text_to_speech(
        text=request.text,
        speed=request.speed,
        emotion=request.emotion
    )
    
    return SynthesizeResponse(**result)


@router.post("/conversation-turn")
async def conversation_turn(request: ConversationTurnRequest):
    """
    Process one turn of voice conversation with avatar
    
    Flow:
    1. STT: User audio -> text
    2. AI: Generate response (handled externally)
    3. TTS: AI text -> audio
    
    Note: This endpoint only handles STT, the AI response generation
    should be handled by the caller (using /questions/analyze etc.)
    and then call /speech/synthesize
    """
    if _speech_processor is None:
        raise HTTPException(500, "Speech processor not initialized")
    
    # Step 1: Transcribe user audio
    stt_result = _speech_processor.speech_to_text(
        audio_base64=request.user_audio,
        language=request.language
    )
    
    user_text = stt_result.get("text", "")
    
    if not user_text:
        return ConversationTurnResponse(
            user_text="",
            ai_text="죄송해요, 잘 못 알아들었어요. 다시 말씀해주세요.",
            ai_audio="",
            ai_audio_duration=0,
            error="Could not transcribe audio"
        )
    
    # Note: AI response generation should be handled by caller
    # This is just the speech processing layer
    return {
        "user_text": user_text,
        "transcription_confidence": stt_result.get("confidence", 0),
        "segments": stt_result.get("segments", [])
    }


@router.get("/health")
async def health():
    """Check speech services health"""
    status = {
        "stt": "unknown",
        "tts": "unknown"
    }
    
    if _speech_processor:
        status["stt"] = "ready" if _speech_processor.stt.model else "not_loaded"
        status["tts"] = "ready" if _speech_processor.tts.model else "fallback"
    
    return {
        "status": "healthy" if all(s != "unknown" for s in status.values()) else "degraded",
        "services": status,
        "models": {
            "stt": "faster-whisper/large-v3",
            "tts": "MeloTTS-Korean (or edge-tts fallback)"
        }
    }
