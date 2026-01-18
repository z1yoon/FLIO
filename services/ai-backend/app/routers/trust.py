"""
FLIO Trust Score API Routes
Korean Marriage Agency Style (결혼정보회사)

Endpoints for trust score management and verification status.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

from ..services.trust_score_service import trust_score_service, TrustScoreResponse, TrustSummary

logger = logging.getLogger(__name__)
router = APIRouter()


# Response Models

class TrustScoreDetailResponse(BaseModel):
    """Detailed trust score breakdown"""
    user_id: str
    total_trust_score: float
    trust_tier: str
    component_scores: Dict[str, float]
    tier_benefits: Dict[str, Any]
    calculation_details: Dict[str, Any]
    last_calculated_at: str


class TrustSummaryResponse(BaseModel):
    """Simplified trust summary"""
    trust_score: float
    trust_tier: str
    trust_tier_korean: str
    verified_items: List[str]
    profile_completeness: float
    is_matching_enabled: bool
    daily_match_limit: int


class TrustTierInfoResponse(BaseModel):
    """Trust tier information and benefits"""
    tier: str
    tier_korean: str
    min_score: float
    benefits: Dict[str, Any]
    requirements: List[str]


class RecalculateResponse(BaseModel):
    """Trust score recalculation result"""
    success: bool
    message: str
    previous_score: Optional[float]
    new_score: float
    previous_tier: Optional[str]
    new_tier: str


class BehaviorLogRequest(BaseModel):
    """Request to log user behavior"""
    user_id: str
    event_type: str
    event_data: Optional[Dict] = None
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None


# Korean tier names
TIER_KOREAN_NAMES = {
    'platinum': 'VIP회원',
    'gold': '우수회원',
    'silver': '인증회원',
    'bronze': '기본회원',
    'unverified': '미인증'
}

# Tier requirements
TIER_REQUIREMENTS = {
    'platinum': [
        '신분증 인증 완료',
        '학력 인증 완료',
        '소득 인증 완료',
        '재직 인증 완료',
        '모든 질문 답변 완료',
        '가족 정보 입력 완료',
        '논리적 일관성 검증 통과'
    ],
    'gold': [
        '신분증 인증 완료',
        '학력 또는 소득 인증 1개 이상',
        '모든 질문 답변 완료',
        '가족 정보 입력 완료'
    ],
    'silver': [
        '신분증 인증 완료',
        '질문 80% 이상 답변',
        '기본 프로필 완성'
    ],
    'bronze': [
        '전화번호 인증',
        '질문 50% 이상 답변',
        '기본 정보 입력'
    ],
    'unverified': [
        '아직 인증되지 않음',
        '매칭 서비스 이용 불가'
    ]
}


# API Endpoints

@router.get("/score/{user_id}", response_model=TrustScoreDetailResponse)
async def get_trust_score(user_id: str):
    """
    Get detailed trust score for a user

    Returns full breakdown of trust score components:
    - Document verification score
    - Logical consistency score
    - Behavioral stability score
    - Profile completeness score

    - **user_id**: User's unique identifier
    """
    try:
        # Get or calculate trust score
        score = await trust_score_service.get_trust_score(user_id)

        if not score:
            # Calculate if not exists
            score = await trust_score_service.calculate_trust_score(user_id)

        # Get tier benefits
        benefits = await trust_score_service.get_tier_benefits(score.trust_tier)

        return TrustScoreDetailResponse(
            user_id=user_id,
            total_trust_score=score.total_trust_score,
            trust_tier=score.trust_tier,
            component_scores={
                'document': score.document_score,
                'consistency': score.consistency_score,
                'behavioral': score.behavioral_score,
                'completeness': score.completeness_score
            },
            tier_benefits=benefits,
            calculation_details=score.calculation_details,
            last_calculated_at=score.last_calculated_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to get trust score for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{user_id}", response_model=TrustSummaryResponse)
async def get_trust_summary(user_id: str):
    """
    Get simplified trust summary for display

    Returns:
    - Current trust score and tier
    - List of verified items
    - Profile completeness percentage
    - Whether matching is enabled

    - **user_id**: User's unique identifier
    """
    try:
        summary = await trust_score_service.get_trust_summary(user_id)
        benefits = await trust_score_service.get_tier_benefits(summary.trust_tier)

        return TrustSummaryResponse(
            trust_score=summary.trust_score,
            trust_tier=summary.trust_tier,
            trust_tier_korean=TIER_KOREAN_NAMES.get(summary.trust_tier, '미인증'),
            verified_items=summary.verified_items,
            profile_completeness=summary.profile_completeness,
            is_matching_enabled=summary.is_matching_enabled,
            daily_match_limit=benefits.get('daily_matches', 0)
        )

    except Exception as e:
        logger.error(f"Failed to get trust summary for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tier/{user_id}")
async def get_trust_tier(user_id: str):
    """
    Get just the trust tier for a user

    Quick endpoint for tier-based access control

    - **user_id**: User's unique identifier
    """
    try:
        score = await trust_score_service.get_trust_score(user_id)

        if not score:
            return {
                "user_id": user_id,
                "trust_tier": "unverified",
                "trust_tier_korean": "미인증"
            }

        return {
            "user_id": user_id,
            "trust_tier": score.trust_tier,
            "trust_tier_korean": TIER_KOREAN_NAMES.get(score.trust_tier, '미인증'),
            "trust_score": score.total_trust_score
        }

    except Exception as e:
        logger.error(f"Failed to get trust tier for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recalculate/{user_id}", response_model=RecalculateResponse)
async def recalculate_trust_score(user_id: str):
    """
    Force recalculation of trust score

    Use this after:
    - Document verification completed
    - Profile updates
    - Consistency checks resolved

    - **user_id**: User's unique identifier
    """
    try:
        # Get previous score
        previous = await trust_score_service.get_trust_score(user_id)

        # Recalculate
        new_score = await trust_score_service.calculate_trust_score(user_id)

        return RecalculateResponse(
            success=True,
            message="Trust score recalculated successfully",
            previous_score=previous.total_trust_score if previous else None,
            new_score=new_score.total_trust_score,
            previous_tier=previous.trust_tier if previous else None,
            new_tier=new_score.trust_tier
        )

    except Exception as e:
        logger.error(f"Failed to recalculate trust score for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}")
async def get_trust_history(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    Get trust score history for a user

    Shows how trust score has changed over time

    - **user_id**: User's unique identifier
    - **limit**: Number of history entries to return
    """
    try:
        from ..models.database import get_supabase_client
        supabase = get_supabase_client()

        result = supabase.table('user_trust_scores').select(
            'score_history, total_trust_score, trust_tier, last_calculated_at'
        ).eq('user_id', user_id).single().execute()

        if not result.data:
            return {
                "user_id": user_id,
                "history": [],
                "current_score": 0,
                "current_tier": "unverified"
            }

        history = result.data.get('score_history', [])

        # Get last N entries
        recent_history = history[-limit:] if history else []

        return {
            "user_id": user_id,
            "history": recent_history,
            "current_score": result.data['total_trust_score'],
            "current_tier": result.data['trust_tier'],
            "last_calculated": result.data['last_calculated_at']
        }

    except Exception as e:
        logger.error(f"Failed to get trust history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tiers/info")
async def get_all_tier_info():
    """
    Get information about all trust tiers

    Returns tier names, thresholds, benefits, and requirements
    Useful for displaying tier system to users
    """
    tiers = []

    tier_thresholds = {
        'platinum': 0.90,
        'gold': 0.75,
        'silver': 0.60,
        'bronze': 0.40,
        'unverified': 0.00
    }

    for tier_name, min_score in tier_thresholds.items():
        benefits = await trust_score_service.get_tier_benefits(tier_name)

        tiers.append(TrustTierInfoResponse(
            tier=tier_name,
            tier_korean=TIER_KOREAN_NAMES.get(tier_name, tier_name),
            min_score=min_score,
            benefits=benefits,
            requirements=TIER_REQUIREMENTS.get(tier_name, [])
        ))

    return {"tiers": tiers}


@router.get("/tier/{tier_name}/info", response_model=TrustTierInfoResponse)
async def get_tier_info(tier_name: str):
    """
    Get information about a specific trust tier

    - **tier_name**: Tier name (platinum, gold, silver, bronze, unverified)
    """
    tier_thresholds = {
        'platinum': 0.90,
        'gold': 0.75,
        'silver': 0.60,
        'bronze': 0.40,
        'unverified': 0.00
    }

    if tier_name not in tier_thresholds:
        raise HTTPException(status_code=404, detail=f"Unknown tier: {tier_name}")

    benefits = await trust_score_service.get_tier_benefits(tier_name)

    return TrustTierInfoResponse(
        tier=tier_name,
        tier_korean=TIER_KOREAN_NAMES.get(tier_name, tier_name),
        min_score=tier_thresholds[tier_name],
        benefits=benefits,
        requirements=TIER_REQUIREMENTS.get(tier_name, [])
    )


@router.get("/matching-tiers/{user_id}")
async def get_matching_allowed_tiers(user_id: str):
    """
    Get tiers that a user can see in matches

    Based on user's tier, returns which tiers they can match with
    Higher tier users see higher quality matches

    - **user_id**: User's unique identifier
    """
    try:
        score = await trust_score_service.get_trust_score(user_id)
        tier = score.trust_tier if score else 'unverified'

        allowed_tiers = await trust_score_service.get_minimum_tier_for_matching(tier)

        return {
            "user_id": user_id,
            "user_tier": tier,
            "user_tier_korean": TIER_KOREAN_NAMES.get(tier, '미인증'),
            "can_see_tiers": allowed_tiers,
            "can_see_tiers_korean": [TIER_KOREAN_NAMES.get(t, t) for t in allowed_tiers]
        }

    except Exception as e:
        logger.error(f"Failed to get matching tiers for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/behavior/log")
async def log_user_behavior(request: BehaviorLogRequest):
    """
    Log user behavior for trust scoring

    Internal endpoint for tracking user actions
    High-risk behaviors decrease trust score

    - **user_id**: User's unique identifier
    - **event_type**: Type of event (profile_edit, income_change, etc.)
    - **event_data**: Additional event context
    """
    try:
        log_id = await trust_score_service.log_behavior(
            user_id=request.user_id,
            event_type=request.event_type,
            event_data=request.event_data,
            field_changed=request.field_changed,
            old_value=request.old_value,
            new_value=request.new_value
        )

        return {
            "success": True,
            "log_id": log_id,
            "message": "Behavior logged successfully"
        }

    except Exception as e:
        logger.error(f"Failed to log behavior: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upgrade-path/{user_id}")
async def get_upgrade_path(user_id: str):
    """
    Get recommendations to upgrade trust tier

    Shows what the user needs to do to reach the next tier
    Personalized based on current status

    - **user_id**: User's unique identifier
    """
    try:
        score = await trust_score_service.get_trust_score(user_id)

        if not score:
            score = await trust_score_service.calculate_trust_score(user_id)

        current_tier = score.trust_tier
        current_score = score.total_trust_score

        # Determine next tier and gap
        tier_order = ['unverified', 'bronze', 'silver', 'gold', 'platinum']
        tier_thresholds = {
            'bronze': 0.40,
            'silver': 0.60,
            'gold': 0.75,
            'platinum': 0.90
        }

        current_index = tier_order.index(current_tier)

        if current_index >= len(tier_order) - 1:
            return {
                "user_id": user_id,
                "current_tier": current_tier,
                "current_score": current_score,
                "next_tier": None,
                "score_gap": 0,
                "recommendations": ["최고 등급 달성! 현재 상태를 유지하세요."],
                "is_max_tier": True
            }

        next_tier = tier_order[current_index + 1]
        next_threshold = tier_thresholds[next_tier]
        score_gap = next_threshold - current_score

        # Generate personalized recommendations
        recommendations = []

        if score.document_score < 0.5:
            recommendations.append("신분증을 업로드하여 본인 인증을 완료하세요")
        if score.document_score < 0.8:
            recommendations.append("학력증명서나 재직증명서를 추가로 업로드하세요")

        if score.completeness_score < 0.8:
            if score.completeness_score < 0.4:
                recommendations.append("프로필 기본 정보를 모두 입력하세요")
            recommendations.append("모든 호환성 질문에 답변해주세요")
            recommendations.append("가족 정보를 입력하면 신뢰도가 올라갑니다")

        if score.consistency_score < 0.9:
            recommendations.append("프로필과 답변 내용의 일관성을 확인하세요")

        if not recommendations:
            recommendations.append("현재 상태를 유지하면 자동으로 등급이 상승합니다")

        return {
            "user_id": user_id,
            "current_tier": current_tier,
            "current_tier_korean": TIER_KOREAN_NAMES.get(current_tier, '미인증'),
            "current_score": round(current_score, 3),
            "next_tier": next_tier,
            "next_tier_korean": TIER_KOREAN_NAMES.get(next_tier, next_tier),
            "next_threshold": next_threshold,
            "score_gap": round(score_gap, 3),
            "recommendations": recommendations,
            "component_breakdown": {
                "document": {
                    "score": score.document_score,
                    "weight": 0.35,
                    "contribution": round(score.document_score * 0.35, 3)
                },
                "consistency": {
                    "score": score.consistency_score,
                    "weight": 0.25,
                    "contribution": round(score.consistency_score * 0.25, 3)
                },
                "behavioral": {
                    "score": score.behavioral_score,
                    "weight": 0.20,
                    "contribution": round(score.behavioral_score * 0.20, 3)
                },
                "completeness": {
                    "score": score.completeness_score,
                    "weight": 0.20,
                    "contribution": round(score.completeness_score * 0.20, 3)
                }
            },
            "is_max_tier": False
        }

    except Exception as e:
        logger.error(f"Failed to get upgrade path for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
