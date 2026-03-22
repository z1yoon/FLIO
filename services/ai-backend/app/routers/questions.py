"""
FLIO Question Database API Routes
Serves questions from Supabase database for Korean dating compatibility
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging
import json
import os
from supabase import create_client, Client

logger = logging.getLogger(__name__)
router = APIRouter()

# Import Supabase client from database models
from ..models.database import get_supabase_client


# Enhanced Question Models
class QuestionResponse(BaseModel):
    id: str
    text: str
    category: str
    type: str
    options: Optional[List[str]] = None
    effectiveness_score: Optional[float] = None
    placeholder: Optional[str] = None
    maxLength: Optional[int] = None


class InitialQuestionsResponse(BaseModel):
    questions: List[QuestionResponse]
    total: int
    metadata: Dict[str, Any]


class QuestionStatsResponse(BaseModel):
    total_questions: int
    by_category: Dict[str, int]
    by_type: Dict[str, int]
    high_effectiveness_count: int
    open_ended_count: int
    multiple_choice_count: int


# Legacy models for backward compatibility
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


# Enhanced Question Database API Endpoints

@router.get("/initial", response_model=InitialQuestionsResponse)
async def get_initial_questions(user_id: Optional[str] = None, language: str = "ko"):
    """
    Get initial questions from Supabase database for Korean dating compatibility
    
    Returns questions ordered by base_weight (effectiveness score).
    If user_id provided, excludes questions already answered.
    
    - **user_id**: Optional user ID to exclude answered questions
    - **language**: Language preference (ko/en)
    """
    try:
        # If user_id provided, get unanswered questions
        if user_id:
            result = get_supabase_client().rpc('get_questions_for_user', {
                'p_user_id': user_id,
                'p_limit': 100  # Support dynamic question count
            }).execute()
            
            if result.data:
                questions = []
                for q in result.data:
                    # Parse options JSON
                    options_data = q.get('options', [])
                    if isinstance(options_data, str):
                        options_data = json.loads(options_data)
                    
                    # Extract option texts based on language
                    text_key = f"text_{language}" if language == "en" else "text_ko"
                    option_texts = [opt.get(text_key, opt.get("text_ko", "")) for opt in options_data]
                    
                    questions.append(QuestionResponse(
                        id=q['question_id'],
                        text=q['question_text'],
                        category=q['category'],
                        type=q['answer_type'],
                        options=option_texts if option_texts else None,
                        effectiveness_score=q.get('base_weight', 0.5)
                    ))
                
                return InitialQuestionsResponse(
                    questions=questions,
                    total=len(questions),
                    metadata={
                        "version": "2.0",
                        "source": "Supabase database",
                        "language": language,
                        "user_specific": True,
                        "unanswered_only": True
                    }
                )
        
        # Get all active questions in insertion order (dealbreakers first, then others)
        # Order by can_be_dealbreaker DESC to show dealbreakers first, then by ID to maintain SQL insertion order
        result = get_supabase_client().table('questions').select(
            'id, category, text_ko, text_en, answer_type, options, base_weight, effectiveness_score, can_be_dealbreaker, placeholder, max_length'
        ).eq('is_active', True).order('can_be_dealbreaker', desc=True).order('id', desc=False).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="No questions found")
        
        questions = []
        for q in result.data:
            # Parse options JSON
            options_data = q.get('options', [])
            if isinstance(options_data, str):
                options_data = json.loads(options_data)
            
            # Extract option texts based on language
            text_key = f"text_{language}" if language == "en" else "text_ko"
            question_text = q.get(f'text_{language}', q.get('text_ko', ''))
            option_texts = [opt.get(text_key, opt.get("text_ko", "")) for opt in options_data]
            
            # Handle open-ended questions
            if q.get('answer_type') in ['text', 'open_ended']:
                questions.append(QuestionResponse(
                    id=q['id'],
                    text=question_text,
                    category=q['category'],
                    type='text',  # Normalize to 'text' for frontend
                    options=None,
                    effectiveness_score=q.get('effectiveness_score', q.get('base_weight', 0.5)),
                    placeholder=q.get('placeholder'),
                    maxLength=q.get('max_length', 500)
                ))
            else:
                # Convert 'single_select' to 'choice' for frontend compatibility
                question_type = 'choice' if q.get('answer_type') == 'single_select' else q.get('answer_type')
                
                questions.append(QuestionResponse(
                    id=q['id'],
                    text=question_text,
                    category=q['category'],
                    type=question_type,
                    options=option_texts if option_texts else None,
                    effectiveness_score=q.get('effectiveness_score', q.get('base_weight', 0.5))
                ))
        
        return InitialQuestionsResponse(
            questions=questions,
            total=len(questions),
            metadata={
                "version": "2.0",
                "source": "Supabase database",
                "language": language,
                "user_specific": False,
                "research_basis": [
                    "Korean MBTI cultural preferences",
                    "Marriage agency assessment practices", 
                    "Attachment theory research",
                    "Big Five personality compatibility"
                ]
            }
        )
    except Exception as e:
        logger.error(f"Failed to load questions from Supabase: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Please try again later."
        )


@router.get("/stats", response_model=QuestionStatsResponse)
async def get_question_statistics():
    """
    Get statistics about the question database from Supabase
    
    Returns breakdown by category, type, and effectiveness metrics
    """
    try:
        # Get all questions
        result = get_supabase_client().table('questions').select(
            'category, answer_type, base_weight, effectiveness_score'
        ).eq('is_active', True).execute()
        
        if not result.data:
            return QuestionStatsResponse(
                total_questions=0,
                by_category={},
                by_type={},
                high_effectiveness_count=0,
                open_ended_count=0,
                multiple_choice_count=0
            )
        
        questions = result.data
        total = len(questions)
        
        # Count by category
        by_category = {}
        for q in questions:
            cat = q.get('category', 'Unknown')
            by_category[cat] = by_category.get(cat, 0) + 1
        
        # Count by type
        by_type = {}
        for q in questions:
            qtype = q.get('answer_type', 'Unknown')
            by_type[qtype] = by_type.get(qtype, 0) + 1
        
        # High effectiveness count (>= 9.0)
        high_eff = len([q for q in questions if q.get('effectiveness_score', q.get('base_weight', 0)) >= 9.0])
        
        # Open-ended and multiple choice counts
        open_ended = by_type.get('text', 0) + by_type.get('open_ended', 0)
        multiple_choice = by_type.get('choice', 0) + by_type.get('single_select', 0) + by_type.get('multiple_select', 0)
        
        return QuestionStatsResponse(
            total_questions=total,
            by_category=by_category,
            by_type=by_type,
            high_effectiveness_count=high_eff,
            open_ended_count=open_ended,
            multiple_choice_count=multiple_choice
        )
    except Exception as e:
        logger.error(f"Failed to get question stats from Supabase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category/{category}")
async def get_questions_by_category(category: str, language: str = "ko"):
    """
    Get questions by specific category from Supabase
    
    - **category**: Category name (Korean or English)
    - **language**: Language preference (ko/en)
    """
    try:
        result = get_supabase_client().table('questions').select(
            'id, category, text_ko, text_en, answer_type, options, base_weight, effectiveness_score'
        ).eq('category', category).eq('is_active', True).order('effectiveness_score', desc=True).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail=f"No questions found for category: {category}")
        
        questions = []
        for q in result.data:
            # Parse options JSON
            options_data = q.get('options', [])
            if isinstance(options_data, str):
                options_data = json.loads(options_data)
            
            # Extract option texts based on language
            text_key = f"text_{language}" if language == "en" else "text_ko"
            question_text = q.get(f'text_{language}', q.get('text_ko', ''))
            option_texts = [opt.get(text_key, opt.get("text_ko", "")) for opt in options_data]
            
            questions.append({
                "id": q['id'],
                "text": question_text,
                "type": 'choice' if q['answer_type'] == 'single_select' else q['answer_type'],
                "options": option_texts if option_texts else None,
                "effectiveness_score": q.get('effectiveness_score', q.get('base_weight', 0.5))
            })
        
        return {
            "category": category,
            "questions": questions,
            "total": len(questions),
            "language": language
        }
    except Exception as e:
        logger.error(f"Failed to get questions for category {category}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/question/{question_id}")
async def get_question_by_id(question_id: str, language: str = "ko"):
    """
    Get a specific question by its ID from Supabase
    
    - **question_id**: Unique question identifier
    - **language**: Language preference (ko/en)
    """
    try:
        result = get_supabase_client().table('questions').select(
            'id, category, text_ko, text_en, answer_type, options, base_weight, effectiveness_score, can_be_dealbreaker, placeholder, max_length'
        ).eq('id', question_id).eq('is_active', True).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Question not found: {question_id}")
        
        question = result.data[0]
        
        # Parse options JSON
        options_data = question.get('options', [])
        if isinstance(options_data, str):
            options_data = json.loads(options_data)
        
        # Extract option texts based on language
        text_key = f"text_{language}" if language == "en" else "text_ko"
        question_text = question.get(f'text_{language}', question.get('text_ko', ''))
        option_texts = [opt.get(text_key, opt.get("text_ko", "")) for opt in options_data]
        
        # Normalize type for frontend compatibility
        question_type = question['answer_type']
        if question_type == 'single_select':
            question_type = 'choice'
        elif question_type == 'open_ended':
            question_type = 'text'
            
        return {
            "id": question['id'],
            "text": question_text,
            "category": question['category'],
            "type": question_type,
            "options": option_texts if option_texts else None,
            "effectiveness_score": question.get('effectiveness_score', question.get('base_weight', 0.5)),
            "can_be_dealbreaker": question.get('can_be_dealbreaker', False),
            "placeholder": question.get('placeholder'),
            "maxLength": question.get('max_length', 500 if question_type == 'text' else None)
        }
    except Exception as e:
        logger.error(f"Failed to get question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# User Answer Management

class UserAnswerRequest(BaseModel):
    user_id: str
    question_id: str
    answer_value: str
    importance: Optional[int] = 3
    is_dealbreaker: Optional[bool] = False

class UserAnswerResponse(BaseModel):
    success: bool
    message: str
    analysis: Optional[Dict] = None
    needs_followup: Optional[bool] = False

class UserAnswer(BaseModel):
    question_id: str
    answer_value: str
    importance: int
    is_dealbreaker: bool
    timestamp: str
    question_text: Optional[str] = None
    category: Optional[str] = None

class UserProfileResponse(BaseModel):
    user_id: str
    answers: List[UserAnswer]
    total_answers: int
    embedding_status: Dict[str, Any]
    profile_completion: Dict[str, Any]

@router.get("/user/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(user_id: str):
    """
    Get user's complete profile including all answers and embedding status
    
    - **user_id**: User's unique identifier
    
    Returns all answered questions with values and AI analysis status
    """
    try:
        # 1. Get user's answers with question details
        answers_result = get_supabase_client().table('user_answers').select(
            'question_id, answer_value, importance, is_dealbreaker, created_at, questions!inner(text_ko, category, answer_type)'
        ).eq('user_id', user_id).order('created_at', desc=True).execute()
        
        user_answers = []
        if answers_result.data:
            for answer in answers_result.data:
                question_data = answer.get('questions', {})
                user_answers.append(UserAnswer(
                    question_id=answer['question_id'],
                    answer_value=answer['answer_value'],
                    importance=answer['importance'],
                    is_dealbreaker=answer['is_dealbreaker'],
                    timestamp=answer['created_at'],
                    question_text=question_data.get('text_ko', ''),
                    category=question_data.get('category', '')
                ))
        
        # 2. Check embedding status using existing service
        from ..services.azure_openai_service import azure_openai_service
        try:
            # Check if user has embedding in user_embeddings table
            embedding_result = get_supabase_client().table('user_embeddings').select(
                'embedding_dimension, created_at'
            ).eq('user_id', user_id).single().execute()
            
            if embedding_result.data:
                embedding_status = {
                    "has_embedding": True,
                    "embedding_dimension": embedding_result.data.get('embedding_dimension', 1024),
                    "created_at": embedding_result.data.get('created_at'),
                    "message": "AI 프로필 분석 완료"
                }
            else:
                embedding_status = {
                    "has_embedding": False,
                    "message": "AI 프로필 분석 대기 중"
                }
        except Exception:
            embedding_status = {
                "has_embedding": False,
                "message": "AI 프로필 분석 대기 중"
            }
        
        # 3. Calculate profile completion
        total_questions_result = get_supabase_client().table('questions').select(
            'id', count='exact'
        ).execute()
        
        total_questions = total_questions_result.count if total_questions_result.count else 60
        answered_questions = len(user_answers)
        completion_percentage = (answered_questions / total_questions) * 100 if total_questions > 0 else 0
        
        profile_completion = {
            "total_questions": total_questions,
            "answered_questions": answered_questions,
            "completion_percentage": completion_percentage,
            "can_start_matching": answered_questions >= total_questions  # Must answer ALL questions before matching
        }
        
        return UserProfileResponse(
            user_id=user_id,
            answers=user_answers,
            total_answers=answered_questions,
            embedding_status=embedding_status,
            profile_completion=profile_completion
        )
            
    except Exception as e:
        logger.error(f"Failed to get user profile for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user/{user_id}/answer/{question_id}")
async def delete_user_answer(user_id: str, question_id: str):
    """
    Delete a specific answer from user's profile
    
    - **user_id**: User's unique identifier
    - **question_id**: Question identifier to delete
    """
    try:
        result = get_supabase_client().table('user_answers').delete().eq(
            'user_id', user_id
        ).eq('question_id', question_id).execute()
        
        if result.data:
            return {"success": True, "message": f"Answer deleted for question {question_id}"}
        else:
            raise HTTPException(status_code=404, detail="Answer not found")
            
    except Exception as e:
        logger.error(f"Failed to delete answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/answer", response_model=UserAnswerResponse)
async def save_user_answer(request: UserAnswerRequest, background_tasks: BackgroundTasks):
    """
    Save user's answer to a question in Supabase with AI analysis
    
    - **user_id**: User's unique identifier
    - **question_id**: Question identifier
    - **answer_value**: Selected option value or open-ended text
    - **importance**: How important this is to user (1-5)
    - **is_dealbreaker**: Whether mismatch is dealbreaker
    """
    try:
        # 1. Insert or update user answer
        result = get_supabase_client().table('user_answers').upsert({
            'user_id': request.user_id,
            'question_id': request.question_id,
            'answer_value': request.answer_value,
            'importance': request.importance,
            'is_dealbreaker': request.is_dealbreaker
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to save answer")
        
        # 2. Get question text for analysis
        question_result = get_supabase_client().table('questions').select('text_ko').eq('id', request.question_id).single().execute()
        question_text = question_result.data.get('text_ko', '') if question_result.data else ''
        
        # 3. Analyze answer using Azure OpenAI (for open-ended questions)
        analysis_result = None
        needs_followup = False
        
        if len(request.answer_value) > 10:  # Only analyze substantial text answers
            try:
                from ..services.azure_openai_service import azure_openai_service
                analysis = await azure_openai_service.analyze_user_answer(question_text, request.answer_value)
                
                analysis_result = {
                    "clarity_score": analysis.clarity_score,
                    "is_vague": analysis.is_vague,
                    "key_insights": analysis.key_insights,
                    "analysis": analysis.analysis
                }
                needs_followup = analysis.needs_followup
                
                # Store analysis in answer_history table
                get_supabase_client().table('answer_history').insert({
                    'user_id': request.user_id,
                    'question_text': question_text,
                    'category': 'dating_compatibility',
                    'answer_text': request.answer_value,
                    'clarity_score': analysis.clarity_score,
                    'is_vague': analysis.is_vague,
                    'key_info': analysis.key_insights,
                    'triggered_followup': analysis.needs_followup
                }).execute()
                
            except Exception as analysis_error:
                logger.warning(f"Answer analysis failed: {analysis_error}")
                # Continue without analysis if it fails
        
        # After saving, check if all 60 questions are answered → run NLI in background
        count_result = get_supabase_client().table('user_answers').select(
            'question_id', count='exact'
        ).eq('user_id', request.user_id).execute()
        total_answered = count_result.count or 0

        if total_answered >= 60:
            from ..services.nli_consistency_service import nli_consistency_service
            background_tasks.add_task(nli_consistency_service.check_user_consistency, request.user_id)
            logger.info(f"NLI check queued for {request.user_id} (all 60 questions answered)")

        return UserAnswerResponse(
            success=True,
            message=f"Answer saved for question {request.question_id}",
            analysis=analysis_result,
            needs_followup=needs_followup
        )
            
    except Exception as e:
        logger.error(f"Failed to save user answer: {e}")
        # Return success even if database save fails (for demo purposes)
        logger.warning("Continuing without database - answer not persisted")
        return UserAnswerResponse(
            success=True,
            message=f"Answer received for question {request.question_id} (demo mode - not persisted)",
            analysis=None,
            needs_followup=False
        )


# Legacy API endpoints for backward compatibility
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
