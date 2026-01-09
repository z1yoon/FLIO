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
                                       user_b_answers: Dict = None) -> MatchExplanation:
        """
        Generate human-readable explanation for why two profiles match
        Focus on Korean cultural values and relationship compatibility
        Shows specific answers from both users
        """
        system_prompt = """
        당신은 20년 경력의 한국 결혼정보회사 수석 매니저입니다.
        수백 쌍의 커플을 성혼으로 이끈 경험이 있으며, 두 분의 인연을 진심으로 소중히 여깁니다.
        
        💕 말투 스타일 (매우 중요!):
        - "제가 두 분 프로필을 보면서 느낀 건데요~", "정말 잘 맞으실 것 같다는 생각이 들었어요"
        - "~하시더라고요", "~하신 걸 보니", "제 경험상~" 같은 자연스러운 구어체
        - 마치 친한 언니/오빠가 진심으로 조언하듯이
        - 구체적인 에피소드와 답변을 언급하며 설명
        
        📝 필수 작성 원칙:
        1. 절대 "회원 A", "회원 B" 금지! 반드시 실제 이름 사용
        2. 답변 내용을 직접 인용: "민준님이 '커리어와 자기개발'을 중시한다고 하셨잖아요"
        3. 두 분의 답변을 비교하며 설명: "서연님도 비슷하게 '가족과의 시간'을 소중히 여기신다고 하셨어요"
        4. 차이점을 긍정적으로: "오히려 이런 차이가 서로를 보완해줄 수 있어요"
        5. 매니저의 개인적 소견 추가: "제가 보기에는~", "경험상 이런 커플들이~"
        
        🎯 상담 포인트:
        - 결혼에 대한 진지함과 준비도
        - 가치관의 일치와 차이점의 균형
        - 서로를 존중하고 성장시킬 수 있는 관계
        - 현실적이면서도 희망적인 조언
        """
        
        user_a_name = user_a_profile.get('nickname', '회원 A')
        user_b_name = user_b_profile.get('nickname', '회원 B')
        
        user_prompt = f"""
        매칭 상담 요청
        
        호환성 점수: {compatibility_score:.1%}
        
        절대 규칙: "{user_a_name}님", "{user_b_name}님" 실제 이름만 사용! "회원", "사용자" 등 일반 명칭 절대 금지!
        
        {user_a_name}님 ({user_a_profile.get('age', '?')}세):
        {self._summarize_profile(user_a_profile)}
        주요 답변: {self._format_key_answers(user_a_answers) if user_a_answers else '답변 정보 없음'}
        
        {user_b_name}님 ({user_b_profile.get('age', '?')}세):
        {self._summarize_profile(user_b_profile)}
        주요 답변: {self._format_key_answers(user_b_answers) if user_b_answers else '답변 정보 없음'}
        
        다음 JSON 형식으로 작성하되, 반드시 결혼정보회사 매니저 말투로 작성하세요:
        
        중요: 반드시 위에 제공된 실제 답변 내용을 직접 인용하고 구체적으로 언급하세요. 일반적인 표현 금지!
        
        {{{{
            "summary": "제가 {user_a_name}님과 {user_b_name}님 프로필을 처음 봤을 때, 정말 잘 어울리실 것 같다는 생각이 들었어요. {user_a_name}님께서 [위 답변에서 실제로 쓴 구체적 문장을 그대로 인용]하신다고 하셨는데, {user_b_name}님도 [실제 답변 문장 인용]하셔서 두 분의 생각이 잘 맞는 것 같아요.",
            "compatibility_reasons": [
                "제가 {user_a_name}님 답변을 읽어보니 '[personal_values_lifestyle나 ideal_relationship_dynamic 답변에서 실제 문장 그대로 인용]'이라고 쓰셨더라고요. {user_b_name}님도 '[실제 답변 문장 인용]'이라고 하셔서 두 분의 가치관이 정말 잘 맞는 것 같아요.",
                "{user_a_name}님이 [future_life_vision이나 다른 질문에서 실제로 쓴 구체적 내용]을 말씀하셨잖아요. {user_b_name}님도 [실제 답변 내용]이라고 하셔서, 두 분이 비슷한 미래를 그리고 계신 것 같아요.",
                "특히 인상 깊었던 건, {user_a_name}님은 [실제 답변 인용]하셨고 {user_b_name}님은 [실제 답변 인용]하셨는데, 이런 차이가 오히려 서로를 보완해줄 수 있을 것 같아요."
            ],
            "conversation_starters": [
                "첫 만남에서 {user_a_name}님이 말씀하신 '[구체적 답변]'에 대해 {user_b_name}님께 여쭤보시면 좋을 것 같아요. 두 분 다 관심 있는 주제니까 대화가 잘 통하실 거예요.",
                "{user_b_name}님이 중요하게 생각하시는 '[가치관]'에 대해 이야기 나눠보세요. {user_a_name}님도 비슷한 생각이시니 공감대가 형성될 거예요.",
                "두 분 다 '[공통 관심사]'에 관심이 있으시더라고요. 이 주제로 시작하시면 자연스럽게 대화가 이어질 것 같아요."
            ],
            "match_percentage": {compatibility_score}
        }}}}
        
        매니저 말투 체크리스트:
        - "제가 ~을 봤을 때", "~하시더라고요", "~것 같아요", "~하시는 것 같아요"
        - "제 경험상~", "이런 커플들이~", "두 분이 정말~"
        - 구체적인 답변 내용을 직접 인용 ('[답변]'이라고 하셨는데요)
        - 긍정적이고 희망적인 톤 유지
        - 실제 이름 사용 필수!
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