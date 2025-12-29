"""
Matching API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


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
async def generate_profile_embedding(request: EmbedProfileRequest):
    """
    Generate 768D embedding for user profile
    
    - **profile**: Dictionary of question-answer pairs
    
    Returns semantic embedding for matching
    """
    from app.main import get_profile_model
    
    try:
        model = get_profile_model()
        
        if not request.profile:
            raise HTTPException(
                status_code=400,
                detail="Profile data is empty"
            )
        
        embedding = model.generate_embedding(request.profile)
        
        return EmbedProfileResponse(embedding=embedding)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile embedding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain", response_model=ExplainResponse)
async def generate_match_explanation(request: ExplainRequest):
    """
    Generate human-readable explanation for match
    
    - **profile_a**: First user's profile
    - **profile_b**: Second user's profile  
    - **score**: Matching score (0-100)
    
    Returns explanation with specific match points
    """
    try:
        # Analyze key matching categories
        match_points = []
        
        # Marriage timeline
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
        
        # Financial values
        if "경제력" in request.profile_a and "경제력" in request.profile_b:
            a_val = request.profile_a["경제력"]
            b_val = request.profile_b["경제력"]
            is_match = a_val == b_val
            match_points.append(MatchPoint(
                category="재정 관리",
                match=is_match,
                description="재정 가치관 일치" if is_match else "재정 가치관 차이"
            ))
        
        # Family living
        if "부모님 동거" in request.profile_a and "부모님 동거" in request.profile_b:
            a_val = request.profile_a["부모님 동거"]
            b_val = request.profile_b["부모님 동거"]
            is_match = a_val == b_val
            match_points.append(MatchPoint(
                category="가족 생활",
                match=is_match,
                description="부모님 동거 계획 일치" if is_match 
                           else f"부모님 동거 의견 차이 (대화 권장)"
            ))
        
        # Generate overall explanation
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
        logger.error(f"Match explanation error: {e}")
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
