"""
FLIO Matching API Routes
Core matching functionality using Azure OpenAI embeddings
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

from ..services.profile_embedding_service import profile_embedding_service
from ..services.azure_openai_service import azure_openai_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Response Models
class ProfileEmbeddingResponse(BaseModel):
    success: bool
    message: str
    profile_summary: Optional[Dict] = None
    embedding_created: bool = False

class MatchResult(BaseModel):
    user_id: str
    compatibility_score: float
    similarity_score: float
    cultural_bonus: float
    name: Optional[str] = None
    age: Optional[int] = None
    explanation: Optional[str] = None

class MatchesResponse(BaseModel):
    user_id: str
    matches: List[MatchResult]
    total_found: int
    metadata: Dict[str, Any]

class MatchExplanationResponse(BaseModel):
    compatibility_score: float
    summary: str
    statistical_insights: List[str]
    compatibility_graphs: Dict[str, Dict]
    personalized_insights: Dict[str, Any]
    ai_analysis: Optional[Dict] = None
    conversation_starters: List[str]
    detailed_scores: Dict[str, float]
    score_breakdown: Dict[str, str]

# Profile Embedding Endpoints

@router.post("/profile/create-embedding", response_model=ProfileEmbeddingResponse)
async def create_user_embedding(user_id: str):
    """
    Create or update user profile embedding from their answers
    This should be called when user completes questionnaire
    
    - **user_id**: User's unique identifier
    """
    try:
        # Create user profile embedding
        user_profile = await profile_embedding_service.create_user_profile_embedding(user_id)
        
        return ProfileEmbeddingResponse(
            success=True,
            message=f"Profile embedding created successfully for user {user_id}",
            profile_summary={
                "nickname": user_profile.nickname,
                "age": user_profile.age,
                "answer_count": len(user_profile.answers),
                "profile_length": len(user_profile.profile_text),
                "embedding_dimension": len(user_profile.embedding)
            },
            embedding_created=True
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create embedding for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding creation failed: {str(e)}")

@router.get("/profile/{user_id}/embedding-status")
async def get_embedding_status(user_id: str):
    """
    Check if user has a valid profile embedding
    
    - **user_id**: User's unique identifier
    """
    try:
        embedding = await profile_embedding_service._get_user_embedding(user_id)
        
        if embedding:
            return {
                "has_embedding": True,
                "embedding_dimension": len(embedding),
                "message": "User has valid profile embedding"
            }
        else:
            return {
                "has_embedding": False,
                "message": "User needs to complete questionnaire for embedding creation"
            }
            
    except Exception as e:
        logger.error(f"Failed to check embedding status for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Matching Endpoints

@router.get("/matches/{user_id}", response_model=MatchesResponse)
async def find_matches(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50, description="Number of matches to return"),
    min_compatibility: float = Query(default=0.3, ge=0.0, le=1.0, description="Minimum compatibility score")
):
    """
    Find compatible matches for a user based on profile similarity
    
    - **user_id**: User's unique identifier
    - **limit**: Maximum number of matches to return (1-50)
    - **min_compatibility**: Minimum compatibility score (0.0-1.0)
    """
    try:
        # Find compatible matches
        match_results = await profile_embedding_service.find_compatible_matches(user_id, limit * 2)
        
        # Filter by minimum compatibility
        filtered_matches = [
            match for match in match_results 
            if match.compatibility_score >= min_compatibility
        ]
        
        # Limit results
        final_matches = filtered_matches[:limit]
        
        # Convert to dict for serialization
        matches_dict = [match.dict() for match in final_matches]
        
        return MatchesResponse(
            user_id=user_id,
            matches=matches_dict,
            total_found=len(filtered_matches),
            metadata={
                "algorithm_version": "3.0-static-priority",
                "embedding_dimension": 1024,
                "static_questions_weight": 0.7,
                "importance_bonus_weight": 0.2,
                "embedding_weight": 0.1,
                "dealbreaker_filtering": True
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to find matches for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Match finding failed: {str(e)}")


@router.get("/match-explanation/{user_a_id}/{user_b_id}", response_model=MatchExplanationResponse)
async def get_match_explanation(user_a_id: str, user_b_id: str):
    """
    Get detailed explanation for why two users match
    Uses Azure OpenAI to generate human-readable explanation
    
    - **user_a_id**: First user's ID
    - **user_b_id**: Second user's ID
    """
    try:
        # Generate match explanation
        explanation_data = await profile_embedding_service.get_match_explanation(user_a_id, user_b_id)
        
        explanation = explanation_data['explanation']
        
        return MatchExplanationResponse(
            compatibility_score=explanation_data['compatibility_score'],
            summary=explanation['summary'],
            statistical_insights=explanation.get('statistical_insights', []),
            compatibility_graphs=explanation.get('compatibility_graphs', {}),
            personalized_insights=explanation.get('personalized_insights', {}),
            ai_analysis=explanation.get('ai_analysis'),
            conversation_starters=explanation.get('conversation_starters', []),
            detailed_scores=explanation_data['detailed_scores'],
            score_breakdown=explanation_data.get('score_breakdown', {})
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate explanation for {user_a_id} and {user_b_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Explanation generation failed: {str(e)}")


# Legacy endpoints for backward compatibility
class EmbedProfileRequest(BaseModel):
    profile: Dict[str, str]  # Question-answer pairs

class EmbedProfileResponse(BaseModel):
    embedding: List[float]

class ExplainRequest(BaseModel):
    profile_a: Dict[str, str]
    profile_b: Dict[str, str]
    score: float

class MatchPoint(BaseModel):
    category: str
    match: bool
    description: str

class ExplainResponse(BaseModel):
    explanation: str
    match_points: List[MatchPoint]

@router.post("/embed", response_model=EmbedProfileResponse)
async def generate_profile_embedding_legacy(request: EmbedProfileRequest):
    """
    Legacy endpoint - Generate embedding for profile dictionary
    """
    try:
        if not request.profile:
            raise HTTPException(status_code=400, detail="Profile data is empty")
        
        # Build profile text from dictionary
        profile_text = " | ".join([f"{k}: {v}" for k, v in request.profile.items()])
        
        # Generate embedding using Azure OpenAI
        embedding_response = await azure_openai_service.generate_profile_embedding(profile_text)
        
        return EmbedProfileResponse(embedding=embedding_response.embedding)
        
    except Exception as e:
        logger.error(f"Legacy profile embedding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/explain", response_model=ExplainResponse)
async def generate_match_explanation_legacy(request: ExplainRequest):
    """
    Legacy endpoint - Generate simple match explanation
    """
    try:
        # Simple compatibility analysis
        match_points = []
        
        # Check key matching factors
        if "결혼 계획" in request.profile_a and "결혼 계획" in request.profile_b:
            a_val = request.profile_a["결혼 계획"]
            b_val = request.profile_b["결혼 계획"]
            is_match = _check_timeline_match(a_val, b_val)
            match_points.append(MatchPoint(
                category="결혼·가족관",
                match=is_match,
                description=f"결혼 시기: {a_val} vs {b_val}" if is_match 
                           else f"결혼 시기 차이 ({a_val} vs {b_val})"
            ))
        
        # Generate explanation
        matches = sum(1 for mp in match_points if mp.match)
        total = len(match_points)
        
        if matches == total and total > 0:
            explanation = f"두 분의 프로필이 매우 잘 맞습니다! 주요 가치관이 모두 일치해요."
        elif matches > total / 2:
            explanation = f"전반적으로 잘 맞는 편이에요. 몇 가지 차이점은 대화로 조율할 수 있어요."
        else:
            explanation = f"몇 가지 차이점이 있지만, 서로를 알아가며 조율할 수 있을 거예요."
        
        return ExplainResponse(
            explanation=explanation,
            match_points=match_points
        )
    except Exception as e:
        logger.error(f"Legacy match explanation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _check_timeline_match(a: str, b: str) -> bool:
    """Check if marriage timelines are compatible"""
    timeline_order = ["1년 이내", "2-3년 이내", "생각 중", "아직 모르겠어요"]
    
    try:
        a_idx = timeline_order.index(a)
        b_idx = timeline_order.index(b)
        return abs(a_idx - b_idx) <= 1  # Within one step
    except ValueError:
        return False
