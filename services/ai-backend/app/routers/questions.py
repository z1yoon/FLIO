"""
Adaptive Question Generation API Routes
Uses Qwen2.5-7B for Korean language understanding
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyzeAnswerRequest(BaseModel):
    question: str
    answer: str


class AnalyzeAnswerResponse(BaseModel):
    clarity_score: int
    sentiment: str
    key_info: List[str]
    is_vague: bool
    needs_followup: bool
    followup_reason: Optional[str]


class GenerateQuestionsRequest(BaseModel):
    question: str
    answer: str
    user_profile: Dict[str, Any]
    num_questions: int = 3


class QuestionItem(BaseModel):
    question: str
    category: str
    priority: str
    goal: str


class GenerateQuestionsResponse(BaseModel):
    questions: List[QuestionItem]


class ReshuffleAnalysisRequest(BaseModel):
    user_profile: Dict[str, Any]
    current_filters: Dict[str, Any]
    reshuffle_reason: str
    rejected_profiles: Optional[List[Dict[str, Any]]] = None


class SuggestedQuestion(BaseModel):
    question: str
    category: str
    reason: str


class FilterSuggestions(BaseModel):
    age_range: Optional[List[int]] = None
    location_radius_km: Optional[int] = None
    priority_changes: Optional[List[str]] = None


class ReshuffleAnalysisResponse(BaseModel):
    analysis: str
    user_intent: str
    missing_info: List[str]
    needs_questions: bool
    suggested_questions: List[SuggestedQuestion]
    filter_suggestions: FilterSuggestions
    avatar_message: str


class MatchExplanationRequest(BaseModel):
    profile_a: Dict[str, Any]
    profile_b: Dict[str, Any]
    match_score: float


class MatchPoint(BaseModel):
    category: str
    type: str
    icon: str
    description: str


class MatchExplanationResponse(BaseModel):
    summary: str
    match_points: List[MatchPoint]
    conversation_starters: List[str]


# Global model instance (loaded on startup)
_question_generator = None


def get_question_generator():
    global _question_generator
    if _question_generator is None:
        from app.models.question_generator import AdaptiveQuestionGenerator
        _question_generator = AdaptiveQuestionGenerator()
    return _question_generator


@router.post("/analyze", response_model=AnalyzeAnswerResponse)
async def analyze_answer(request: AnalyzeAnswerRequest):
    """
    Analyze user's answer for clarity and extract key information
    
    This helps determine if we need follow-up questions
    
    - **question**: The question that was asked
    - **answer**: User's answer to analyze
    
    Returns clarity score, sentiment, and whether follow-up is needed
    """
    try:
        generator = get_question_generator()
        result = generator.analyze_answer(request.question, request.answer)
        
        return AnalyzeAnswerResponse(
            clarity_score=result.get("clarity_score", 50),
            sentiment=result.get("sentiment", "neutral"),
            key_info=result.get("key_info", []),
            is_vague=result.get("is_vague", True),
            needs_followup=result.get("needs_followup", True),
            followup_reason=result.get("followup_reason")
        )
    except Exception as e:
        logger.error(f"Answer analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=GenerateQuestionsResponse)
async def generate_followup_questions(request: GenerateQuestionsRequest):
    """
    Generate follow-up questions based on user's vague answer
    
    This is the core feature that makes FLIO different:
    - Acts like a 결혼정보회사 매니저
    - Digs deeper into vague answers
    - Non-judgmental AI encourages honesty
    
    - **question**: Original question
    - **answer**: User's answer (possibly vague)
    - **user_profile**: Current profile data
    - **num_questions**: Number of questions to generate (default 3)
    """
    try:
        generator = get_question_generator()
        questions = generator.generate_followup_questions(
            question=request.question,
            answer=request.answer,
            user_profile=request.user_profile,
            num_questions=request.num_questions
        )
        
        return GenerateQuestionsResponse(
            questions=[QuestionItem(**q) for q in questions]
        )
    except Exception as e:
        logger.error(f"Question generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reshuffle-analysis", response_model=ReshuffleAnalysisResponse)
async def analyze_reshuffle_request(request: ReshuffleAnalysisRequest):
    """
    Analyze why user wants to reshuffle and suggest improvements
    
    When user is unsatisfied with current matches:
    1. Understand WHY they're unsatisfied
    2. Identify missing profile information
    3. Suggest additional questions if needed
    4. Adjust filters for better results
    
    - **user_profile**: Current user profile
    - **current_filters**: Current matching filters
    - **reshuffle_reason**: User's reason for reshuffling
    - **rejected_profiles**: Recently rejected profiles (optional)
    """
    try:
        generator = get_question_generator()
        result = generator.analyze_reshuffle_request(
            user_profile=request.user_profile,
            current_filters=request.current_filters,
            reshuffle_reason=request.reshuffle_reason,
            rejected_profiles=request.rejected_profiles
        )
        
        # Parse filter suggestions
        filter_data = result.get("filter_suggestions", {})
        filter_suggestions = FilterSuggestions(
            age_range=filter_data.get("age_range"),
            location_radius_km=filter_data.get("location_radius_km"),
            priority_changes=filter_data.get("priority_changes")
        )
        
        return ReshuffleAnalysisResponse(
            analysis=result.get("analysis", ""),
            user_intent=result.get("user_intent", ""),
            missing_info=result.get("missing_info", []),
            needs_questions=result.get("needs_questions", False),
            suggested_questions=[
                SuggestedQuestion(**q) 
                for q in result.get("suggested_questions", [])
            ],
            filter_suggestions=filter_suggestions,
            avatar_message=result.get("avatar_message", "")
        )
    except Exception as e:
        logger.error(f"Reshuffle analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match-explanation", response_model=MatchExplanationResponse)
async def generate_match_explanation(request: MatchExplanationRequest):
    """
    Generate human-readable explanation for why two profiles match
    
    - **profile_a**: First user's profile
    - **profile_b**: Second user's profile
    - **match_score**: Calculated match percentage
    
    Returns summary, match points, and conversation starters
    """
    try:
        generator = get_question_generator()
        result = generator.generate_match_explanation(
            profile_a=request.profile_a,
            profile_b=request.profile_b,
            match_score=request.match_score
        )
        
        return MatchExplanationResponse(
            summary=result.get("summary", ""),
            match_points=[
                MatchPoint(**mp) 
                for mp in result.get("match_points", [])
            ],
            conversation_starters=result.get("conversation_starters", [])
        )
    except Exception as e:
        logger.error(f"Match explanation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
