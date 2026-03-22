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
    
    # Shared AI manager persona — used in ALL AI manager LLM calls for consistency.
    # Every method that acts as the "AI manager" must include this as the system prompt base.
    _MANAGER_PERSONA = (
        "당신은 FLIO의 AI 결혼 매니저입니다. "
        "10년 경력의 결혼정보회사 상담사이자 프로필 컨설턴트로서, "
        "따뜻하고 전문적인 태도로 회원들의 매칭 성공을 돕습니다. "
        "한국 결혼 문화와 가치관을 깊이 이해하며, "
        "진실되고 구체적인 정보를 바탕으로 신뢰할 수 있는 조언을 제공합니다."
    )

    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        # Model configurations
        self.embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        self.chat_model = os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-4o-mini")
        self.whisper_model = os.getenv("AZURE_OPENAI_WHISPER_MODEL", "whisper-1")
        
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
        system_prompt = (
            self._MANAGER_PERSONA + "\n\n"
            "역할: 사용자의 답변을 분석하여 결혼 상대 매칭에 도움이 되는 통찰을 제공합니다.\n\n"
            "분석 기준:\n"
            "1. 답변의 구체성과 명확성 (1-10점)\n"
            "2. 결혼관이나 가치관이 잘 드러나는지\n"
            "3. 추가 질문이 필요한지\n"
            "4. 핵심 인사이트 추출"
        )
        
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
        - 사용자의 새로운 매칭 요청을 정확히 이해하고 그에 부합하는 분석 제공
        
        분석 관점:
        - 심리 프로필: 핵심 성격 특성, 가치관, 감정 표현 방식
        - 관계 역학: 두 사람의 화학 반응과 상호작용
        - 성장 잠재력: 서로를 어떻게 성장시킬 수 있는지
        - 갈등 관리: 차이점의 작용과 극복 방안
        - 정서적 안정성: 서로에게 주는 안정감
        - 특별 요청 분석: 사용자가 원하는 특별한 조건과 새로운 상대의 부합성
        
        **새로운 매칭 요청 처리 원칙:**
        사용자가 "더 비슷한 취미를 가진 분", "운동을 좋아하는 분", "가족을 중시하는 분" 등의 
        특별한 요청을 했다면, 반드시 해당 상대방이 그 조건을 어떻게 충족하는지 구체적으로 설명해야 합니다.
        
        중요 원칙:
        - 실제 이름만 사용 ("회원 A/B" 절대 금지)
        - 답변을 인용하되, 심리적 의미를 해석
        - 자연스럽고 다양한 표현 사용 (고정된 패턴 피하기)
        - 따뜻하면서도 전문적인 톤 유지
        - 구체적이고 실용적인 조언 제공
        - 새로운 매칭 요청이 있을 때는 그 조건을 충족하는 이유를 명확히 제시
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
        🎯 **특별 매칭 요청**: {user_a_name}님의 새로운 요청 분석
        
        {user_a_name}님께서 "{reshuffle_preference}"라고 하시며 새로운 매칭을 원하셨습니다.
        
        **필수 분석 사항:**
        1. {user_b_name}님이 이 특별 요청("{reshuffle_preference}")을 어떻게 충족하는지 구체적으로 분석
        2. {user_b_name}님의 답변에서 해당 조건과 일치하는 부분을 직접 인용
        3. 왜 {user_b_name}님이 {user_a_name}님의 이번 요청에 특히 적합한지 설명
        4. 이전 매칭과 어떤 점이 다르고 더 나은지 명시
        
        ⚠️ 중요: 단순히 일반적인 궁합만 설명하지 말고, 사용자의 구체적 요청에 부합하는 이유를 반드시 포함하세요.
        '''}
        
        {"" if not reshuffle_context else f'''
        📊 **과거 요청 이력**: {user_a_name}님의 매칭 선호도 변화
        {self._format_reshuffle_context(reshuffle_context)}
        이런 변화 패턴을 고려하여 {user_b_name}님이 {user_a_name}님의 진화하는 선호도에 얼마나 잘 맞는지 분석해주세요.
        '''}
        
        심리 전문가이자 매니저로서 두 사람을 깊이 분석하여 다음 JSON 형식으로 작성하세요:
        
        핵심 요구사항:
        1. 답변 내용을 직접 인용하고, 그 이면의 심리적 의미를 해석하세요
        2. 성격 특성, 애착 유형, 가치관, 감정 패턴을 분석하세요
        3. 자연스럽고 다양한 표현을 사용하세요 (매번 같은 시작 문구 피하기)
        4. 따뜻하면서도 전문적인 톤을 유지하세요
        5. 구체적이고 실용적인 조언을 제공하세요
        {"6. **최우선**: 사용자의 새로운 매칭 요청을 summary와 compatibility_reasons 첫 번째 항목에 반드시 반영하세요" if reshuffle_preference else ""}
        {"7. **요청 충족도**: 각 compatibility_reasons에서 새로운 요청 조건과의 연관성을 명확히 하세요" if reshuffle_preference else ""}
        
        JSON 형식:
        {{{{
            "summary": "두 분의 프로필을 분석한 전체적인 인상과 궁합 평가 (2-3문장, 자유로운 시작){"+ 새로운 요청에 대한 부합도를 반드시 포함" if reshuffle_preference else ""}",
            "compatibility_reasons": [
                "{"첫 번째 궁합 이유 - 새로운 요청에 대한 부합성을 반드시 포함 (실제 답변 인용 + 심리 분석 + 요청 충족 설명)" if reshuffle_preference else "첫 번째 궁합 이유 - 실제 답변 인용 + 심리 분석 + 관계 예측"}",
                "두 번째 궁합 이유 - 다른 각도에서의 분석",
                "세 번째 궁합 이유 - 차이점이나 보완점 분석"
            ],
            "conversation_starters": [
                "{"새로운 요청과 관련된 첫 만남 대화 주제" if reshuffle_preference else "첫 만남 대화 주제 제안 1"}",
                "{"공통 관심사나 가치관 관련 대화 주제" if reshuffle_preference else "첫 만남 대화 주제 제안 2"}",
                "{"미래 계획이나 목표 관련 대화 주제" if reshuffle_preference else "첫 만남 대화 주제 제안 3"}"
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
    
    async def transcribe_audio(self, audio_file_path: str, language: str = "ko") -> Dict[str, Any]:
        """
        Transcribe audio file using Azure OpenAI Whisper
        Critical for blind accessibility - converts voice to text for matching
        """
        try:
            logger.info(f"Transcribing audio file: {audio_file_path}")
            
            with open(audio_file_path, 'rb') as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model=self.whisper_model,
                    file=audio_file,
                    language=language,  # Korean support
                    response_format="json"
                )
            
            transcribed_text = response.text.strip()
            logger.info(f"Transcription successful: '{transcribed_text[:100]}...'")
            
            return {
                "text": transcribed_text,
                "language": language,
                "confidence": 1.0  # Whisper doesn't provide confidence score
            }
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            raise Exception(f"Whisper transcription failed: {str(e)}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Azure OpenAI connection and model availability"""
        try:
            # Test chat model
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[{"role": "user", "content": "테스트"}],
                max_tokens=10
            )
            
            return {
                "status": "connected",
                "whisper_available": True,
                "embedding_available": True,
                "chat_available": bool(response.choices[0].message.content)
            }
            
        except Exception as e:
            logger.error(f"Azure OpenAI connection test failed: {e}")
            return {
                "status": "disconnected",
                "error": str(e),
                "whisper_available": False,
                "embedding_available": False,
                "chat_available": False
            }
    
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
    
    def _format_reshuffle_context(self, reshuffle_context: List[Dict]) -> str:
        """Format reshuffle context for AI analysis"""
        if not reshuffle_context:
            return "이전 요청 이력 없음"
        
        formatted_context = []
        for i, context in enumerate(reshuffle_context[-3:], 1):  # Show last 3 requests
            preference = context.get('preference_text', '알 수 없음')
            timestamp = context.get('created_at', '')
            formatted_context.append(f"{i}. '{preference}' ({timestamp[:10] if timestamp else '날짜 미상'})")
        
        return "\n".join(formatted_context)
    
    async def analyze_user_preference(self, preference_text: str) -> Dict[str, Any]:
        """
        Intelligently analyze user's preference text to extract matching criteria
        Uses AI to understand complex, nuanced preferences beyond simple keywords
        """
        system_prompt = """
        당신은 한국 결혼정보회사의 매칭 전문가입니다.
        사용자가 새로운 매칭을 위해 제시한 선호도를 분석하여, 
        실제 프로필에서 찾을 수 있는 구체적인 매칭 조건으로 변환해주세요.

        분석 관점:
        - 음식/요리 선호도 (매운음식, 단음식, 특정 요리, 외식 스타일 등)
        - 활동/취미 (운동, 문화활동, 야외활동, 실내활동 등)
        - 성격/라이프스타일 (활발함, 차분함, 사교성, 집중력 등)
        - 가치관 (가족관, 커리어관, 금전관, 종교관 등)
        - 외모/스타일 선호도
        - 지역/환경 선호도

        중요: 실제 사용자 답변에서 찾을 수 있는 키워드와 패턴으로 변환해주세요.
        """

        user_prompt = f"""
        사용자 선호도: "{preference_text}"

        위 선호도를 분석하여 다음 JSON 형식으로 응답해주세요:

        {{
            "preference_category": "주요 선호도 카테고리 (음식, 활동, 성격, 가치관, 외모, 지역 중 하나)",
            "search_keywords": ["실제 답변에서 찾을 수 있는 키워드들"],
            "answer_patterns": [
                "이런 답변을 가진 사람을 찾으세요 1",
                "이런 답변을 가진 사람을 찾으세요 2"
            ],
            "matching_criteria": {{
                "must_have": ["필수로 포함해야 할 요소들"],
                "nice_to_have": ["있으면 좋을 요소들"],
                "avoid": ["피해야 할 요소들"]
            }},
            "confidence_score": 0.8,
            "explanation": "이 선호도는 왜 이렇게 분석되었는지 간단한 설명"
        }}

        예시:
        "매운걸 좋아하는 사람" → 음식 카테고리, ["매운", "맵", "매콤"] 키워드로 분석
        "활발한 사람" → 성격 카테고리, ["활발", "에너지", "사교"] 키워드로 분석
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
            
            # Clean up markdown if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            analysis_data = json.loads(content)
            
            logger.info(f"AI preference analysis for '{preference_text}': {analysis_data.get('preference_category', 'unknown')}")
            return analysis_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI preference analysis: {e}")
            # Fallback to simple analysis
            return self._fallback_preference_analysis(preference_text)
        except Exception as e:
            logger.error(f"Failed to analyze preference with AI: {e}")
            return self._fallback_preference_analysis(preference_text)
    
    async def generate_followup_question(
        self,
        question_text: str,
        answer: str,
        question_category: str,
        previous_answers: List[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Detect ambiguity in a user's answer and generate a context-aware follow-up question.
        Returns: {ambiguity_score, reason, followup_question}
        """
        prev_context = ""
        if previous_answers:
            recent = previous_answers[-3:]
            prev_context = "\n".join(
                f"- {a.get('question_text', a.get('question_id', ''))}: {a.get('answer_value', '')}"
                for a in recent
            )

        system_prompt = (
            self._MANAGER_PERSONA + "\n\n"
            "역할: 사용자의 답변이 모호하거나 불명확한 경우, 더 구체적인 정보를 수집하기 위해 "
            "맥락에 맞는 추가 질문을 생성합니다.\n\n"
            "모호 판단 기준:\n"
            "- 모호한 표현: '상관없어요', '괜찮아요', '모르겠어요', 한 단어 답변 등\n"
            "- 구체성 부족: 본인의 실제 생각/경험이 드러나지 않는 답변\n"
            "- 맥락 불일치: 이전 답변과 모순되거나 연결이 약한 답변"
        )

        user_prompt = f"""
        질문 카테고리: {question_category}
        원본 질문: {question_text}
        사용자 답변: "{answer}"
        
        {f"이전 답변 맥락:{chr(10)}{prev_context}" if prev_context else ""}
        
        위 답변을 분석하여 다음 JSON 형식으로 응답하세요:
        {{
            "ambiguity_score": 0.0~1.0 (0=명확, 1=완전히 모호),
            "reason": "모호한 이유 또는 명확한 이유 (한 문장)",
            "followup_question": "추가 질문 (필요한 경우만, 없으면 null)",
            "followup_example": "추가 질문에 대한 답변 예시 (있으면)"
        }}
        
        예시:
        답변 "종교는 상관없어요" → followup: "종교 자체를 중요하게 생각하지 않으시는 건가요, 
        아니면 상대방의 종교에 따라 유연하게 생각하시는 건가요?"
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"generate_followup_question failed: {e}")
            return {"ambiguity_score": 0.5, "reason": "분석 실패", "followup_question": None}

    async def diagnose_profile_quality(
        self,
        profile_data: Dict,
        answers_summary: Dict,
        existing_issues: List[Dict] = None,
    ) -> Dict[str, Any]:
        """
        AI-powered profile quality analysis beyond rule-based checks.
        Returns additional issues, recommendations, market_percentile.
        """
        system_prompt = (
            self._MANAGER_PERSONA + "\n\n"
            "역할: 수천 개의 프로필을 분석한 경험을 바탕으로 사용자 프로필의 강점과 개선점을 진단합니다.\n\n"
            "핵심 관점:\n"
            "- 답변의 진실성과 구체성\n"
            "- 매칭 상대방이 매력을 느낄 수 있는 요소\n"
            "- 결혼 의지와 진지함이 전달되는지\n"
            "- 개인의 가치관이 명확하게 드러나는지"
        )

        open_answers = answers_summary.get("open_answers", [])
        answers_text = "\n".join(f"- {a}" for a in open_answers[:3]) if open_answers else "서술형 답변 없음"

        user_prompt = f"""
        프로필 요약:
        - 사진 수: {len(profile_data.get('photos', []))}
        - 답변 완성도: {answers_summary.get('answered_count', 0)}/{answers_summary.get('total_questions', 40)}
        - 딜브레이커 수: {answers_summary.get('dealbreaker_count', 0)}
        
        서술형 답변 샘플:
        {answers_text}
        
        이미 발견된 문제들:
        {json.dumps(existing_issues or [], ensure_ascii=False)}
        
        추가 분석을 통해 다음 JSON 형식으로 응답하세요:
        {{
            "additional_issues": [
                {{
                    "severity": "high/medium/low",
                    "issue": "문제 설명",
                    "impact": "매칭에 미치는 영향",
                    "solution": "구체적 해결 방안"
                }}
            ],
            "recommendations": ["추천 1", "추천 2", "추천 3"],
            "market_percentile": 상위 몇 % (숫자만, 낮을수록 좋음, 예: 30은 상위 30%)
        }}
        
        이미 발견된 문제는 중복 언급하지 마세요.
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=800,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"diagnose_profile_quality failed: {e}")
            return {"additional_issues": [], "recommendations": [], "market_percentile": 50}

    async def ai_manager_chat(
        self,
        user_message: str,
        conversation_history: List[Dict],
        user_context: Dict,
    ) -> Dict[str, Any]:
        """
        Conversational AI manager response.
        Returns: {message, suggested_actions, intent, extracted_insights}
        """
        nickname = user_context.get("nickname", "회원님")
        profile_score = user_context.get("profile_score")
        top_issues = user_context.get("top_issues", [])
        feedback_summary = user_context.get("feedback_summary", {})

        context_block = f"""
        회원 정보:
        - 닉네임: {nickname}
        - 신뢰 등급: {user_context.get('trust_tier', '미확인')}
        - 구독 상태: {user_context.get('subscription_status', 'none')}
        {f"- 프로필 품질 점수: {profile_score}/100" if profile_score else ""}
        {f"- 주요 프로필 개선 필요사항: {', '.join(top_issues)}" if top_issues else ""}
        {f"- 매칭 피드백 평균: {feedback_summary.get('avg_rating', 'N/A')}점" if feedback_summary.get('total_feedback') else ""}
        """

        system_prompt = (
            self._MANAGER_PERSONA + "\n\n"
            + context_block +
            "\n역할:\n"
            "- 결혼/연애 목표와 타임라인을 대화를 통해 파악\n"
            "- 매칭 불만족 시 원인 분석 및 구체적 해결책 제시\n"
            "- 프로필 개선 방향 코칭 (구체적, 실행 가능하게)\n"
            "- 매칭된 상대에 대한 추가 인사이트 제공\n"
            "- 정서적 지지와 현실적 조언 균형\n\n"
            "말투 지침:\n"
            "- 따뜻하되 전문적인 톤 유지\n"
            "- 구체적 사례와 수치로 설명\n"
            "- 2-4문장으로 간결하게 (필요 시 더 길게)\n"
            "- 과도한 존댓말이나 딱딱한 격식 피하기\n\n"
            'JSON 형식으로 응답: {"message": "응답 텍스트", "intent": "matching_help|profile_coaching|emotional_support|general_info", "suggested_actions": ["액션1", "액션2"], "extracted_insights": {}}'
        )

        # Build conversation history for context (last 10 messages)
        history_messages = []
        for msg in conversation_history[-10:]:
            role = msg.get("role", "user")
            if role in ("user", "assistant"):
                history_messages.append({"role": role, "content": msg.get("content", "")})

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *history_messages,
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=600,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"ai_manager_chat failed: {e}")
            return {
                "message": f"{nickname}, 잠시 후 다시 시도해 주세요. 연결에 일시적인 문제가 있습니다.",
                "intent": "error",
                "suggested_actions": ["다시 시도"],
                "extracted_insights": {},
            }

    async def generate_coaching_message(
        self,
        nickname: str,
        trigger: Dict[str, Any],
        profile_completion_pct: int,
        avg_rating: float,
    ) -> Dict[str, Any]:
        """
        Generate a proactive coaching message based on user state and trigger.
        Returns: {message, suggested_actions}
        """
        trigger_type = trigger.get("type", "general")
        trigger_desc = {
            "first_time_welcome": "처음 AI 매니저를 만나는 사용자입니다.",
            "inactivity_nudge": f"{trigger.get('days_inactive', 3)}일간 활동이 없는 사용자입니다.",
            "profile_incomplete": f"프로필 완성도가 {profile_completion_pct}%이고, 남은 질문이 {trigger.get('remaining', 0)}개입니다.",
            "low_satisfaction": f"최근 매칭 평균 만족도가 {avg_rating}점이며, 주요 불만 사항은 {trigger.get('common_dealbreakers', [])}입니다.",
            "milestone_first_feedback": "첫 번째 매칭 피드백을 남긴 사용자입니다.",
            "milestone_profile_complete": "프로필을 100% 완성한 사용자입니다.",
        }.get(trigger_type, "일반 코칭 메시지를 생성합니다.")

        system_prompt = (
            self._MANAGER_PERSONA + "\n\n"
            "역할: 사용자에게 먼저 다가가는 프로액티브 코칭 메시지를 작성합니다.\n"
            "원칙:\n"
            "- 짧고 따뜻하게 (2-3문장)\n"
            "- 구체적 행동을 유도\n"
            "- 부담주지 않으면서 동기부여\n"
            "- 사용자 이름을 자연스럽게 사용\n\n"
            'JSON 형식: {"message": "코칭 메시지", "suggested_actions": ["액션1", "액션2"]}'
        )

        user_prompt = f"닉네임: {nickname}\n트리거: {trigger_desc}\n프로필 완성도: {profile_completion_pct}%"

        try:
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=300,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"generate_coaching_message failed: {e}")
            raise

    def _fallback_preference_analysis(self, preference_text: str) -> Dict[str, Any]:
        """Simple fallback when AI analysis fails"""
        preference_lower = preference_text.lower()
        
        # Simple keyword detection
        if any(word in preference_lower for word in ['매운', '맵', '매콤']):
            return {
                "preference_category": "음식",
                "search_keywords": ["매운", "맵"],
                "answer_patterns": ["매운 음식을 좋아한다고 답한 사람"],
                "matching_criteria": {
                    "must_have": ["매운음식선호"],
                    "nice_to_have": ["요리관심"],
                    "avoid": ["매운음식싫어"]
                },
                "confidence_score": 0.6,
                "explanation": "간단한 키워드 매칭으로 분석됨"
            }
        
        # Default fallback
        return {
            "preference_category": "기타",
            "search_keywords": [preference_text],
            "answer_patterns": [f"{preference_text}와 관련된 답변"],
            "matching_criteria": {
                "must_have": [preference_text],
                "nice_to_have": [],
                "avoid": []
            },
            "confidence_score": 0.3,
            "explanation": "구체적 분석 불가, 원문 검색"
        }

# Singleton instance
azure_openai_service = AzureOpenAIService()