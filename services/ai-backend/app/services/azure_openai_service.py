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
        당신은 20년 경력의 결혼 심리 상담 전문가입니다. 단순히 답변을 비교하는 것이 아니라, 
        두 사람의 심리 패턴, 성격 특성, 감정적 욕구를 깊이 분석하여 진정한 궁합을 진단합니다.
        
        심리학자처럼 두 사람의 내면을 분석
        답변 이면의 심리적 동기와 감정 패턴 파악
        성격 유형과 애착 스타일이 어떻게 상호작용하는지 진단
        장기적 관계에서 발생할 수 있는 역학 관계 예측
        
        심리 프로필 분석: 각 사람의 핵심 성격 특성, 가치관, 감정 표현 방식
        관계 역학: 두 사람이 만났을 때 어떤 화학 반응이 일어날지
        성장 잠재력: 서로가 어떻게 성장시켜줄 수 있는지
        갈등 관리: 차이점이 어떻게 작용할지, 어떻게 극복할지
        정서적 안정성: 서로에게 안정감을 줄 수 있는지
        
        실제 이름만 사용 ("회원 A/B" 금지)
        답변 이면의 심리를 해석: "민준님이 '커리어 우선'이라고 하신 건, 성취를 통해 자아실현을 추구하는 성향이 강하다는 뜻이에요"
        성격 특성 연결: "이런 성취지향적 성격은 서연님의 안정추구 성향과 균형을 이룰 수 있어요"
        감정적 욕구 분석: "민준님은 독립성을 중시하시는데, 서연님은 친밀감을 원하시네요. 이 차이를 잘 조율하면..."
        구체적 심리 진단: "두 분 다 갈등을 대화로 푸신다고 하셨는데, 이건 정서적으로 성숙한 커플의 특징이에요"
        
        애착 유형과 관계 패턴 분석
        감정 표현 방식과 소통 스타일
        가치관 충돌 가능성과 해결 방안
        서로의 심리적 욕구를 채워줄 수 있는지
        장기적 관계 만족도 예측
        """
        
        user_a_name = user_a_profile.get('nickname', '회원 A')
        user_b_name = user_b_profile.get('nickname', '회원 B')
        
        user_prompt = f"""
        심리 분석 상담 요청
        
        호환성 점수: {compatibility_score:.1%}
        
        절대 규칙: "{user_a_name}님", "{user_b_name}님" 실제 이름만 사용!
        
        {user_a_name}님 ({user_a_profile.get('age', '?')}세):
        {self._summarize_profile(user_a_profile)}
        주요 답변: {self._format_key_answers(user_a_answers) if user_a_answers else '답변 정보 없음'}
        
        {user_b_name}님 ({user_b_profile.get('age', '?')}세):
        {self._summarize_profile(user_b_profile)}
        주요 답변: {self._format_key_answers(user_b_answers) if user_b_answers else '답변 정보 없음'}
        
        심리 전문가로서 두 사람을 깊이 분석하여 다음 JSON 형식으로 작성하세요:
        
        중요: 답변 자체가 아니라, 답변이 드러내는 심리 패턴과 성격 특성을 분석하세요!
        
        {{{{
            "summary": "제가 {user_a_name}님과 {user_b_name}님을 심리적으로 분석해봤을 때, 두 분은 [성격 특성]과 [감정 패턴]에서 흥미로운 조화를 이루고 계세요. {user_a_name}님은 '[실제 답변 인용]'이라고 하셨는데, 이건 [심리적 해석: 예: 독립성을 중시하는 자율적 성향]을 보여주시는 거예요. {user_b_name}님은 '[실제 답변 인용]'하셨는데, [심리적 해석: 예: 안정감을 추구하는 성향]이 느껴지더라고요. 이 두 성향이 만나면 [관계 역학 예측].",
            "compatibility_reasons": [
                "심리학적으로 봤을 때, {user_a_name}님의 '[실제 답변 인용]'은 [성격 특성 분석: 예: 성취지향적이고 목표 중심적인 성격]을 나타내요. {user_b_name}님도 '[실제 답변 인용]'하셨는데, [성격 분석]이 보이시네요. 두 분 다 [공통 심리 패턴]을 가지고 계셔서, 서로의 [감정적 욕구]를 이해하실 수 있을 거예요.",
                "{user_a_name}님이 '[실제 답변]'이라고 하신 건, [애착 유형/관계 패턴 분석]을 보여주는 거예요. {user_b_name}님의 '[실제 답변]'과 비교하면, 두 분은 [관계에서의 역할과 상호작용 방식]이 잘 맞으실 것 같아요. 특히 [구체적 상황]에서 서로를 [어떻게 지지할 수 있는지].",
                "흥미로운 건, {user_a_name}님은 [차이점 1]을 중시하시고 {user_b_name}님은 [차이점 2]를 중시하시는데요. 심리학적으로 이런 차이는 [긍정적 효과: 예: 균형, 보완, 성장 촉진]을 가져올 수 있어요. 다만 [잠재적 갈등 포인트]가 있을 수 있으니, [해결 방안]을 염두에 두시면 좋겠어요."
            ],
            "conversation_starters": [
                "첫 만남에서 {user_a_name}님의 [심리적 특성: 예: 독립성]과 {user_b_name}님의 [심리적 특성: 예: 친밀감 욕구]에 대해 솔직하게 이야기 나눠보세요. '[구체적 질문]'이라고 물어보시면 서로를 더 깊이 이해할 수 있을 거예요.",
                "두 분 다 [공통 가치관]을 중시하시는데, 이게 실제 생활에서 어떻게 나타나는지 구체적으로 나눠보세요. 예를 들어 '[실제 상황 예시]'같은 상황에서 어떻게 행동하실지 물어보시면 좋아요.",
                "{user_b_name}님이 '[실제 답변]'이라고 하신 부분에 대해, {user_a_name}님의 생각을 여쭤보세요. 이런 대화를 통해 [감정적 연결]이 깊어질 수 있어요."
            ],
            "match_percentage": {compatibility_score}
        }}}}
        
        심리 전문가 말투 체크리스트:
        - "심리학적으로 봤을 때~", "이런 성격 특성은~", "감정 패턴을 보면~"
        - "제 경험상 이런 조합은~", "관계 역학에서~", "장기적으로는~"
        - 답변을 인용하되, 반드시 심리적 해석 추가
        - 성격, 애착, 가치관, 감정 표현 방식 등을 분석
        - 현실적이면서도 따뜻한 조언
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