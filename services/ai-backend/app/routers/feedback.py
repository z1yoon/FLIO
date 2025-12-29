"""
Feedback API Router
- Match outcomes tracking
- Secret profile verification
- A/B testing
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/feedback", tags=["feedback"])


# ==========================================
# Request/Response Models
# ==========================================

class MatchOutcomeRequest(BaseModel):
    match_id: str
    user_a_id: str
    user_b_id: str
    outcome: str  # dating, met, chatting, rejected, no_response
    days_active: int = 0
    questions_asked_a: List[str] = []
    questions_asked_b: List[str] = []


class SecretReportRequest(BaseModel):
    """
    Submit anonymous report about another user's profile
    NOTE: reporter_id is handled server-side from auth token
    """
    reported_user_id: str
    field: str  # height, weight, photos, job, education
    is_accurate: bool
    actual_value: Optional[str] = None
    notes: Optional[str] = None


class PostMeetingFeedbackRequest(BaseModel):
    """Feedback after meeting someone in person"""
    met_user_id: str
    overall: str  # accurate, somewhat_different, very_different
    photos: str
    height: str
    job: Optional[str] = None


class ABVariantRequest(BaseModel):
    experiment_id: str
    user_id: str


class ABConversionRequest(BaseModel):
    experiment_id: str
    user_id: str
    metric_name: str = "conversion"
    metric_value: float = 1.0


# ==========================================
# Global instances (set by main.py)
# ==========================================

_feedback_system = None
_ab_framework = None


def set_feedback_system(system):
    global _feedback_system
    _feedback_system = system


def set_ab_framework(framework):
    global _ab_framework
    _ab_framework = framework


# ==========================================
# Match Outcome Endpoints
# ==========================================

@router.post("/match-outcome")
async def record_match_outcome(request: MatchOutcomeRequest):
    """
    Record match outcome for RL learning
    
    Called when:
    - Users start chatting
    - Users meet in person
    - Users start dating
    - Users reject each other
    """
    if _feedback_system is None:
        raise HTTPException(500, "Feedback system not initialized")
    
    reward = _feedback_system.record_match_outcome(
        match_id=request.match_id,
        user_a_id=request.user_a_id,
        user_b_id=request.user_b_id,
        questions_asked_a=request.questions_asked_a,
        questions_asked_b=request.questions_asked_b,
        outcome=request.outcome,
        days_active=request.days_active
    )
    
    return {
        "status": "recorded",
        "outcome": request.outcome,
        "reward": reward,
        "message": f"Match outcome '{request.outcome}' recorded for RL learning"
    }


@router.get("/match-statistics")
async def get_match_statistics():
    """Get overall match statistics"""
    if _feedback_system is None:
        raise HTTPException(500, "Feedback system not initialized")
    
    return _feedback_system.get_match_statistics()


# ==========================================
# Secret Profile Verification Endpoints
# ==========================================

@router.post("/secret-report")
async def submit_secret_report(
    request: SecretReportRequest,
    reporter_id: str  # In production, get from auth token
):
    """
    Submit anonymous report about another user's profile
    
    ⚠️ IMPORTANT:
    - The reported user will NEVER know who reported them
    - If 2+ reports say info is wrong → user is blocked
    - Used to prevent catfishing
    
    Fields: height, weight, photos, job, education, age
    """
    if _feedback_system is None:
        raise HTTPException(500, "Feedback system not initialized")
    
    result = _feedback_system.submit_secret_report(
        reporter_id=reporter_id,
        reported_user_id=request.reported_user_id,
        field=request.field,
        is_accurate=request.is_accurate,
        actual_value=request.actual_value,
        notes=request.notes
    )
    
    return {
        "status": "submitted",
        "message": "피드백이 익명으로 제출되었습니다. 감사합니다!",
        **result
    }


@router.post("/post-meeting-feedback")
async def submit_post_meeting_feedback(
    request: PostMeetingFeedbackRequest,
    reporter_id: str  # In production, get from auth token
):
    """
    Submit feedback after meeting someone in person
    
    This is the main UI flow for secret verification
    """
    if _feedback_system is None:
        raise HTTPException(500, "Feedback system not initialized")
    
    results = []
    
    # Map responses to is_accurate
    accuracy_map = {
        "정확했어요": True,
        "accurate": True,
        "비슷했어요": True,
        "조금 달랐어요": False,
        "somewhat_different": False,
        "많이 달랐어요": False,
        "very_different": False,
        "5cm 이내": True,
        "5cm 이상 차이": False
    }
    
    # Process each field
    fields_to_check = [
        ("photos", request.photos),
        ("height", request.height),
    ]
    
    if request.job:
        fields_to_check.append(("job", request.job))
    
    for field, response in fields_to_check:
        is_accurate = accuracy_map.get(response, True)
        
        result = _feedback_system.submit_secret_report(
            reporter_id=reporter_id,
            reported_user_id=request.met_user_id,
            field=field,
            is_accurate=is_accurate
        )
        results.append(result)
    
    return {
        "status": "submitted",
        "message": "피드백이 익명으로 제출되었습니다. 다른 회원들에게 도움이 됩니다!",
        "results": results
    }


@router.get("/user-status/{user_id}")
async def check_user_status(user_id: str):
    """
    Check if user is blocked or has flagged fields
    
    Call before showing user in matches
    """
    if _feedback_system is None:
        raise HTTPException(500, "Feedback system not initialized")
    
    return _feedback_system.check_user_status(user_id)


@router.get("/user-notification/{user_id}")
async def get_user_notification(user_id: str):
    """
    Get notification for user if they need to update their profile
    
    Returns null if no action needed
    """
    if _feedback_system is None:
        return None
    
    return _feedback_system.get_user_notification(user_id)


@router.get("/post-meeting-prompt/{met_user_id}")
async def get_post_meeting_prompt(met_user_id: str, user_id: str):
    """
    Get the UI prompt for post-meeting feedback
    
    Called when user indicates they met someone
    """
    if _feedback_system is None:
        raise HTTPException(500, "Feedback system not initialized")
    
    return _feedback_system.get_post_meeting_prompt(user_id, met_user_id)


@router.post("/profile-updated")
async def notify_profile_updated(user_id: str, updated_fields: List[str]):
    """
    Notify system that user updated their profile
    
    May unblock user if they corrected flagged fields
    """
    if _feedback_system is None:
        return {"status": "ok"}
    
    _feedback_system.user_updated_profile(user_id, updated_fields)
    
    return {
        "status": "updated",
        "message": "프로필이 업데이트되었습니다"
    }


# ==========================================
# A/B Testing Endpoints
# ==========================================

@router.post("/ab/get-variant")
async def get_ab_variant(request: ABVariantRequest):
    """
    Get the A/B test variant for a user
    
    Uses consistent hashing - same user always gets same variant
    """
    if _ab_framework is None:
        raise HTTPException(500, "A/B framework not initialized")
    
    variant = _ab_framework.get_variant(
        experiment_id=request.experiment_id,
        user_id=request.user_id
    )
    
    if variant is None:
        return {"variant": None, "in_experiment": False}
    
    return {
        "variant": {
            "id": variant.id,
            "name": variant.name,
            "config": variant.config
        },
        "in_experiment": True
    }


@router.post("/ab/record-conversion")
async def record_ab_conversion(request: ABConversionRequest):
    """Record a conversion for A/B testing"""
    if _ab_framework is None:
        raise HTTPException(500, "A/B framework not initialized")
    
    _ab_framework.record_conversion(
        experiment_id=request.experiment_id,
        user_id=request.user_id,
        value=request.metric_value
    )
    
    return {"status": "recorded"}


@router.get("/ab/results/{experiment_id}")
async def get_ab_results(experiment_id: str):
    """Get A/B test results"""
    if _ab_framework is None:
        raise HTTPException(500, "A/B framework not initialized")
    
    return _ab_framework.get_results(experiment_id)


@router.get("/ab/experiments")
async def list_experiments():
    """List all experiments"""
    if _ab_framework is None:
        return {"experiments": []}
    
    return {
        "experiments": [
            {
                "id": exp.id,
                "name": exp.name,
                "status": exp.status.value,
                "variants": len(exp.variants)
            }
            for exp in _ab_framework.experiments.values()
        ]
    }
