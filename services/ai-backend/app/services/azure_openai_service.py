"""
FLIO Azure OpenAI Service
Core AI functionality for Korean dating app profile matching and analysis
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncAzureOpenAI
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    dimensions: int
    tokens_used: int

class AnalysisResponse(BaseModel):
    analysis: str
    clarity_score: int
    is_vague: bool
    key_insights: List[str]
    needs_followup: bool

class MatchExplanation(BaseModel):
    summary: str
    compatibility_reasons: List[str]
    conversation_starters: List[str]
    match_percentage: float

class AzureOpenAIService:
    """
    Core Azure OpenAI integration for FLIO dating app
    Handles embeddings, text analysis, and match explanations
    """
    
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        # Model configurations
        self.embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        self.chat_model = os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-4")
        
        # Validate environment variables
        if not all([os.getenv("AZURE_OPENAI_API_KEY"), os.getenv("AZURE_OPENAI_ENDPOINT")]):
            raise ValueError("Azure OpenAI credentials not configured. Check environment variables.")
    
    async def generate_profile_embedding(self, profile_text: str) -> EmbeddingResponse:
        """
        Generate high-dimensional embedding for user profile
        Used for compatibility matching between users
        """
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=profile_text,
                dimensions=1024  # Reduced from 3072 for efficiency while maintaining quality
            )
            
            embedding_data = response.data[0]
            
            return EmbeddingResponse(
                embedding=embedding_data.embedding,
                dimensions=len(embedding_data.embedding),
                tokens_used=response.usage.total_tokens
            )
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise Exception(f"Embedding generation failed: {str(e)}")
    
    async def analyze_user_answer(self, question: str, answer: str, context: Dict = None) -> AnalysisResponse:
        """
        Analyze user's answer for clarity and extract insights
        Korean marriage counselor perspective for cultural accuracy
        """
        system_prompt = """
        당신은 한국의 결혼정보회사에서 10년 경력을 가진 전문 상담사입니다.
        사용자의 답변을 분석하여 결혼 상대 매칭에 도움이 되는 통찰을 제공해주세요.
        
        분석 기준:
        1. 답변의 구체성과 명확성 (1-10점)
        2. 결혼관이나 가치관이 잘 드러나는지
        3. 추가 질문이 필요한지
        4. 핵심 인사이트 추출
        
        답변은 따뜻하고 이해심 있는 톤으로 해주세요.
        """
        
        user_prompt = f"""
        질문: {question}
        답변: {answer}
        
        위 답변을 분석하여 다음 JSON 형식으로 응답해주세요:
        {{
            "analysis": "답변에 대한 전문가 분석 (2-3 문장)",
            "clarity_score": 숫자 (1-10, 10이 가장 명확),
            "is_vague": boolean (모호하면 true),
            "key_insights": ["핵심 인사이트 1", "핵심 인사이트 2"],
            "needs_followup": boolean (추가 질문 필요시 true),
            "followup_reason": "추가 질문이 필요한 이유"
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            content = response.choices[0].message.content
            analysis_data = json.loads(content)
            
            return AnalysisResponse(
                analysis=analysis_data.get("analysis", ""),
                clarity_score=analysis_data.get("clarity_score", 5),
                is_vague=analysis_data.get("is_vague", False),
                key_insights=analysis_data.get("key_insights", []),
                needs_followup=analysis_data.get("needs_followup", False)
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis response: {e}")
            raise Exception(f"Failed to parse AI analysis response: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to analyze answer: {e}")
            raise Exception(f"Answer analysis failed: {str(e)}")
    
    async def generate_match_explanation(self, 
                                       user_a_profile: Dict, 
                                       user_b_profile: Dict, 
                                       compatibility_score: float) -> MatchExplanation:
        """
        Generate human-readable explanation for why two profiles match
        Focus on Korean cultural values and relationship compatibility
        """
        system_prompt = """
        당신은 한국의 결혼정보회사 매니저입니다. 
        두 회원의 매칭 결과를 보고 따뜻하고 격려적인 매칭 설명을 작성해주세요.
        
        한국 문화에서 중요한 가치들을 고려하세요:
        - 가족관과 효도
        - 교육과 직업에 대한 가치관  
        - 성격과 라이프스타일 궁합
        - 미래 계획과 비전의 일치
        
        긍정적이고 희망적인 톤으로 작성해주세요.
        """
        
        user_prompt = f"""
        매칭 점수: {compatibility_score:.1%}
        
        회원 A 프로필 요약: {self._summarize_profile(user_a_profile)}
        회원 B 프로필 요약: {self._summarize_profile(user_b_profile)}
        
        다음 JSON 형식으로 매칭 설명을 작성해주세요:
        {{
            "summary": "전체 매칭에 대한 요약 (3-4 문장)",
            "compatibility_reasons": ["호환성 이유 1", "호환성 이유 2", "호환성 이유 3"],
            "conversation_starters": ["대화 시작 주제 1", "대화 시작 주제 2", "대화 시작 주제 3"],
            "match_percentage": {compatibility_score}
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            explanation_data = json.loads(content)
            
            return MatchExplanation(
                summary=explanation_data.get("summary", ""),
                compatibility_reasons=explanation_data.get("compatibility_reasons", []),
                conversation_starters=explanation_data.get("conversation_starters", []),
                match_percentage=compatibility_score
            )
            
        except Exception as e:
            logger.error(f"Failed to generate match explanation: {e}")
            raise Exception(f"Match explanation generation failed: {str(e)}")
    
    async def batch_generate_embeddings(self, texts: List[str]) -> List[EmbeddingResponse]:
        """
        Generate embeddings for multiple texts efficiently
        Useful for processing all user profiles or questions
        """
        tasks = [self.generate_profile_embedding(text) for text in texts]
        return await asyncio.gather(*tasks)
    
    def _summarize_profile(self, profile: Dict) -> str:
        """Helper to create profile summary for matching analysis"""
        summary_parts = []
        
        if profile.get('nickname'):
            summary_parts.append(f"닉네임: {profile['nickname']}")
        
        if profile.get('age'):
            summary_parts.append(f"나이: {profile['age']}세")
        
        if profile.get('key_values'):
            summary_parts.append(f"주요 가치관: {', '.join(profile['key_values'])}")
        
        if profile.get('lifestyle'):
            summary_parts.append(f"라이프스타일: {profile['lifestyle']}")
        
        return " | ".join(summary_parts)

# Singleton instance
azure_openai_service = AzureOpenAIService()