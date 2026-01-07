"""
FLIO Profile Embedding Service
Converts user answers into embeddings for matching
Uses translation to English for cost optimization
"""

import asyncio
import json
from typing import Dict, List, Tuple, Optional
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
    explanation: Optional[Dict] = None

class ProfileEmbeddingService:
    """
    Service to manage user profile embeddings for dating compatibility
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.embedding_dimension = 1024  # Azure OpenAI text-embedding-3-large
    
    async def build_profile_text(self, user_answers: Dict[str, str]) -> str:
        """
        Build Korean narrative text from user answers for embedding generation
        This text represents the user's personality, values, and preferences
        """
        profile_sections = []
        
        # MBTI and personality section
        mbti_answers = {k: v for k, v in user_answers.items() if 'MBTI' in k or '성향' in k}
        if mbti_answers:
            personality_text = self._build_personality_section(mbti_answers)
            profile_sections.append(f"성격 및 성향: {personality_text}")
        
        # Values and lifestyle section  
        value_answers = {k: v for k, v in user_answers.items() if any(word in k for word in ['가치관', '라이프스타일', '취미', '여가'])}
        if value_answers:
            values_text = self._build_values_section(value_answers)
            profile_sections.append(f"가치관과 생활방식: {values_text}")
        
        # Relationship and future plans
        relationship_answers = {k: v for k, v in user_answers.items() if any(word in k for word in ['결혼', '연애', '가족', '미래'])}
        if relationship_answers:
            relationship_text = self._build_relationship_section(relationship_answers)
            profile_sections.append(f"연애관과 미래계획: {relationship_text}")
        
        # Communication and conflict resolution
        communication_answers = {k: v for k, v in user_answers.items() if any(word in k for word in ['소통', '갈등', '의견', '결정'])}
        if communication_answers:
            communication_text = self._build_communication_section(communication_answers)
            profile_sections.append(f"소통방식과 갈등해결: {communication_text}")
        
        # Combine all sections
        full_profile = " | ".join(profile_sections)
        
        # Add context for better embedding
        contextualized_profile = f"한국인 결혼 대상자 프로필: {full_profile}"
        
        return contextualized_profile
    
    def _build_personality_section(self, answers: Dict[str, str]) -> str:
        """Build personality description from MBTI-related answers"""
        traits = []
        for question_id, answer in answers.items():
            # Map answers to personality traits
            if 'energy' in question_id or '에너지' in question_id:
                if 'friends' in answer or '친구' in answer:
                    traits.append("사교적")
                elif 'alone' in answer or '혼자' in answer:
                    traits.append("내성적")
            
            if 'gathering' in question_id or '모임' in question_id:
                if 'lead' in answer or '이끈다' in answer:
                    traits.append("리더십있는")
                elif 'listen' in answer or '듣기' in answer:
                    traits.append("경청하는")
        
        return ", ".join(traits) if traits else "다양한 성격을 가진"
    
    def _build_values_section(self, answers: Dict[str, str]) -> str:
        """Build values and lifestyle description"""
        values = []
        for question_id, answer in answers.items():
            # Extract key values from answers
            if 'family' in answer or '가족' in answer:
                values.append("가족중심적")
            if 'career' in answer or '커리어' in answer or '직업' in answer:
                values.append("성취지향적")
            if 'balance' in answer or '균형' in answer:
                values.append("균형추구")
        
        return ", ".join(values) if values else "다양한 가치관을 가진"
    
    def _build_relationship_section(self, answers: Dict[str, str]) -> str:
        """Build relationship philosophy description"""
        relationship_style = []
        for question_id, answer in answers.items():
            if 'trust' in answer or '신뢰' in answer:
                relationship_style.append("신뢰중시")
            if 'communication' in answer or '소통' in answer:
                relationship_style.append("소통중시")
            if 'support' in answer or '지지' in answer or '격려' in answer:
                relationship_style.append("서로격려")
        
        return ", ".join(relationship_style) if relationship_style else "진실한 관계를 원하는"
    
    def _build_communication_section(self, answers: Dict[str, str]) -> str:
        """Build communication style description"""
        comm_style = []
        for question_id, answer in answers.items():
            if 'direct' in answer or '직접' in answer or '솔직' in answer:
                comm_style.append("직접적소통")
            if 'patient' in answer or '인내' in answer or '기다' in answer:
                comm_style.append("인내심있는")
            if 'compromise' in answer or '타협' in answer or '절충' in answer:
                comm_style.append("타협적")
        
        return ", ".join(comm_style) if comm_style else "건강한 소통을 추구하는"
    
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
            
            # 2. Build profile text (Korean)
            profile_text_korean = await self.build_profile_text(user_answers)
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
    
    async def find_compatible_matches(self, user_id: str, limit: int = 10) -> List[MatchResult]:
        """
        Find compatible matches for a user based on embedding similarity
        Core matching algorithm for the dating app
        """
        try:
            # 1. Get user's embedding
            user_embedding = await self._get_user_embedding(user_id)
            if not user_embedding:
                raise ValueError(f"No embedding found for user {user_id}")
            
            # 2. Find similar profiles using Supabase vector search
            similar_profiles = await self._vector_similarity_search(user_id, user_embedding, limit * 2)
            
            # 3. Calculate detailed compatibility scores
            match_results = []
            for profile in similar_profiles:
                compatibility_score = await self._calculate_compatibility(user_id, profile['user_id'])
                
                match_result = MatchResult(
                    user_id=profile['user_id'],
                    compatibility_score=compatibility_score['total_score'],
                    similarity_score=compatibility_score['similarity_score'],
                    cultural_bonus=compatibility_score['cultural_bonus']
                )
                match_results.append(match_result)
            
            # 4. Sort by compatibility and return top matches
            match_results.sort(key=lambda x: x.compatibility_score, reverse=True)
            return match_results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to find matches for user {user_id}: {e}")
            raise Exception(f"Match finding failed: {str(e)}")
    
    async def get_match_explanation(self, user_a_id: str, user_b_id: str) -> Dict:
        """
        Generate detailed explanation for why two users match
        Uses Azure OpenAI to create human-readable explanation
        """
        try:
            # Get both user profiles
            user_a_info = await self._fetch_user_profile_summary(user_a_id)
            user_b_info = await self._fetch_user_profile_summary(user_b_id)
            
            # Calculate compatibility score
            compatibility = await self._calculate_compatibility(user_a_id, user_b_id)
            
            # Generate explanation using Azure OpenAI
            explanation = await azure_openai_service.generate_match_explanation(
                user_a_profile=user_a_info,
                user_b_profile=user_b_info,
                compatibility_score=compatibility['total_score']
            )
            
            return {
                "compatibility_score": compatibility['total_score'],
                "explanation": explanation.dict(),
                "detailed_scores": compatibility
            }
            
        except Exception as e:
            logger.error(f"Failed to generate explanation for {user_a_id} and {user_b_id}: {e}")
            raise Exception(f"Match explanation generation failed: {str(e)}")
    
    async def _fetch_user_answers(self, user_id: str) -> Dict[str, str]:
        """Fetch user's question answers from Supabase"""
        try:
            result = self.supabase.table('user_answers').select(
                'question_id, answer_value'
            ).eq('user_id', user_id).execute()
            
            return {item['question_id']: item['answer_value'] for item in result.data}
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
            result = self.supabase.rpc('store_user_embedding', {
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
                'profile_embedding_v2'
            ).eq('user_id', user_id).single().execute()
            
            embedding_str = result.data['profile_embedding_v2']
            if not embedding_str:
                return None
            
            # Parse pgvector format back to list
            embedding = eval(embedding_str)  # Note: In production, use proper JSON parsing
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to get embedding for user {user_id}: {e}")
            return None
    
    async def _vector_similarity_search(self, user_id: str, user_embedding: List[float], limit: int) -> List[Dict]:
        """Use Supabase vector similarity search to find similar profiles"""
        try:
            # Convert embedding to pgvector format
            embedding_vector = f"[{','.join(map(str, user_embedding))}]"
            
            # Use Supabase RPC function for vector similarity search
            result = self.supabase.rpc('find_similar_profiles_v2', {
                'query_embedding': embedding_vector,
                'exclude_user_id': user_id,
                'match_limit': limit
            }).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Vector similarity search failed: {e}")
            return []
    
    async def _calculate_compatibility(self, user_a_id: str, user_b_id: str) -> Dict[str, float]:
        """Calculate detailed compatibility score between two users"""
        try:
            # Get embeddings for both users
            embedding_a = await self._get_user_embedding(user_a_id)
            embedding_b = await self._get_user_embedding(user_b_id)
            
            if not embedding_a or not embedding_b:
                return {'total_score': 0.0, 'similarity_score': 0.0, 'cultural_bonus': 0.0}
            
            # Calculate cosine similarity
            similarity = cosine_similarity([embedding_a], [embedding_b])[0][0]
            
            # Cultural bonus based on answer compatibility (simple version)
            cultural_bonus = await self._calculate_cultural_bonus(user_a_id, user_b_id)
            
            # Final compatibility score (weighted)
            total_score = (similarity * 0.8) + (cultural_bonus * 0.2)
            
            return {
                'total_score': min(max(total_score, 0.0), 1.0),  # Clamp between 0-1
                'similarity_score': similarity,
                'cultural_bonus': cultural_bonus
            }
            
        except Exception as e:
            logger.error(f"Compatibility calculation failed: {e}")
            return {'total_score': 0.0, 'similarity_score': 0.0, 'cultural_bonus': 0.0}
    
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
profile_embedding_service = ProfileEmbeddingService()