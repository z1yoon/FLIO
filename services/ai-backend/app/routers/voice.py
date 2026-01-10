"""
Voice Processing Router for FLIO Dating App
Handles Whisper transcription for blind accessibility
"""

import tempfile
import os
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
import logging

from ..services.azure_openai_service import azure_openai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form("ko")  # Default to Korean
):
    """
    Transcribe audio file using Azure OpenAI Whisper
    
    For FLIO blind accessibility:
    - Converts voice answers to text for matching algorithm
    - Supports Korean language for dating questions
    - Returns clean text that feeds into existing answer processing
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('audio/'):
            raise HTTPException(
                status_code=400, 
                detail="File must be an audio file (m4a, mp3, wav, etc.)"
            )
        
        # Create temporary file for audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Processing audio file: {file.filename}, size: {len(content)} bytes")
        
        # Transcribe using Azure OpenAI Whisper
        transcription_result = await azure_openai_service.transcribe_audio(
            temp_file_path, 
            language=language
        )
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        # Return transcribed text
        transcribed_text = transcription_result.get('text', '').strip()
        
        logger.info(f"Transcription successful: '{transcribed_text[:100]}...'")
        
        return JSONResponse({
            "success": True,
            "text": transcribed_text,
            "language": language,
            "confidence": transcription_result.get('confidence', 1.0)
        })
        
    except Exception as e:
        # Clean up temp file on error
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        logger.error(f"Audio transcription failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Speech recognition failed: {str(e)}"
        )

@router.post("/validate-answer")
async def validate_voice_answer(
    transcribed_text: str = Form(...),
    question_id: str = Form(...),
    expected_options: Optional[str] = Form(None)  # JSON string of choice options
):
    """
    Validate and clean transcribed voice answer for choice questions
    
    For choice questions, finds best match among available options
    For text questions, returns cleaned text
    """
    try:
        import json
        
        cleaned_text = transcribed_text.strip()
        
        # If it's a choice question with expected options
        if expected_options:
            options = json.loads(expected_options)
            option_texts = [opt.get('text_ko', '') for opt in options if opt.get('text_ko')]
            
            # Find best matching option using simple similarity
            best_match = None
            best_similarity = 0
            
            for option in options:
                option_text = option.get('text_ko', '').lower()
                if option_text in cleaned_text.lower():
                    best_match = option.get('value')
                    best_similarity = 1.0
                    break
                
                # Simple word overlap check
                overlap = len(set(option_text.split()) & set(cleaned_text.lower().split()))
                if overlap > best_similarity:
                    best_match = option.get('value')
                    best_similarity = overlap
            
            if best_match and best_similarity > 0:
                return JSONResponse({
                    "success": True,
                    "answer_value": best_match,
                    "answer_text": cleaned_text,
                    "confidence": best_similarity,
                    "matched_option": next(opt['text_ko'] for opt in options if opt['value'] == best_match)
                })
            else:
                # No good match found
                return JSONResponse({
                    "success": False,
                    "error": "voice_answer_unclear",
                    "message": "음성 답변이 선택지와 일치하지 않습니다. 다시 말해보시거나 화면을 터치해보세요.",
                    "transcribed_text": cleaned_text,
                    "available_options": option_texts
                })
        
        # For text questions, just return cleaned text
        return JSONResponse({
            "success": True,
            "answer_text": cleaned_text,
            "confidence": 1.0
        })
        
    except Exception as e:
        logger.error(f"Answer validation failed: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": "validation_failed",
            "message": "답변 처리 중 오류가 발생했습니다."
        })

@router.get("/health")
async def voice_health_check():
    """Health check for voice service"""
    try:
        # Test Azure OpenAI connection
        health_status = await azure_openai_service.test_connection()
        
        return JSONResponse({
            "status": "healthy",
            "whisper_available": health_status.get('whisper_available', True),
            "azure_openai_status": health_status.get('status', 'connected')
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e)
        }, status_code=503)