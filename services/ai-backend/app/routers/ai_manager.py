"""
FLIO AI Manager Router
Endpoints for conversational AI manager, profile diagnostics,
follow-up question generation, and structured match feedback.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging

from ..services.ai_manager_service import ai_manager_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class FollowupRequest(BaseModel):
    user_id: str
    question_id: str
    question_text: str
    answer: str
    question_category: str
    previous_answers: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class FollowupResponse(BaseModel):
    is_ambiguous: bool
    ambiguity_score: float
    followup_question: Optional[str] = None
    followup_example: Optional[str] = None
    reason: str
    log_id: Optional[str] = None


class SaveFollowupAnswerRequest(BaseModel):
    log_id: str
    answer: str


class DiagnoseProfileRequest(BaseModel):
    user_id: str
    force_refresh: bool = False


class DiagnosticIssueOut(BaseModel):
    severity: str
    issue: str
    impact: str
    solution: str


class DiagnoseProfileResponse(BaseModel):
    overall_score: int
    issues: List[DiagnosticIssueOut]
    recommendations: List[str]
    estimated_improvement_pct: int
    market_percentile: int
    summary_message: str


class MatchFeedbackRequest(BaseModel):
    user_id: str
    match_user_id: str
    overall_rating: int = Field(ge=1, le=5)
    dimension_ratings: Optional[Dict[str, int]] = Field(default_factory=dict)
    positive_aspects: Optional[List[str]] = Field(default_factory=list)
    dealbreaker_aspects: Optional[List[str]] = Field(default_factory=list)
    free_text_feedback: Optional[str] = None
    implicit_signals: Optional[Dict[str, Any]] = None


class MatchFeedbackResponse(BaseModel):
    success: bool
    message: str
    needs_diagnosis: bool


class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    suggested_actions: List[str]
    intent_detected: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/followup-question", response_model=FollowupResponse)
async def get_followup_question(request: FollowupRequest):
    """
    Detect ambiguity in a user's answer and generate a context-aware follow-up question.

    Call this after the user submits an answer during onboarding questions.
    If the answer is clear (ambiguity_score < 0.55), followup_question will be null.

    - **question_id**: The question being answered
    - **answer**: The user's answer text
    - **previous_answers**: List of previous {question_id, question_text, answer_value} for context
    """
    try:
        result = await ai_manager_service.detect_ambiguity_and_followup(
            question_text=request.question_text,
            answer=request.answer,
            question_category=request.question_category,
            previous_answers=request.previous_answers,
        )

        log_id = None
        if result.is_ambiguous and result.followup:
            log_id = await ai_manager_service.log_followup(
                user_id=request.user_id,
                question_id=request.question_id,
                original_answer=request.answer,
                ambiguity_score=result.score,
                followup_question=result.followup,
            )

        return FollowupResponse(
            is_ambiguous=result.is_ambiguous,
            ambiguity_score=round(result.score, 3),
            followup_question=result.followup,
            reason=result.reason,
            log_id=log_id,
        )

    except Exception as e:
        logger.error(f"followup-question endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/followup-question/answer")
async def save_followup_answer(request: SaveFollowupAnswerRequest):
    """
    Save the user's answer to a follow-up question.
    Call this when user responds to the generated follow-up.
    """
    try:
        await ai_manager_service.save_followup_answer(request.log_id, request.answer)
        return {"success": True}
    except Exception as e:
        logger.error(f"save_followup_answer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diagnose-profile", response_model=DiagnoseProfileResponse)
async def diagnose_profile(request: DiagnoseProfileRequest):
    """
    Run a full AI-powered profile quality diagnosis.

    Returns scored issues with actionable solutions and market positioning.
    Triggered automatically when:
    - User's match rating falls below 3.0 for 3+ consecutive matches
    - User requests profile improvement
    - Profile diagnostics cache is stale

    - **force_refresh**: Bypass cached results and run fresh diagnosis
    """
    try:
        if not request.force_refresh:
            from ..models.database import get_supabase_client
            cached = get_supabase_client().table("profile_diagnostics").select(
                "overall_score, issues, recommendations, estimated_match_improvement_pct, market_percentile, is_stale"
            ).eq("user_id", request.user_id).execute()

            if cached.data and not cached.data[0].get("is_stale"):
                import json
                row = cached.data[0]
                issues_raw = row.get("issues", "[]")
                if isinstance(issues_raw, str):
                    issues_raw = json.loads(issues_raw)
                recs_raw = row.get("recommendations", "[]")
                if isinstance(recs_raw, str):
                    recs_raw = json.loads(recs_raw)
                score = row["overall_score"]
                return DiagnoseProfileResponse(
                    overall_score=score,
                    issues=[DiagnosticIssueOut(**i) for i in issues_raw],
                    recommendations=recs_raw,
                    estimated_improvement_pct=row.get("estimated_match_improvement_pct", 0) or 0,
                    market_percentile=row.get("market_percentile", 50) or 50,
                    summary_message=_build_summary_message(score),
                )

        result = await ai_manager_service.diagnose_profile(request.user_id)
        return DiagnoseProfileResponse(
            overall_score=result.overall_score,
            issues=[DiagnosticIssueOut(**i.to_dict()) for i in result.issues],
            recommendations=result.recommendations,
            estimated_improvement_pct=result.estimated_improvement_pct,
            market_percentile=result.market_percentile,
            summary_message=_build_summary_message(result.overall_score),
        )

    except Exception as e:
        logger.error(f"diagnose-profile endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _build_summary_message(score: int) -> str:
    if score >= 80:
        return "프로필이 매우 잘 작성되어 있습니다! 매칭 품질이 높을 것으로 예상됩니다."
    elif score >= 60:
        return "프로필이 양호하나 몇 가지 개선으로 매칭 품질을 크게 높일 수 있습니다."
    elif score >= 40:
        return "프로필 개선이 필요합니다. 아래 제안을 따르면 매칭 품질이 크게 향상됩니다."
    else:
        return "프로필이 미완성 상태입니다. 우선순위가 높은 문제부터 해결해주세요."


@router.post("/feedback", response_model=MatchFeedbackResponse)
async def submit_match_feedback(request: MatchFeedbackRequest):
    """
    Submit structured feedback after viewing / interacting with a match.

    This feedback is used to:
    1. Learn per-user question importance weights
    2. Improve future match recommendations
    3. Trigger profile diagnostics if satisfaction is consistently low

    - **overall_rating**: 1-5 overall satisfaction
    - **dimension_ratings**: {values_alignment, lifestyle_match, conversation_comfort, marriage_seriousness}
    - **positive_aspects**: e.g. ["가치관 일치", "대화 편안함"]
    - **dealbreaker_aspects**: e.g. ["종교 차이", "거리 문제"]
    """
    try:
        result = await ai_manager_service.process_match_feedback(
            user_id=request.user_id,
            match_user_id=request.match_user_id,
            overall_rating=request.overall_rating,
            dimension_ratings=request.dimension_ratings or {},
            positive_aspects=request.positive_aspects or [],
            dealbreaker_aspects=request.dealbreaker_aspects or [],
            free_text=request.free_text_feedback,
            implicit_signals=request.implicit_signals,
        )
        return MatchFeedbackResponse(**result)
    except Exception as e:
        logger.error(f"feedback endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def ai_manager_chat(request: ChatRequest):
    """
    Conversational AI marriage manager.

    Acts like a real marriage agency counselor:
    - Collects relationship goals and timeline through conversation
    - Explains match recommendations with evidence
    - Coaches on profile improvement
    - Analyses repeated dissatisfaction and suggests fixes
    - Emotionally supports the user's journey

    - **session_id**: Optional, resumes existing session. Omit to start new.
    """
    try:
        result = await ai_manager_service.chat(
            user_id=request.user_id,
            user_message=request.message,
            session_id=request.session_id,
        )
        return ChatResponse(
            session_id=result["session_id"],
            message=result["message"],
            suggested_actions=result.get("suggested_actions", []),
            intent_detected=result.get("intent_detected", "general"),
        )
    except Exception as e:
        logger.error(f"chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CoachingResponse(BaseModel):
    has_coaching: bool
    message: Optional[str] = None
    coaching_type: Optional[str] = None
    suggested_actions: List[str] = []


@router.get("/coaching/{user_id}", response_model=CoachingResponse)
async def get_proactive_coaching(user_id: str):
    """
    Get proactive coaching message for a user.

    Call on app open or periodically. Returns a coaching message if
    a trigger condition is met (inactivity, low satisfaction, incomplete profile, etc.).
    If no coaching is needed, has_coaching will be false.
    """
    try:
        result = await ai_manager_service.generate_proactive_coaching(user_id)
        return CoachingResponse(**result)
    except Exception as e:
        logger.error(f"coaching endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{user_id}")
async def get_session_history(user_id: str, limit: int = 20):
    """
    Get the latest AI manager conversation history for a user.
    Returns the last N messages from the active session.
    """
    try:
        from ..models.database import get_supabase_client
        result = get_supabase_client().table("ai_manager_sessions").select(
            "id, messages, session_type, last_message_at"
        ).eq("user_id", user_id).eq("is_active", True).order(
            "last_message_at", desc=True
        ).limit(1).execute()

        if not result.data:
            return {"session_id": None, "messages": [], "has_history": False}

        import json
        session = result.data[0]
        messages = session.get("messages", [])
        if isinstance(messages, str):
            messages = json.loads(messages)

        return {
            "session_id": session["id"],
            "messages": messages[-limit:],
            "has_history": len(messages) > 0,
            "session_type": session.get("session_type", "general"),
            "last_message_at": session.get("last_message_at"),
        }
    except Exception as e:
        logger.error(f"get session history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
