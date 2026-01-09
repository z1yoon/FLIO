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
        self.chat_model = os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-4o-mini")
        
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
                                       compatibility_score: float,
                                       user_a_answers: Dict = None,
                                       user_b_answers: Dict = None,
                                       reshuffle_preference: str = None,
                                       reshuffle_context: List[Dict] = None) -> MatchExplanation:
        """
        Generate human-readable explanation for why two profiles match
        Focus on Korean cultural values and relationship compatibility
        Shows specific answers from both users
        """
        system_prompt = """
        당신은 20년 경력의 결혼 심리 상담 전문가이자 결혼정보회사 매니저입니다.
        
        심리학적 전문성과 따뜻한 매니저의 감성을 모두 갖추고, 두 사람의 심리 패턴, 성격 특성, 
        감정적 욕구를 깊이 분석하여 진정한 궁합을 진단합니다.
        
        핵심 역할:
        - 심리학자처럼 두 사람의 내면과 성격 특성을 분석
        - 답변 이면의 심리적 동기와 감정 패턴 파악
        - 성격 유형과 애착 스타일의 상호작용 진단
        - 장기적 관계 역학과 성장 잠재력 예측
        - 매니저로서 따뜻하고 현실적인 조언 제공
        
        분석 관점:
        - 심리 프로필: 핵심 성격 특성, 가치관, 감정 표현 방식
        - 관계 역학: 두 사람의 화학 반응과 상호작용
        - 성장 잠재력: 서로를 어떻게 성장시킬 수 있는지
        - 갈등 관리: 차이점의 작용과 극복 방안
        - 정서적 안정성: 서로에게 주는 안정감
        
        중요 원칙:
        - 실제 이름만 사용 ("회원 A/B" 절대 금지)
        - 답변을 인용하되, 심리적 의미를 해석
        - 자연스럽고 다양한 표현 사용 (고정된 패턴 피하기)
        - 따뜻하면서도 전문적인 톤 유지
        - 구체적이고 실용적인 조언 제공
        """
        
        user_a_name = user_a_profile.get('nickname', '회원 A')
        user_b_name = user_b_profile.get('nickname', '회원 B')
        
        user_prompt = f"""
        매칭 심리 분석 요청
        
        호환성 점수: {compatibility_score:.1%}
        
        절대 규칙: "{user_a_name}님", "{user_b_name}님" 실제 이름만 사용!
        
        {user_a_name}님 ({user_a_profile.get('age', '?')}세):
        {self._summarize_profile(user_a_profile)}
        주요 답변: {self._format_key_answers(user_a_answers) if user_a_answers else '답변 정보 없음'}
        
        {user_b_name}님 ({user_b_profile.get('age', '?')}세):
        {self._summarize_profile(user_b_profile)}
        주요 답변: {self._format_key_answers(user_b_answers) if user_b_answers else '답변 정보 없음'}
        
        {"" if not reshuffle_preference else f'''
        ⚠️ 중요: {user_a_name}님의 새로운 매칭 요청
        {user_a_name}님께서 "{reshuffle_preference}"라고 하시며 새로운 매칭을 원하셨습니다.
        이 요청을 반드시 반영하여, {user_b_name}님이 이 선호도에 어떻게 부합하는지 설명해주세요.
        '''}
        
        심리 전문가이자 매니저로서 두 사람을 깊이 분석하여 다음 JSON 형식으로 작성하세요:
        
        핵심 요구사항:
        1. 답변 내용을 직접 인용하고, 그 이면의 심리적 의미를 해석하세요
        2. 성격 특성, 애착 유형, 가치관, 감정 패턴을 분석하세요
        3. 자연스럽고 다양한 표현을 사용하세요 (매번 같은 시작 문구 피하기)
        4. 따뜻하면서도 전문적인 톤을 유지하세요
        5. 구체적이고 실용적인 조언을 제공하세요
        {"6. **중요**: 사용자의 새로운 매칭 요청을 반드시 설명에 반영하세요" if reshuffle_preference else ""}
        
        JSON 형식:
        {{{{
            "summary": "두 분의 프로필을 분석한 전체적인 인상과 궁합 평가 (2-3문장, 자유로운 시작)",
            "compatibility_reasons": [
                "첫 번째 궁합 이유 - 실제 답변 인용 + 심리 분석 + 관계 예측",
                "두 번째 궁합 이유 - 다른 각도에서의 분석",
                "세 번째 궁합 이유 - 차이점이나 보완점 분석"
            ],
            "conversation_starters": [
                "첫 만남 대화 주제 제안 1",
                "첫 만남 대화 주제 제안 2",
                "첫 만남 대화 주제 제안 3"
            ],
            "match_percentage": {compatibility_score}
        }}}}
        
        표현 다양성 가이드:
        - 시작 문구를 다양하게: "두 분을 보니~", "프로필에서 느껴지는 건~", "인상 깊었던 건~", "제가 주목한 부분은~" 등
        - 분석 표현 변화: "~라는 점에서", "~을 보면", "~에서 알 수 있듯이", "~을 통해" 등
        - 자연스러운 연결: 매번 "심리학적으로" 시작하지 말고, 문맥에 맞게 자연스럽게
        - 매니저의 따뜻함: "제 경험상~", "두 분이라면~", "이런 조합은~" 등 다양하게
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            logger.info(f"Azure OpenAI raw response: {content[:200]}...")
            
            if not content or content.strip() == "":
                logger.error("Azure OpenAI returned empty content")
                raise Exception("Empty response from Azure OpenAI")
            
            # Strip markdown code blocks if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            elif content.startswith("```"):
                content = content[3:]  # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove trailing ```
            content = content.strip()
            
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
    
    def _format_key_answers(self, answers: Dict) -> str:
        """Format user answers for match explanation"""
        if not answers:
            return "답변 정보 없음"
        
        # Select important questions to show
        key_questions = [
            'marriage_timeline', 'children_plan', 'family_values',
            'career_family_balance', 'conflict_resolution', 'trust_building',
            'personal_values_lifestyle', 'ideal_relationship_dynamic'
        ]
        
        formatted = []
        for q_id in key_questions:
            if q_id in answers and answers[q_id]:
                formatted.append(f"- {q_id}: {answers[q_id][:100]}")  # Limit length
        
        return "\n".join(formatted[:8]) if formatted else "답변 정보 없음"
    
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