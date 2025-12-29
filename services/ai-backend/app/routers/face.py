"""
Face Verification API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class EmbedRequest(BaseModel):
    image: str  # Base64 encoded image


class EmbedResponse(BaseModel):
    embedding: Optional[List[float]]
    face_detected: bool
    error: Optional[str]


class VerifyRequest(BaseModel):
    profile_embedding: List[float]
    live_embedding: List[float]
    threshold: float = 0.85


class VerifyResponse(BaseModel):
    verified: bool
    similarity: float
    threshold: float
    message: str


class LivenessRequest(BaseModel):
    frames: List[str]  # List of base64 encoded frames


class LivenessResponse(BaseModel):
    is_live: bool
    blink_count: int
    message: str


@router.post("/embed", response_model=EmbedResponse)
async def extract_face_embedding(request: EmbedRequest):
    """
    Extract 512D face embedding from image using InsightFace/ArcFace
    
    - **image**: Base64 encoded image (with or without data URL prefix)
    
    Returns embedding vector for face verification
    """
    from app.main import get_face_model
    
    try:
        model = get_face_model()
        embedding, face_detected, error = model.extract_embedding(request.image)
        
        return EmbedResponse(
            embedding=embedding,
            face_detected=face_detected,
            error=error if error else None
        )
    except Exception as e:
        logger.error(f"Face embedding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify", response_model=VerifyResponse)
async def verify_face(request: VerifyRequest):
    """
    Verify if two face embeddings match (85% threshold)
    
    - **profile_embedding**: 512D embedding from profile photo
    - **live_embedding**: 512D embedding from live selfie
    - **threshold**: Similarity threshold (default 0.85 = 85%)
    
    Returns verification result with similarity score
    """
    from app.main import get_face_model
    
    try:
        model = get_face_model()
        
        # Validate embedding dimensions
        if len(request.profile_embedding) != 512 or len(request.live_embedding) != 512:
            raise HTTPException(
                status_code=400,
                detail="Invalid embedding dimension. Expected 512D vectors."
            )
        
        verified, similarity = model.verify_faces(
            request.profile_embedding,
            request.live_embedding,
            request.threshold
        )
        
        # Convert to percentage
        similarity_percent = similarity * 100
        threshold_percent = request.threshold * 100
        
        message = (
            f"✅ Face verified ({similarity_percent:.1f}%)"
            if verified
            else f"❌ Face mismatch ({similarity_percent:.1f}% < {threshold_percent:.0f}%)"
        )
        
        return VerifyResponse(
            verified=verified,
            similarity=similarity_percent,
            threshold=threshold_percent,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Face verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/liveness", response_model=LivenessResponse)
async def check_liveness(request: LivenessRequest):
    """
    Check liveness from video frames using blink detection
    
    - **frames**: List of base64 encoded video frames (30 frames recommended)
    
    Returns liveness result with blink count
    """
    from app.main import get_face_model
    
    try:
        if len(request.frames) < 10:
            raise HTTPException(
                status_code=400,
                detail="At least 10 frames required for liveness detection"
            )
        
        model = get_face_model()
        is_live, blink_count, message = model.detect_liveness(request.frames)
        
        return LivenessResponse(
            is_live=is_live,
            blink_count=blink_count,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Liveness check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
