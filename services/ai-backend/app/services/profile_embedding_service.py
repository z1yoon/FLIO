"""
FLIO Profile Embedding Service
Converts user answers into embeddings for matching
Uses translation to English for cost optimization
"""

import asyncio
import json
from typing import Dict, List, Tuple, Optional, Any
from pydantic import BaseModel
import logging

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .azure_openai_service import azure_openai_service
from .translation_service import get_translation_service
from ..models.database import get_supabase_client

logger = logging.getLogger(__name__)

class UserProfile(BaseModel):
    user_id: str
    nickname: str
    age: int
    answers: Dict[str, str]
    profile_text: str
    embedding: List[float]
    last_updated: str

class MatchResult(BaseModel):
    user_id: str
    compatibility_score: float
    similarity_score: float
    cultural_bonus: float
    name: Optional[str] = None
    age: Optional[int] = None
    # Trust Score fields (Korean marriage agency style)
    trust_tier: Optional[str] = None
    trust_score: Optional[float] = None
    verified_items: Optional[List[str]] = None

class ProfileEmbeddingService:
    """
    Service to manage user profile embeddings for dating compatibility
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.embedding_dimension = 1024  # Azure OpenAI text-embedding-3-large
    
    async def build_profile_text(self, user_answers: Dict[str, str], user_id: Optional[str] = None) -> str:
        """
        Build profile text for embedding from open-ended question answers.
        If a follow-up answer exists for a question (from followup_question_log),
        it is appended to the original answer so the richer context is embedded.
        Static choice questions are handled by exact matching, not embeddings.
        """
        text_question_ids = [
            'personal_values_lifestyle',
            'ideal_relationship_dynamic',
            'conflict_growth_philosophy',
        ]

        # Fetch follow-up answers for this user's text questions (if user_id provided)
        followup_answers: Dict[str, str] = {}
        if user_id:
            try:
                result = self.supabase.table('followup_question_log').select(
                    'question_id, followup_answer'
                ).eq('user_id', user_id).in_(
                    'question_id', text_question_ids
                ).not_.is_('followup_answer', 'null').execute()
                for row in (result.data or []):
                    if row.get('followup_answer'):
                        followup_answers[row['question_id']] = row['followup_answer']
            except Exception as e:
                logger.warning(f"Could not fetch follow-up answers for {user_id}: {e}")

        text_answers = []
        for qid in text_question_ids:
            if qid in user_answers and user_answers[qid]:
                answer = user_answers[qid].strip()
                if answer:
                    # Append follow-up context if available
                    if qid in followup_answers:
                        answer = f"{answer} {followup_answers[qid].strip()}"
                    text_answers.append(answer)

        if not text_answers:
            return "한국인 결혼 대상자 프로필: 프로필 작성 중"

        full_profile = " | ".join(text_answers)
        return f"한국인 결혼 대상자 프로필: {full_profile}"
    
    # Removed: _build_personality_section, _build_values_section, 
    # _build_relationship_section, _build_communication_section
    # These methods extracted keywords from static choice questions,
    # which is redundant since static questions are exact-matched (60% of score)
    # Only the 5 open-ended text questions need embedding for semantic similarity
    
    async def create_user_profile_embedding(self, user_id: str) -> UserProfile:
        """
        Create embedding for a user's profile based on their answers
        Main entry point for profile embedding generation
        
        Cost optimization: Translates Korean text to English before embedding generation
        to reduce token costs by ~60%
        """
        try:
            # 1. Fetch user answers from Supabase
            user_answers = await self._fetch_user_answers(user_id)
            user_info = await self._fetch_user_info(user_id)
            
            if not user_answers:
                raise ValueError(f"No answers found for user {user_id}")
            
            # 2. Build profile text (Korean), including any follow-up answers
            profile_text_korean = await self.build_profile_text(user_answers, user_id=user_id)
            logger.info(f"Built Korean profile text: {len(profile_text_korean)} chars")
            
            # 3. Translate to English for cost-efficient embedding
            translation_service = get_translation_service()
            profile_text_english = await translation_service.translate_to_english(profile_text_korean)
            logger.info(f"Translated to English: {len(profile_text_english)} chars")
            
            # 4. Generate embedding using Azure OpenAI (on English text)
            embedding_response = await azure_openai_service.generate_profile_embedding(profile_text_english)
            logger.info(f"Generated embedding with {len(embedding_response.embedding)} dimensions")
            
            # 5. Store embedding in Supabase (store Korean text for display)
            await self._store_user_embedding(user_id, embedding_response.embedding, profile_text_korean)
            
            # 6. Return user profile
            return UserProfile(
                user_id=user_id,
                nickname=user_info.get('nickname', 'Unknown'),
                age=user_info.get('age', 0),
                answers=user_answers,
                profile_text=profile_text_korean,  # Store Korean for display
                embedding=embedding_response.embedding,
                last_updated=user_info.get('updated_at', '')
            )
            
        except Exception as e:
            logger.error(f"Failed to create embedding for user {user_id}: {e}")
            raise Exception(f"Profile embedding creation failed: {str(e)}")
    
    async def find_compatible_matches(
        self,
        user_id: str,
        limit: int = 10,
        excluded_user_ids: List[str] = None,
        apply_trust_filter: bool = True,
        tier_filter: List[str] = None
    ) -> List[MatchResult]:
        """
        Find compatible matches for a user using the database matching function.

        Uses database function find_matches() which implements:
        - Hybrid algorithm: 60% static questions + 20% importance + 20% embeddings
        - Tier filtering (users match within same/lower tiers)
        - Photo verification requirement (REQUIRED)
        - Dealbreaker enforcement (hard filtering on Q001-Q004)

        Ocean Pearl Theme Tiers: 조약돌 → 조개 → 진주 → 산호 → 다이아
        """
        try:
            # Call database function find_matches() which has the correct algorithm
            result = self.supabase.rpc('find_matches', {
                'p_user_id': user_id,
                'p_limit': limit,
                'p_min_compatibility': 0.40  # Minimum 40% compatibility
            }).execute()

            if not result.data:
                logger.info(f"No matches found for user {user_id}")
                return []

            # Convert database results to MatchResult objects
            match_results = []
            for match in result.data:
                # Get profile info for this match
                profile_result = self.supabase.table('profiles').select(
                    'nickname, age'
                ).eq('user_id', match['match_user_id']).single().execute()

                profile_data = profile_result.data if profile_result.data else {}

                # Get trust info for display
                match_trust_tier = None
                match_trust_score = None
                match_verified_items = []

                try:
                    from .trust_score_service import trust_score_service
                    match_trust = await trust_score_service.get_trust_score(match['match_user_id'])
                    if match_trust:
                        match_trust_tier = match_trust.trust_tier
                        match_trust_score = match_trust.total_trust_score

                    match_summary = await trust_score_service.get_trust_summary(match['match_user_id'])
                    match_verified_items = match_summary.verified_items
                except Exception as e:
                    logger.warning(f"Trust info lookup failed for match: {e}")

                match_result = MatchResult(
                    user_id=match['match_user_id'],
                    compatibility_score=float(match['compatibility_score']),
                    similarity_score=float(match['embedding_similarity']),
                    cultural_bonus=0.0,  # Not used in new algorithm
                    name=profile_data.get('nickname'),
                    age=profile_data.get('age'),
                    trust_tier=match_trust_tier,
                    trust_score=match_trust_score,
                    verified_items=match_verified_items
                )
                match_results.append(match_result)

            logger.info(f"Found {len(match_results)} matches for user {user_id}")
            return match_results

        except Exception as e:
            logger.error(f"Failed to find matches for user {user_id}: {e}")
            raise Exception(f"Match finding failed: {str(e)}")
    
    async def get_match_explanation(self, user_a_id: str, user_b_id: str, reshuffle_preference: str = None) -> Dict:
        """
        Generate detailed explanation for why two users match
        Uses statistical analysis for static questions and AI only for open-ended questions
        Can include reshuffle preference context for personalized explanations
        """
        try:
            # Get both user profiles
            user_a_info = await self._fetch_user_profile_summary(user_a_id)
            user_b_info = await self._fetch_user_profile_summary(user_b_id)
            
            # Get user answers with metadata
            user_a_answers = await self._fetch_user_answers_with_metadata(user_a_id)
            user_b_answers = await self._fetch_user_answers_with_metadata(user_b_id)
            
            # Calculate compatibility score
            compatibility = await self._calculate_compatibility(user_a_id, user_b_id)
            
            # Generate statistical analysis for static questions
            static_analysis = await self._generate_statistical_analysis(
                user_a_answers, user_b_answers, user_a_info, user_b_info
            )
            
            # Get reshuffle context if available
            reshuffle_context = None
            if reshuffle_preference:
                reshuffle_context = await self.get_reshuffle_context(user_a_id)
            
            # Generate AI explanation only for open-ended text questions (Q36-40)
            ai_explanation = await self._generate_ai_explanation_for_text_questions(
                user_a_info, user_b_info, user_a_answers, user_b_answers, 
                compatibility['total_score'], reshuffle_preference, reshuffle_context
            )
            
            # Debug logging
            if ai_explanation:
                logger.info(f"AI explanation type: {type(ai_explanation)}")
                logger.info(f"AI explanation attributes: {dir(ai_explanation) if hasattr(ai_explanation, '__dict__') else 'No __dict__'}")
                if hasattr(ai_explanation, '__dict__'):
                    logger.info(f"AI explanation dict: {ai_explanation.__dict__}")
                elif hasattr(ai_explanation, 'dict'):
                    try:
                        logger.info(f"AI explanation dict(): {ai_explanation.dict()}")
                    except Exception as e:
                        logger.error(f"Error calling dict(): {e}")
            
            # Generate personalized matching explanations
            personalized_explanation = await self._generate_personalized_matching_explanation(
                user_a_answers, user_b_answers, user_a_info, user_b_info, compatibility['total_score']
            )

            return {
                "compatibility_score": compatibility['total_score'],
                "explanation": {
                    "summary": static_analysis['summary'],
                    "statistical_insights": static_analysis['insights'],
                    "compatibility_graphs": static_analysis['graphs'],
                    "ai_analysis": self._safe_serialize_ai_explanation(ai_explanation),
                    "personalized_insights": personalized_explanation,
                    "conversation_starters": static_analysis['conversation_starters']
                },
                "detailed_scores": compatibility,
                "score_breakdown": {
                    "static_questions": f"{compatibility.get('static_score', 0):.1%} (60% weight)",
                    "open_ended_embedding": f"{compatibility.get('embedding_score', 0):.1%} (40% weight)",
                    "total": f"{compatibility['total_score']:.1%}"
                },
            }
            
        except Exception as e:
            logger.error(f"Failed to generate explanation for {user_a_id} and {user_b_id}: {e}")
            raise Exception(f"Match explanation generation failed: {str(e)}")
    
    async def _fetch_user_answers(self, user_id: str) -> Dict[str, str]:
        """Fetch user's question answers from Supabase"""
        try:
            result = self.supabase.table('user_answers').select(
                'question_id, answer_value, answer_text'
            ).eq('user_id', user_id).execute()
            
            # Use answer_text for text questions, answer_value for choice questions
            return {
                item['question_id']: item['answer_text'] or item['answer_value'] 
                for item in result.data
            }
        except Exception as e:
            logger.error(f"Failed to fetch answers for user {user_id}: {e}")
            return {}
    
    async def _fetch_user_info(self, user_id: str) -> Dict:
        """Fetch basic user information"""
        try:
            result = self.supabase.table('profiles').select(
                'nickname, birth_date, updated_at'
            ).eq('user_id', user_id).single().execute()
            
            profile = result.data
            # Calculate age from birth_date
            from datetime import datetime
            birth_date = datetime.fromisoformat(profile['birth_date'].replace('Z', '+00:00'))
            age = datetime.now().year - birth_date.year
            
            return {
                'nickname': profile['nickname'],
                'age': age,
                'updated_at': profile['updated_at']
            }
        except Exception as e:
            logger.error(f"Failed to fetch user info for {user_id}: {e}")
            # Return default values when profiles table is not accessible
            from datetime import datetime
            return {
                'nickname': f'User_{user_id[:8]}',
                'age': 25,  # Default age
                'updated_at': datetime.now().isoformat()
            }
    
    async def _store_user_embedding(self, user_id: str, embedding: List[float], profile_text: str):
        """Store user embedding in Supabase using RPC function"""
        try:
            # Convert embedding to pgvector format
            embedding_vector = f"[{','.join(map(str, embedding))}]"
            
            # Use RPC function for better performance and error handling
            result = self.supabase.rpc('store_profile_embedding', {
                'p_user_id': user_id,
                'p_embedding': embedding_vector,
                'p_profile_text': profile_text
            }).execute()
            
            if not result.data:
                raise ValueError(f"Failed to store embedding for user {user_id}")
            
            logger.info(f"Successfully stored embedding for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to store embedding for user {user_id}: {e}")
            raise
    
    async def _get_user_embedding(self, user_id: str) -> List[float]:
        """Get user's embedding from Supabase"""
        try:
            result = self.supabase.table('profiles').select(
                'profile_embedding'
            ).eq('user_id', user_id).single().execute()
            
            embedding_str = result.data['profile_embedding']
            if not embedding_str:
                return None
            
            # Parse pgvector format back to list
            embedding = eval(embedding_str)  # Note: In production, use proper JSON parsing
            return embedding
        except Exception as e:
            logger.error(f"Failed to get embedding for user {user_id}: {e}")
            return None
            
    async def _vector_similarity_search(self, user_id: str, user_embedding: List[float], limit: int, excluded_user_ids: List[str] = None) -> List[Dict]:
        """Use Supabase vector similarity search to find similar profiles
        Excludes specified user IDs at database level to avoid unnecessary API calls"""
        try:
            # Convert embedding to pgvector format
            embedding_str = f"[{','.join(map(str, user_embedding))}]"
            
            # Build list of excluded IDs (any rejected matches)
            all_excluded = excluded_user_ids if excluded_user_ids else []
            
            # Call the RPC function for vector similarity search with exclusions
            result = self.supabase.rpc('find_similar_profiles', {
                'query_embedding': embedding_str,
                'exclude_user_id': user_id,  # Primary exclusion
                'match_limit': limit,
                'excluded_user_ids': all_excluded  # Additional exclusions (rejected matches)
            }).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Vector similarity search failed: {e}")
            return []

# ... (rest of the code remains the same)
    async def _calculate_compatibility(self, user_a_id: str, user_b_id: str) -> Dict[str, float]:
        """
        Calculate detailed compatibility score between two users.

        Hybrid Algorithm:
        - 60% Static question matching (choice questions, with per-user learned weights)
        - 40% Open-ended answer embedding similarity (semantic understanding)
        """
        try:
            embedding_a = await self._get_user_embedding(user_a_id)
            embedding_b = await self._get_user_embedding(user_b_id)

            if not embedding_a or not embedding_b:
                return {'total_score': 0.0, 'embedding_score': 0.0, 'static_score': 0.0}

            # 60%: static choice question matching (uses per-user learned weights)
            static_score = await self._calculate_static_question_score(user_a_id, user_b_id) * 0.6

            # 40%: open-ended answer embedding similarity
            embedding_similarity = cosine_similarity([embedding_a], [embedding_b])[0][0]
            embedding_score = float(embedding_similarity) * 0.4

            total_score = static_score + embedding_score

            return {
                'total_score': min(max(total_score, 0.0), 1.0),
                'embedding_score': embedding_score,
                'static_score': static_score,
                'similarity_score': float(embedding_similarity),
            }

        except Exception as e:
            logger.error(f"Compatibility calculation failed: {e}")
            return {'total_score': 0.0, 'similarity_score': 0.0}
    
    async def _calculate_cultural_bonus(self, user_a_id: str, user_b_id: str) -> float:
        """Calculate Korean cultural compatibility bonus"""
        try:
            # Get user answers for cultural analysis
            answers_a = await self._fetch_user_answers(user_a_id)
            answers_b = await self._fetch_user_answers(user_b_id)
            
            bonus_score = 0.0
            total_comparisons = 0
            
            # Check key cultural compatibility factors
            cultural_questions = [
                'family_values', 'marriage_timeline', 'financial_management',
                'career_family_balance', 'traditional_modern_values'
            ]
            
            for question_id in cultural_questions:
                if question_id in answers_a and question_id in answers_b:
                    # Simple compatibility check (can be made more sophisticated)
                    if answers_a[question_id] == answers_b[question_id]:
                        bonus_score += 0.2
                    total_comparisons += 1
            
            return bonus_score / total_comparisons if total_comparisons > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Cultural bonus calculation failed: {e}")
            return 0.0
    
    async def _calculate_exact_match_rate(self, user_a_id: str, user_b_id: str) -> float:
        """
        Calculate exact match rate (no partial matches) for filtering
        Used for 50% minimum threshold
        """
        try:
            text_question_ids = {
                'personal_values_lifestyle', 'ideal_relationship_dynamic', 'conflict_growth_philosophy'
            }
            
            answers_a = await self._fetch_user_answers(user_a_id)
            answers_b = await self._fetch_user_answers(user_b_id)
            
            exact_matches = 0
            total_questions = 0
            
            for question_id in answers_a.keys():
                if question_id in text_question_ids:
                    continue
                    
                if question_id in answers_b:
                    if answers_a[question_id] == answers_b[question_id]:
                        exact_matches += 1
                    total_questions += 1
            
            exact_rate = exact_matches / total_questions if total_questions > 0 else 0.0
            logger.info(f"Exact match rate: {exact_matches}/{total_questions} = {exact_rate:.1%}")
            return exact_rate
            
        except Exception as e:
            logger.error(f"Exact match calculation failed: {e}")
            return 0.0
    
    async def _calculate_static_question_score(self, user_a_id: str, user_b_id: str) -> float:
        """
        Calculate compatibility based on static choice question matching.
        Applies per-user learned weights (from reshuffle feedback) for personalization.
        Text/open-ended questions are excluded — those go through embedding similarity.
        """
        try:
            text_question_ids = {
                'personal_values_lifestyle', 'ideal_relationship_dynamic', 'conflict_growth_philosophy'
            }

            answers_a = await self._fetch_user_answers(user_a_id)
            answers_b = await self._fetch_user_answers(user_b_id)
            user_weights = await self._get_user_question_weights(user_a_id)

            weighted_score = 0.0
            total_weight = 0.0

            for question_id in answers_a.keys():
                if question_id in text_question_ids:
                    continue
                if question_id in answers_b:
                    weight = user_weights.get(question_id, 1.0)
                    if answers_a[question_id] == answers_b[question_id]:
                        weighted_score += 1.0 * weight
                    elif answers_a[question_id] and answers_b[question_id]:
                        weighted_score += 0.5 * weight
                    total_weight += weight

            score = weighted_score / total_weight if total_weight > 0 else 0.0
            logger.info(f"Static score for {user_a_id}: {score:.1%} (personalized weights applied)")
            return score

        except Exception as e:
            logger.error(f"Static score calculation failed: {e}")
            return 0.0

    async def _get_user_question_weights(self, user_id: str) -> Dict[str, float]:
        """
        Fetch per-user learned question weights from DB.
        Returns empty dict if no weights exist yet (falls back to equal weighting).
        """
        try:
            result = self.supabase.table('user_question_weights').select(
                'question_id, weight'
            ).eq('user_id', user_id).execute()
            return {row['question_id']: row['weight'] for row in (result.data or [])}
        except Exception as e:
            logger.warning(f"Could not fetch question weights for {user_id}: {e}")
            return {}
    
    async def _get_dealbreakers(self, user_id: str) -> Dict[str, str]:
        """
        Get user's dealbreaker questions and their required answers
        
        Only 4 questions can be dealbreakers (hard filters):
        1. gender_preference - 선호하는 상대방 성별
        2. disability_acceptance - 신체적 차이 유무
        3. divorce_status - 상대방 이혼 유무
        4. age_range_preference - 상대방 나이 연령대
        
        All other questions use importance ratings (1-5) for scoring bonus
        """
        try:
            result = self.supabase.table('user_answers').select(
                'question_id, answer_value, answer_text'
            ).eq('user_id', user_id).eq('is_dealbreaker', True).execute()
            
            dealbreakers = {}
            for item in result.data:
                question_id = item['question_id']
                answer = item.get('answer_text') or item.get('answer_value')
                dealbreakers[question_id] = answer
            
            return dealbreakers
            
        except Exception as e:
            logger.error(f"Failed to get dealbreakers for user {user_id}: {e}")
            return {}
    
    async def _check_dealbreaker_compatibility(self, user_a_id: str, user_b_id: str, user_a_dealbreakers: Dict[str, str]) -> bool:
        """
        Check if two users are compatible based on dealbreakers
        Returns True if compatible, False if any dealbreaker is violated
        """
        try:
            if not user_a_dealbreakers:
                return True  # No dealbreakers, all matches are compatible
            
            # Get user B's answers for dealbreaker questions
            result_b = self.supabase.table('user_answers').select(
                'question_id, answer_value, answer_text'
            ).eq('user_id', user_b_id).execute()
            
            answers_b = {item['question_id']: (item.get('answer_text') or item.get('answer_value')) for item in result_b.data}
            
            # Get user profiles for gender and age checks
            profile_a = self.supabase.table('profiles').select('birth_date').eq('user_id', user_a_id).execute()
            profile_b = self.supabase.table('profiles').select('gender, birth_date').eq('user_id', user_b_id).execute()
            
            user_b_gender = profile_b.data[0]['gender'] if profile_b.data else None
            user_a_birth_date = profile_a.data[0]['birth_date'] if profile_a.data else None
            user_b_birth_date = profile_b.data[0]['birth_date'] if profile_b.data else None
            
            # Calculate ages from birth_date
            from datetime import datetime
            user_a_age = None
            user_b_age = None
            if user_a_birth_date:
                birth_date_a = datetime.fromisoformat(user_a_birth_date.replace('Z', '+00:00'))
                user_a_age = datetime.now().year - birth_date_a.year
            if user_b_birth_date:
                birth_date_b = datetime.fromisoformat(user_b_birth_date.replace('Z', '+00:00'))
                user_b_age = datetime.now().year - birth_date_b.year
            
            # Check each dealbreaker
            for question_id, required_answer in user_a_dealbreakers.items():
                # Special handling for gender_preference dealbreaker
                if question_id == 'gender_preference':
                    if required_answer in ['male', 'female'] and user_b_gender != required_answer:
                        logger.info(f"Dealbreaker violated: gender_preference requires {required_answer}, but user B is {user_b_gender}")
                        return False
                    continue
                
                # Special handling for age_range_preference dealbreaker
                if question_id == 'age_range_preference':
                    if user_a_age and user_b_age:
                        age_diff = abs(user_a_age - user_b_age)
                        
                        if required_answer == 'same_age':  # ±2 years
                            if age_diff > 2:
                                logger.info(f"Dealbreaker violated: age_range_preference requires same age ±2, but age diff is {age_diff}")
                                return False
                        elif required_answer == 'younger_5':  # Up to 5 years younger
                            if user_b_age > user_a_age or age_diff > 5:
                                logger.info(f"Dealbreaker violated: age_range_preference requires younger ≤5, but user B is {user_b_age} vs user A {user_a_age}")
                                return False
                        elif required_answer == 'older_5':  # Up to 5 years older
                            if user_b_age < user_a_age or age_diff > 5:
                                logger.info(f"Dealbreaker violated: age_range_preference requires older ≤5, but user B is {user_b_age} vs user A {user_a_age}")
                                return False
                        # 'age_gap_ok' - no filtering needed
                    continue
                
                # Check if user B has answered this question
                if question_id not in answers_b:
                    logger.info(f"Dealbreaker violated: user B has not answered {question_id}")
                    return False
                
                user_b_answer = answers_b[question_id]
                
                # Special handling for disability_acceptance
                if question_id == 'disability_acceptance':
                    # If user A requires open acceptance, check if user B is open
                    if required_answer in ['열린 마음이에요', 'fully_open']:
                        if user_b_answer not in ['열린 마음이에요', 'fully_open']:
                            logger.info(f"Dealbreaker violated: disability_acceptance requires open mind, but user B answered {user_b_answer}")
                            return False
                    continue
                
                # For other dealbreakers, require exact match
                if required_answer != user_b_answer:
                    logger.info(f"Dealbreaker violated: {question_id} requires '{required_answer}', but user B answered '{user_b_answer}'")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Dealbreaker compatibility check failed: {e}")
            return True  # On error, don't filter out (fail open)
    
    async def _calculate_importance_bonus(self, user_a_id: str, user_b_id: str) -> float:
        """
        Calculate bonus based on matching important questions (importance >= 4)
        This applies to all 35 static questions (not just dealbreakers)
        Gives extra weight when both users marked a question as important AND have matching answers
        """
        try:
            # Get user answers with importance levels
            result_a = self.supabase.table('user_answers').select(
                'question_id, answer_value, answer_text, importance, is_dealbreaker'
            ).eq('user_id', user_a_id).execute()
            
            result_b = self.supabase.table('user_answers').select(
                'question_id, answer_value, answer_text, importance, is_dealbreaker'
            ).eq('user_id', user_b_id).execute()
            
            answers_a = {item['question_id']: item for item in result_a.data}
            answers_b = {item['question_id']: item for item in result_b.data}
            
            importance_score = 0.0
            total_important = 0
            
            for question_id in answers_a.keys():
                if question_id in answers_b:
                    answer_a = answers_a[question_id]
                    answer_b = answers_b[question_id]
                    
                    # Check if either marked as important
                    if answer_a.get('importance', 0) >= 4 or answer_b.get('importance', 0) >= 4:
                        # Check if answers match
                        value_a = answer_a.get('answer_text') or answer_a.get('answer_value')
                        value_b = answer_b.get('answer_text') or answer_b.get('answer_value')
                        
                        if value_a == value_b:
                            importance_score += 1.0
                        total_important += 1
            
            return importance_score / total_important if total_important > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Importance bonus calculation failed: {e}")
            return 0.0
    
    async def _fetch_user_answers_with_metadata(self, user_id: str) -> Dict[str, Dict]:
        """Fetch user answers with question metadata for categorization"""
        try:
            # Get answers with question metadata
            result = self.supabase.table('user_answers').select(
                'question_id, answer_value, answer_text, importance, is_dealbreaker'
            ).eq('user_id', user_id).execute()
            
            # Get question categories and types
            questions_result = self.supabase.table('questions').select(
                'id, category, answer_type, options'
            ).execute()
            
            questions_meta = {q['id']: q for q in questions_result.data}
            
            answers_with_meta = {}
            for item in result.data:
                qid = item['question_id']
                answers_with_meta[qid] = {
                    'answer_text': item['answer_text'],
                    'answer_value': item['answer_value'],
                    'importance': item.get('importance', 3),
                    'is_dealbreaker': item.get('is_dealbreaker', False),
                    'category': questions_meta.get(qid, {}).get('category', ''),
                    'answer_type': questions_meta.get(qid, {}).get('answer_type', 'choice'),
                    'options': questions_meta.get(qid, {}).get('options', [])
                }
            
            return answers_with_meta
            
        except Exception as e:
            logger.error(f"Failed to fetch user answers with metadata for {user_id}: {e}")
            return {}
    
    async def _generate_statistical_analysis(self, user_a_answers: Dict, user_b_answers: Dict, 
                                           user_a_info: Dict, user_b_info: Dict) -> Dict:
        """Generate statistical analysis for static questions with graphs and insights"""
        try:
            # Use dynamic categories from actual database
            categories = {}
            
            # Group matching/mismatching questions by category
            for qid in user_a_answers.keys():
                if qid in user_b_answers and user_a_answers[qid]['answer_type'] == 'choice':
                    category = user_a_answers[qid]['category']
                    value_a = user_a_answers[qid]['answer_text'] or user_a_answers[qid]['answer_value']
                    value_b = user_b_answers[qid]['answer_text'] or user_b_answers[qid]['answer_value']
                    
                    match_status = 'match' if value_a == value_b else 'mismatch'
                    importance = max(user_a_answers[qid]['importance'], user_b_answers[qid]['importance'])
                    
                    question_analysis = {
                        'question_id': qid,
                        'match_status': match_status,
                        'importance': importance,
                        'user_a_answer': value_a,
                        'user_b_answer': value_b
                    }
                    
                    # Create category if it doesn't exist
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(question_analysis)
            
            # Calculate category compatibility percentages
            category_stats = {}
            for category, questions in categories.items():
                if questions:
                    matches = sum(1 for q in questions if q['match_status'] == 'match')
                    total = len(questions)
                    percentage = (matches / total) * 100
                    
                    category_stats[category] = {
                        'match_percentage': percentage,
                        'total_questions': total,
                        'matching_questions': matches,
                        'high_importance_matches': sum(1 for q in questions 
                                                     if q['match_status'] == 'match' and q['importance'] >= 4)
                    }
            
            # Generate insights based on statistical patterns
            insights = self._generate_statistical_insights(category_stats, user_a_info, user_b_info)
            
            # Generate conversation starters based on matches
            conversation_starters = self._generate_conversation_starters_from_stats(categories)
            
            # Create summary
            overall_compatibility = sum(stats['match_percentage'] for stats in category_stats.values()) / len(category_stats) if category_stats else 0
            
            user_a_name = user_a_info.get('nickname', '첫 번째 분')
            user_b_name = user_b_info.get('nickname', '두 번째 분')
            
            summary = f"{user_a_name}님과 {user_b_name}님의 전체 호환성은 {overall_compatibility:.0f}%입니다. " \
                     f"특히 {max(category_stats.keys(), key=lambda k: category_stats[k]['match_percentage']) if category_stats else '알 수 없는'} 영역에서 매우 잘 맞으십니다."
            
            return {
                'summary': summary,
                'insights': insights,
                'graphs': category_stats,  # Frontend can use this to create visual charts
                'conversation_starters': conversation_starters
            }
            
        except Exception as e:
            logger.error(f"Statistical analysis generation failed: {e}")
            return {
                'summary': '통계 분석을 생성할 수 없습니다.',
                'insights': [],
                'graphs': {},
                'conversation_starters': []
            }
    
    def _generate_statistical_insights(self, category_stats: Dict, user_a_info: Dict, user_b_info: Dict) -> List[str]:
        """Generate insights based on statistical analysis"""
        insights = []
        user_a_name = user_a_info.get('nickname', '첫 번째 분')
        user_b_name = user_b_info.get('nickname', '두 번째 분')
        
        # Find strongest and weakest compatibility areas
        if category_stats:
            sorted_categories = sorted(category_stats.items(), key=lambda x: x[1]['match_percentage'], reverse=True)
            
            # Strongest area
            strongest_category, strongest_stats = sorted_categories[0]
            insights.append(f"가장 잘 맞는 영역: {strongest_category} ({strongest_stats['match_percentage']:.0f}% 일치)")
            
            # Areas for growth
            if len(sorted_categories) > 1:
                weakest_category, weakest_stats = sorted_categories[-1]
                if weakest_stats['match_percentage'] < 70:
                    insights.append(f"함께 성장할 영역: {weakest_category}에서 서로 다른 관점을 나누며 더 깊이 이해할 수 있습니다")
            
            # High importance matches
            high_importance_total = sum(stats['high_importance_matches'] for stats in category_stats.values())
            if high_importance_total > 0:
                insights.append(f"중요하게 생각하는 가치관에서 {high_importance_total}개 항목이 일치합니다")
        
        return insights
    
    def _generate_conversation_starters_from_stats(self, categories: Dict) -> List[str]:
        """Generate conversation starters based on matching answers"""
        starters = []
        
        # Find interesting matches to discuss
        for category, questions in categories.items():
            matches = [q for q in questions if q['match_status'] == 'match' and q['importance'] >= 3]
            
            if matches and category == '결혼계획':
                starters.append("두 분 모두 비슷한 결혼 계획을 가지고 계시네요. 구체적으로 어떤 가정을 꿈꾸시는지 이야기해보세요")
            elif matches and category == '생활방식':
                starters.append("라이프스타일이 잘 맞으시는 것 같아요. 함께 하고 싶은 취미나 활동이 있을까요?")
            elif matches and category == '가치관':
                starters.append("중요하게 생각하는 가치관이 비슷하시네요. 이런 가치관을 어떻게 키워오셨는지 궁금해요")
        
        # Add default starters if none generated
        if not starters:
            starters = [
                "서로의 일상에 대해 더 자세히 이야기해보세요",
                "앞으로의 꿈이나 목표에 대해 대화해보시면 좋을 것 같아요",
                "취미나 관심사를 공유해보세요"
            ]
        
        return starters[:3]  # Return top 3
    
    async def _generate_ai_explanation_for_text_questions(self, user_a_info: Dict, user_b_info: Dict, 
                                                        user_a_answers: Dict, user_b_answers: Dict,
                                                        compatibility_score: float,
                                                        reshuffle_preference: str = None,
                                                        reshuffle_context: List[Dict] = None) -> Optional[object]:
        """Generate AI explanation only for open-ended text questions
        Can include reshuffle preference to personalize explanation"""
        try:
            # Extract only text questions (personal_values_lifestyle, ideal_relationship_dynamic, conflict_growth_philosophy)
            text_question_ids = [
                'personal_values_lifestyle', 'ideal_relationship_dynamic', 'conflict_growth_philosophy'
            ]
            
            # Filter to only text questions that both users answered
            text_answers_a = {qid: ans for qid, ans in user_a_answers.items() 
                            if qid in text_question_ids and ans['answer_type'] == 'text' 
                            and (ans['answer_text'] or ans['answer_value'])}
            text_answers_b = {qid: ans for qid, ans in user_b_answers.items() 
                            if qid in text_question_ids and ans['answer_type'] == 'text'
                            and (ans['answer_text'] or ans['answer_value'])}
            
            # Only generate AI explanation if both users have answered text questions
            common_text_questions = set(text_answers_a.keys()) & set(text_answers_b.keys())
            
            if not common_text_questions:
                logger.info("No common text questions found, skipping AI explanation")
                return None
            
            # Prepare text answers for AI analysis
            formatted_text_answers_a = {}
            formatted_text_answers_b = {}
            
            for qid in common_text_questions:
                formatted_text_answers_a[qid] = text_answers_a[qid]['answer_text'] or text_answers_a[qid]['answer_value']
                formatted_text_answers_b[qid] = text_answers_b[qid]['answer_text'] or text_answers_b[qid]['answer_value']
            
            # Generate AI explanation using Azure OpenAI (only for text questions)
            explanation = await azure_openai_service.generate_match_explanation(
                user_a_profile=user_a_info,
                user_b_profile=user_b_info,
                compatibility_score=compatibility_score,
                user_a_answers=formatted_text_answers_a,
                user_b_answers=formatted_text_answers_b,
                reshuffle_preference=reshuffle_preference,
                reshuffle_context=reshuffle_context
            )
            
            logger.info(f"Generated AI explanation for {len(common_text_questions)} text questions")
            return explanation
            
        except Exception as e:
            logger.error(f"AI explanation generation failed: {e}")
            return None
    
    def _safe_serialize_ai_explanation(self, ai_explanation) -> Optional[Dict]:
        """Safely serialize AI explanation object to avoid serialization errors"""
        if not ai_explanation:
            return None
        
        try:
            # Try .dict() method first (Pydantic models)
            if hasattr(ai_explanation, 'dict'):
                return ai_explanation.dict()
            
            # Try .__dict__ attribute
            elif hasattr(ai_explanation, '__dict__'):
                return ai_explanation.__dict__
            
            # If it's already a dict
            elif isinstance(ai_explanation, dict):
                return ai_explanation
            
            # Last resort: convert to string
            else:
                logger.warning(f"Unknown AI explanation type: {type(ai_explanation)}, converting to string")
                return {"raw_content": str(ai_explanation)}
                
        except Exception as e:
            logger.error(f"Failed to serialize AI explanation: {e}")
            return {"error": "Failed to serialize AI explanation", "type": str(type(ai_explanation))}
    
    async def _generate_personalized_matching_explanation(self, user_a_answers: Dict, user_b_answers: Dict,
                                                        user_a_info: Dict, user_b_info: Dict, 
                                                        compatibility_score: float) -> Dict:
        """Generate personalized explanation showing each person's personality and why they match"""
        try:
            user_a_name = user_a_info.get('nickname', '첫 번째 분')
            user_b_name = user_b_info.get('nickname', '두 번째 분')
            
            # Analyze User A's personality traits
            user_a_traits = self._analyze_personality_traits(user_a_answers)
            user_b_traits = self._analyze_personality_traits(user_b_answers)
            
            # Find matching personality aspects
            matching_traits = self._find_matching_personality_aspects(user_a_answers, user_b_answers, user_a_traits, user_b_traits)
            
            # Find complementary differences
            complementary_differences = self._find_complementary_differences(user_a_answers, user_b_answers, user_a_traits, user_b_traits)
            
            return {
                "user_a_personality": {
                    "name": user_a_name,
                    "key_traits": user_a_traits,
                    "description": f"{user_a_name}님은 {', '.join(user_a_traits[:3])}한 성향을 보여주시네요."
                },
                "user_b_personality": {
                    "name": user_b_name,
                    "key_traits": user_b_traits,
                    "description": f"{user_b_name}님은 {', '.join(user_b_traits[:3])}한 성향을 보여주시네요."
                },
                "why_you_match": matching_traits,
                "complementary_strengths": complementary_differences,
                "match_summary": f"{user_a_name}님과 {user_b_name}님은 {len(matching_traits)}개의 공통된 가치관을 가지고 있으며, " + 
                               f"서로 다른 강점으로 균형을 이룰 수 있는 관계입니다."
            }
            
        except Exception as e:
            logger.error(f"Personalized explanation generation failed: {e}")
            return {
                "user_a_personality": {"name": "알 수 없음", "key_traits": [], "description": ""},
                "user_b_personality": {"name": "알 수 없음", "key_traits": [], "description": ""},
                "why_you_match": [],
                "complementary_strengths": [],
                "match_summary": "개인화된 분석을 생성할 수 없습니다."
            }
    
    def _analyze_personality_traits(self, user_answers: Dict) -> List[str]:
        """Analyze personality traits from user answers"""
        traits = []
        
        for qid, answer_data in user_answers.items():
            if answer_data['answer_type'] != 'choice':
                continue
                
            answer = answer_data['answer_text'] or answer_data['answer_value']
            
            # Marriage and commitment
            if qid == 'marriage_timeline':
                if 'within_1_year' in answer or '1년 이내' in answer:
                    traits.append("결혼에 적극적")
                elif 'not_decided' in answer or '생각 중' in answer:
                    traits.append("신중한 결정을 선호")
            
            # Communication style
            elif qid == 'conflict_resolution':
                if 'calm_discussion' in answer or '진정시킨 후' in answer:
                    traits.append("차분하고 이성적")
                elif 'immediate_talk' in answer or '바로 대화' in answer:
                    traits.append("솔직하고 직접적")
            
            # Lifestyle
            elif qid == 'exercise_habits':
                if 'daily' in answer or '매일' in answer:
                    traits.append("활동적이고 건강지향적")
                elif 'regular' in answer or '3-4회' in answer:
                    traits.append("규칙적인 생활을 추구")
            
            # Social preferences
            elif qid == 'social_life_balance':
                if 'weekly' in answer or '주 1회' in answer:
                    traits.append("사교적")
                elif 'rarely' in answer or '거의 안' in answer:
                    traits.append("집에서 시간 보내기를 좋아함")
            
            # Career attitudes
            elif qid == 'career_priority':
                if 'family_first' in answer or '가정을 우선' in answer:
                    traits.append("가정을 중시하는")
                elif 'balanced' in answer or '균형' in answer:
                    traits.append("일과 삶의 균형을 추구")
            
            # Love language
            elif qid == 'love_language':
                if 'words' in answer or '말을 들을 때' in answer:
                    traits.append("언어적 표현을 중시")
                elif 'quality_time' in answer or '함께 시간' in answer:
                    traits.append("함께하는 시간을 소중히 여기는")
        
        # Return unique traits, limit to top 5
        return list(set(traits))[:5]
    
    def _find_matching_personality_aspects(self, user_a_answers: Dict, user_b_answers: Dict, 
                                         user_a_traits: List[str], user_b_traits: List[str]) -> List[str]:
        """Find why these two personalities match well"""
        matching_reasons = []
        
        # Check for exact matching traits
        common_traits = set(user_a_traits) & set(user_b_traits)
        for trait in common_traits:
            matching_reasons.append(f"두 분 모두 {trait}한 성향으로 서로를 이해할 수 있습니다")
        
        # Check for matching answers on key questions
        key_questions = ['marriage_timeline', 'children_plan', 'career_priority', 'conflict_resolution']
        
        for qid in key_questions:
            if (qid in user_a_answers and qid in user_b_answers and 
                user_a_answers[qid]['answer_type'] == 'choice'):
                
                answer_a = user_a_answers[qid]['answer_text'] or user_a_answers[qid]['answer_value']
                answer_b = user_b_answers[qid]['answer_text'] or user_b_answers[qid]['answer_value']
                
                if answer_a == answer_b:
                    if qid == 'marriage_timeline':
                        matching_reasons.append("결혼에 대한 생각과 계획이 비슷합니다")
                    elif qid == 'children_plan':
                        matching_reasons.append("자녀에 대한 계획이 일치합니다")
                    elif qid == 'career_priority':
                        matching_reasons.append("일과 가정에 대한 우선순위가 같습니다")
                    elif qid == 'conflict_resolution':
                        matching_reasons.append("갈등을 해결하는 방식이 비슷합니다")
        
        return matching_reasons[:4]  # Return top 4 matching aspects
    
    def _find_complementary_differences(self, user_a_answers: Dict, user_b_answers: Dict,
                                      user_a_traits: List[str], user_b_traits: List[str]) -> List[str]:
        """Find complementary differences that strengthen the relationship"""
        complementary = []
        
        # Look for complementary personality patterns
        if any('사교적' in trait for trait in user_a_traits) and any('집에서' in trait for trait in user_b_traits):
            complementary.append("한 분은 사교적이고 다른 분은 차분해서 서로에게 균형을 줄 수 있습니다")
        
        if any('활동적' in trait for trait in user_a_traits) and any('규칙적' in trait for trait in user_b_traits):
            complementary.append("활동적인 에너지와 안정적인 계획성이 잘 어우러질 것 같습니다")
        
        # Check for complementary answers
        complementary_pairs = {
            'introvert_extrovert': {
                'extrovert': 'introvert',
                'introvert': 'extrovert'
            }
        }
        
        for qid, pairs in complementary_pairs.items():
            if (qid in user_a_answers and qid in user_b_answers):
                answer_a = user_a_answers[qid]['answer_text'] or user_a_answers[qid]['answer_value']
                answer_b = user_b_answers[qid]['answer_text'] or user_b_answers[qid]['answer_value']
                
                for key, complement in pairs.items():
                    if key in answer_a and complement in answer_b:
                        complementary.append("서로 다른 성격으로 균형잡힌 관계를 만들 수 있습니다")
                        break
        
        # If no complementary differences found, add positive generic ones
        if not complementary:
            complementary = [
                "서로 다른 강점으로 함께 성장할 수 있는 관계입니다",
                "각자의 특별함이 관계에 다양성을 더할 것입니다"
            ]
        
        return complementary[:3]  # Return top 3 complementary aspects
    
    async def _analyze_preference_criteria(self, preference: str) -> Dict[str, Any]:
        """
        Hybrid AI + Cache approach to analyze user preferences
        Uses intelligent AI analysis with caching for performance and cost optimization
        """
        try:
            # Check cache first for common preferences
            cached_analysis = await self._get_cached_preference_analysis(preference)
            if cached_analysis:
                logger.info(f"Using cached analysis for preference: {preference}")
                return cached_analysis
            
            # Use AI for intelligent analysis of new/unique preferences
            ai_analysis = await azure_openai_service.analyze_user_preference(preference)
            
            # Cache the AI analysis for future use
            await self._cache_preference_analysis(preference, ai_analysis)
            
            # Convert AI analysis to our internal format
            criteria = self._convert_ai_analysis_to_criteria(ai_analysis)
            
            logger.info(f"AI analyzed preference '{preference}' -> category: {ai_analysis.get('preference_category', 'unknown')}")
            return criteria
            
        except Exception as e:
            logger.error(f"Failed to analyze preference criteria: {e}")
            # Fallback to simple keyword matching
            return self._simple_keyword_analysis(preference)
    
    async def _get_cached_preference_analysis(self, preference: str) -> Dict[str, Any]:
        """Get cached preference analysis from database"""
        try:
            # Check if cache table exists first
            # Normalize preference text for consistent caching
            normalized_preference = preference.lower().strip()
            
            result = self.supabase.table('preference_analysis_cache').select(
                'analysis_data, created_at'
            ).eq('preference_text', normalized_preference).execute()
            
            if result.data:
                cache_entry = result.data[0]
                # Check if cache is still valid (7 days)
                from datetime import datetime, timedelta
                created_at = datetime.fromisoformat(cache_entry['created_at'].replace('Z', '+00:00'))
                if datetime.now().replace(tzinfo=created_at.tzinfo) - created_at < timedelta(days=7):
                    return cache_entry['analysis_data']
            
            return None
            
        except Exception as e:
            logger.warning(f"Cache table not available, skipping cache: {e}")
            # Return None to trigger AI analysis or fallback
            return None
    
    async def _cache_preference_analysis(self, preference: str, analysis: Dict[str, Any]):
        """Cache preference analysis for future use"""
        try:
            normalized_preference = preference.lower().strip()
            
            # Store in cache table (skip if table doesn't exist)
            self.supabase.table('preference_analysis_cache').upsert({
                'preference_text': normalized_preference,
                'analysis_data': analysis,
                'usage_count': 1
            }).execute()
            
            logger.info(f"Cached analysis for preference: {preference}")
            
        except Exception as e:
            logger.warning(f"Cache not available, skipping cache storage: {e}")
    
    def _convert_ai_analysis_to_criteria(self, ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Convert AI analysis format to internal criteria format"""
        try:
            return {
                'keywords': ai_analysis.get('search_keywords', []),
                'categories': [ai_analysis.get('preference_category', 'general')],
                'lifestyle_preferences': ai_analysis.get('matching_criteria', {}).get('must_have', []),
                'personality_traits': ai_analysis.get('matching_criteria', {}).get('nice_to_have', []),
                'activity_types': [ai_analysis.get('preference_category', 'general')],
                'ai_analysis': ai_analysis,  # Keep full AI analysis for advanced matching
                'confidence_score': ai_analysis.get('confidence_score', 0.5)
            }
        except Exception as e:
            logger.error(f"Failed to convert AI analysis: {e}")
            return self._simple_keyword_analysis(ai_analysis.get('search_keywords', [''])[0] if ai_analysis.get('search_keywords') else '')
    
    def _simple_keyword_analysis(self, preference: str) -> Dict[str, Any]:
        """Fallback simple keyword analysis"""
        criteria = {
            'keywords': [],
            'categories': [],
            'lifestyle_preferences': [],
            'personality_traits': [],
            'activity_types': []
        }
        
        preference_lower = preference.lower()
        
        # Basic keyword patterns
        if any(word in preference_lower for word in ['매운', '맵', '매콤']):
            criteria['keywords'].extend(['매운', '맵'])
            criteria['categories'].append('음식취향')
        elif any(word in preference_lower for word in ['운동', '헬스', '피트니스']):
            criteria['keywords'].extend(['운동', '헬스'])
            criteria['categories'].append('운동취향')
        elif any(word in preference_lower for word in ['여행', '해외']):
            criteria['keywords'].extend(['여행'])
            criteria['categories'].append('여가활동')
        
        logger.info(f"Simple analysis for '{preference}': {criteria}")
        return criteria
    
    async def _filter_matches_by_preference(
        self, 
        user_id: str, 
        matches: List[MatchResult], 
        criteria: Dict[str, Any],
        original_preference: str
    ) -> List[MatchResult]:
        """
        Filter and re-rank matches based on preference criteria
        """
        try:
            if not criteria or not any(criteria.values()):
                logger.info("No specific criteria found, returning original matches")
                return matches
            
            scored_matches = []
            
            for match in matches:
                # Get match user's answers to analyze against criteria
                match_answers = await self._fetch_user_answers(match.user_id)
                preference_score = await self._calculate_preference_match_score(
                    match_answers, criteria, original_preference
                )
                
                # Combine original compatibility score with preference score
                combined_score = (match.compatibility_score * 0.6) + (preference_score * 0.4)
                
                # Create new match result with updated score
                scored_match = MatchResult(
                    user_id=match.user_id,
                    compatibility_score=combined_score,
                    similarity_score=match.similarity_score,
                    cultural_bonus=match.cultural_bonus + preference_score * 0.1,  # Small bonus
                    name=match.name,
                    age=match.age
                )
                
                scored_matches.append((scored_match, preference_score))
            
            # Sort by combined score (compatibility + preference)
            scored_matches.sort(key=lambda x: x[0].compatibility_score, reverse=True)
            
            # Filter to prioritize matches with good preference scores
            high_preference_matches = [match for match, pref_score in scored_matches if pref_score > 0.3]
            remaining_matches = [match for match, pref_score in scored_matches if pref_score <= 0.3]
            
            # Return high preference matches first, then fill with others
            result = high_preference_matches + remaining_matches
            
            logger.info(f"Preference filtering: {len(high_preference_matches)} high-preference, {len(remaining_matches)} regular")
            return result
            
        except Exception as e:
            logger.error(f"Failed to filter matches by preference: {e}")
            return matches
    
    async def _calculate_preference_match_score(
        self, 
        user_answers: Dict[str, str], 
        criteria: Dict[str, Any], 
        original_preference: str
    ) -> float:
        """
        Calculate how well a user's answers match the preference criteria
        """
        try:
            score = 0.0
            total_checks = 0
            
            # Check all user answers for preference keywords
            for question_id, answer in user_answers.items():
                if not answer:
                    continue
                    
                answer_lower = answer.lower()
                
                # Check for direct keyword matches
                for keyword in criteria.get('keywords', []):
                    if keyword in answer_lower:
                        score += 0.3
                        total_checks += 1
                        logger.info(f"Found keyword '{keyword}' in answer: {answer[:50]}")
                
                # Check lifestyle preferences
                for lifestyle_pref in criteria.get('lifestyle_preferences', []):
                    if lifestyle_pref == '매운음식선호' and any(word in answer_lower for word in ['매운', '맵', '매콤']):
                        score += 0.4
                        total_checks += 1
                    elif lifestyle_pref == '가족중심' and any(word in answer_lower for word in ['가족', '가정', '아이']):
                        score += 0.4
                        total_checks += 1
                
                # Check activity types
                for activity in criteria.get('activity_types', []):
                    if activity == '운동활동' and any(word in answer_lower for word in ['운동', '헬스', '피트니스']):
                        score += 0.3
                        total_checks += 1
                    elif activity == '문화예술' and any(word in answer_lower for word in ['음악', '영화', '예술']):
                        score += 0.3
                        total_checks += 1
            
            # Normalize score
            final_score = min(score / max(total_checks, 1), 1.0) if total_checks > 0 else 0.0
            
            logger.info(f"Preference match score: {final_score:.2f} (found {total_checks} matches)")
            return final_score
            
        except Exception as e:
            logger.error(f"Failed to calculate preference match score: {e}")
            return 0.0
    
    async def _fetch_user_profile_summary(self, user_id: str) -> Dict:
        """Fetch user profile summary using RPC function"""
        try:
            # Use RPC function for optimized query
            result = self.supabase.rpc('get_user_profile_summary', {
                'p_user_id': user_id
            }).execute()
            
            if result.data and len(result.data) > 0:
                profile = result.data[0]
                
                # Get user answers for additional analysis
                user_answers = await self._fetch_user_answers(user_id)
                
                # Extract key characteristics
                key_values = []
                lifestyle = ""
                
                for question_id, answer in user_answers.items():
                    if 'family' in answer or '가족' in answer:
                        key_values.append("가족중시")
                    if 'career' in answer or '커리어' in answer or '직업' in answer:
                        key_values.append("성취지향")
                    if 'balance' in answer or '균형' in answer:
                        key_values.append("균형추구")
                
                return {
                    'user_id': profile['user_id'],
                    'nickname': profile['nickname'],
                    'age': profile['age'],
                    'gender': profile['gender'],
                    'answer_count': profile['total_answers'],
                    'has_embedding': profile['has_embedding'],
                    'key_values': key_values,
                    'lifestyle': lifestyle,
                    'last_updated': profile['last_updated']
                }
            else:
                return {}
            
        except Exception as e:
            logger.error(f"Failed to fetch profile summary for {user_id}: {e}")
            return {}

# Singleton instance
    async def store_reshuffle_feedback(self, user_id: str, preference_text: str, rejected_match_ids: List[str] = None):
        """
        Store reshuffle feedback and update per-user question weights.
        1. Save raw feedback to DB
        2. Embed the preference text → extract which question dimensions matter
        3. Update user_question_weights for personalized future matching
        """
        try:
            self.supabase.table('reshuffle_feedback').insert({
                'user_id': user_id,
                'preference_text': preference_text,
                'rejected_match_ids': rejected_match_ids or []
            }).execute()
            logger.info(f"Stored reshuffle feedback for {user_id}")
        except Exception as e:
            logger.warning(f"Reshuffle feedback storage not available: {e}")

        # Update per-user question weights from this feedback
        await self._update_question_weights_from_feedback(user_id, preference_text, rejected_match_ids or [])

    async def _update_question_weights_from_feedback(
        self, user_id: str, preference_text: str, rejected_match_ids: List[str]
    ) -> None:
        """
        Find which questions are most semantically relevant to the user's reshuffle reason
        and boost their weights.

        Works for any free-text reason — no hardcoded keyword map.
        Steps:
        1. Embed the preference text (what the user actually cares about)
        2. Load all choice questions from DB with cached text embeddings
        3. Cosine similarity → pick top-5 most relevant questions
        4. Upsert user_question_weights with +0.2 bump per session (cap 3.0)
        """
        try:
            # 1. Embed the reason text
            reason_embedding_resp = await azure_openai_service.generate_profile_embedding(preference_text)
            reason_vec = reason_embedding_resp.embedding

            # 2. Load question text embeddings (in-memory cache on service instance)
            question_embeddings = await self._get_question_text_embeddings()
            if not question_embeddings:
                return

            # 3. Cosine similarity between reason and each question
            question_ids = list(question_embeddings.keys())
            question_vecs = [question_embeddings[qid] for qid in question_ids]
            similarities = cosine_similarity([reason_vec], question_vecs)[0]

            # Top-5 most relevant questions
            top_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:5]
            top_questions = [question_ids[i] for i in top_indices if similarities[i] > 0.5]

            if not top_questions:
                logger.info(f"No sufficiently similar questions found for feedback from {user_id}")
                return

            # 4. Upsert weights
            current_weights = await self._get_user_question_weights(user_id)
            for qid in top_questions:
                current = current_weights.get(qid, 1.0)
                new_weight = min(current + 0.2, 3.0)
                existing_count = 0
                if qid in current_weights:
                    try:
                        row = self.supabase.table('user_question_weights').select(
                            'feedback_count'
                        ).eq('user_id', user_id).eq('question_id', qid).maybe_single().execute()
                        existing_count = row.data['feedback_count'] if row.data else 0
                    except Exception:
                        existing_count = 0
                self.supabase.table('user_question_weights').upsert({
                    'user_id': user_id,
                    'question_id': qid,
                    'weight': new_weight,
                    'feedback_count': existing_count + 1,
                }, on_conflict='user_id,question_id').execute()

            logger.info(f"Updated question weights for {user_id}: boosted {len(top_questions)} questions via semantic match")

        except Exception as e:
            logger.warning(f"Weight update from feedback failed for {user_id}: {e}")

    async def _get_question_text_embeddings(self) -> Dict[str, List[float]]:
        """
        Return per-question text embeddings from the DB (questions.text_embedding).
        Uses an in-memory cache — populated once per service lifetime from the DB,
        not from the Azure API. Embeddings are pre-seeded via seed_question_embeddings.py.
        """
        if hasattr(self, '_question_embeddings_cache') and self._question_embeddings_cache:
            return self._question_embeddings_cache

        try:
            result = self.supabase.table('questions').select(
                'id, text_embedding'
            ).eq('answer_type', 'choice').not_.is_('text_embedding', 'null').execute()

            cache: Dict[str, List[float]] = {
                row['id']: row['text_embedding']
                for row in (result.data or [])
                if row.get('text_embedding')
            }

            self._question_embeddings_cache = cache
            logger.info(f"Loaded {len(cache)} question embeddings from DB")
            return cache

        except Exception as e:
            logger.warning(f"Failed to load question embeddings from DB: {e}")
            return {}
    
    async def get_reshuffle_context(self, user_id: str, limit: int = 3) -> List[Dict]:
        """Get user's recent reshuffle preferences for context"""
        try:
            result = self.supabase.rpc('get_user_reshuffle_context', {
                'p_user_id': user_id,
                'p_limit': limit
            }).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.warning(f"Reshuffle context not available: {e}")
            # Return empty context - system will work without historical data
            return []
    
    async def find_compatible_matches_with_preference(
        self, 
        user_id: str, 
        preference: str,
        reshuffle_context: List[Dict],
        limit: int = 10,
        excluded_match_ids: List[str] = None
    ) -> List[MatchResult]:
        """
        Find matches with user preference context
        Uses AI to analyze preference and adjust matching to find different matches
        Excludes previously shown matches to ensure new people
        Optimized to reduce API calls
        """
        try:
            excluded_ids = list(excluded_match_ids or [])
            logger.info(f"Finding preference-based matches for user {user_id} with preference: {preference}, excluding {len(excluded_ids)} previous matches at DB level")
            
            # 1. Get potential matches with exclusions applied at database level
            # No need to fetch extra since exclusions happen before fetching
            all_matches = await self.find_compatible_matches(user_id, limit * 2, excluded_ids)
            
            if not all_matches:
                logger.warning("No matches found after database-level exclusions")
                return []
            
            # 2. Analyze user preference to extract matching criteria (uses cache if available)
            preference_criteria = await self._analyze_preference_criteria(preference)
            logger.info(f"Extracted preference criteria: {preference_criteria}")
            
            # 3. Filter and re-rank matches based on preference criteria
            preference_filtered_matches = await self._filter_matches_by_preference(
                user_id, all_matches, preference_criteria, preference
            )
            
            # 4. Return top matches prioritizing high-preference matches
            final_matches = preference_filtered_matches[:limit]
            logger.info(f"Returning {len(final_matches)} NEW preference-filtered matches")
            
            return final_matches
            
        except Exception as e:
            logger.error(f"Failed to find preference-based matches: {e}")
            # Fallback to regular matches if preference matching fails
            return await self.find_compatible_matches(user_id, limit)

profile_embedding_service = ProfileEmbeddingService()