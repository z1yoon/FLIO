"""
Adaptive Question Generator
Uses Qwen2.5-7B-Instruct for Korean language understanding

Features:
- Analyze user answers for clarity and completeness
- Generate follow-up questions when answers are vague
- Analyze reshuffle requests and suggest improvements
- Generate personalized match explanations
"""

import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AdaptiveQuestionGenerator:
    """
    Qwen2.5-7B based adaptive question generator
    
    Why Qwen2.5 over EXAONE:
    1. Apache 2.0 license (commercial use allowed)
    2. #1 on multilingual benchmarks including Korean
    3. Better instruction following
    4. Active community and tooling
    """
    
    def __init__(self, model_name: str = "Qwen/Qwen2.5-7B-Instruct"):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            logger.info(f"Loading {model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype="auto",
                device_map="auto"
            )
            logger.info("Qwen2.5 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Qwen2.5: {e}")
            self.model = None
            self.tokenizer = None
    
    def analyze_answer(self, question: str, answer: str) -> Dict[str, Any]:
        """
        Analyze user's answer for clarity and extract key information
        
        Returns:
            {
                "clarity_score": 0-100,
                "sentiment": "positive/neutral/negative",
                "key_info": ["extracted key points"],
                "is_vague": true/false,
                "needs_followup": true/false,
                "followup_reason": "why followup is needed"
            }
        """
        prompt = f"""당신은 FLIO 데이팅 앱의 AI 분석가입니다.
사용자의 답변을 분석하고 명확도를 평가하세요.

질문: {question}
답변: {answer}

분석 기준:
1. 답변이 구체적인가? (숫자, 시기, 명확한 선호도 포함 여부)
2. 추가 정보가 필요한가?
3. 감정적 톤은 어떤가?

JSON 형식으로 응답하세요 (다른 텍스트 없이 JSON만):
{{
    "clarity_score": 0-100 사이의 숫자,
    "sentiment": "positive" 또는 "neutral" 또는 "negative",
    "key_info": ["추출된 핵심 정보 배열"],
    "is_vague": true 또는 false,
    "needs_followup": true 또는 false,
    "followup_reason": "후속 질문이 필요한 이유 (필요 없으면 null)"
}}"""

        response = self._generate(prompt)
        
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse analysis response: {response}")
            return {
                "clarity_score": 50,
                "sentiment": "neutral",
                "key_info": [],
                "is_vague": True,
                "needs_followup": True,
                "followup_reason": "분석 실패로 추가 확인 필요"
            }
    
    def generate_followup_questions(
        self,
        question: str,
        answer: str,
        user_profile: Dict,
        num_questions: int = 3
    ) -> List[Dict[str, str]]:
        """
        Generate follow-up questions to get more specific information
        
        This is the core feature that makes FLIO different from other dating apps:
        - Acts like a 결혼정보회사 매니저
        - Digs deeper into vague answers
        - Helps users be honest (since it's AI, not a human judging them)
        """
        profile_str = json.dumps(user_profile, ensure_ascii=False, indent=2)
        
        prompt = f"""당신은 FLIO 데이팅 앱의 AI 매칭 매니저입니다.
결혼정보회사 매니저처럼 사용자의 진짜 원하는 것을 파악하세요.

## 역할
- 따뜻하고 친근한 말투
- 판단하지 않는 중립적 태도
- 솔직한 답변을 유도 (AI라서 부끄러워할 필요 없다고 느끼게)

## 이전 질문
{question}

## 사용자 답변
{answer}

## 현재 프로필 정보
{profile_str}

## 지침
1. 답변이 "생각 중", "모르겠어요", "상황에 따라" 같이 애매하면 구체화 질문
2. 숫자/시기/조건을 명확히 알 수 있는 질문
3. 매칭에 중요한 정보를 얻을 수 있는 질문
4. 한국 문화/사회 맥락 고려

{num_questions}개의 후속 질문을 JSON 배열로 생성하세요 (다른 텍스트 없이 JSON만):
[
    {{
        "question": "질문 내용 (존댓말, 친근한 톤)",
        "category": "결혼/가족/재정/가치관/라이프스타일 중 하나",
        "priority": "high/medium/low",
        "goal": "이 질문으로 알고 싶은 것"
    }}
]"""

        response = self._generate(prompt)
        
        try:
            json_str = self._extract_json(response)
            questions = json.loads(json_str)
            return questions[:num_questions]
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse questions: {response}")
            return [{
                "question": "조금 더 구체적으로 말씀해주실 수 있을까요?",
                "category": "일반",
                "priority": "medium",
                "goal": "답변 명확화"
            }]
    
    def analyze_reshuffle_request(
        self,
        user_profile: Dict,
        current_filters: Dict,
        reshuffle_reason: str,
        rejected_profiles: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Analyze why user wants to reshuffle and suggest improvements
        
        This feature:
        1. Understands WHY user is unsatisfied
        2. Identifies missing/unclear profile information
        3. Suggests additional questions if needed
        4. Adjusts matching filters for better results
        """
        profile_str = json.dumps(user_profile, ensure_ascii=False, indent=2)
        filters_str = json.dumps(current_filters, ensure_ascii=False, indent=2)
        
        rejected_info = ""
        if rejected_profiles:
            rejected_str = json.dumps(rejected_profiles[:5], ensure_ascii=False, indent=2)
            rejected_info = f"\n## 거절된 프로필 샘플 (최근 5개)\n{rejected_str}"
        
        prompt = f"""당신은 FLIO 데이팅 앱의 AI 매칭 전문가입니다.

## 현재 사용자 프로필
{profile_str}

## 현재 매칭 필터
{filters_str}

## 리셔플 요청 이유
{reshuffle_reason}
{rejected_info}

## 분석 요청
1. 사용자가 왜 현재 매칭에 불만족한지 분석
2. 프로필에서 누락되거나 모호한 정보 파악
3. 추가 질문이 필요한지 판단
4. 필터 조정 제안
5. 아바타가 사용자에게 전할 공감 메시지 작성

JSON으로 응답하세요 (다른 텍스트 없이 JSON만):
{{
    "analysis": "리셔플 이유 분석 (1-2문장)",
    "user_intent": "사용자가 진짜 원하는 것 추론",
    "missing_info": ["프로필에서 누락된 정보 배열"],
    "needs_questions": true 또는 false,
    "suggested_questions": [
        {{
            "question": "추가 질문 (친근한 톤)",
            "category": "카테고리",
            "reason": "이 질문이 필요한 이유"
        }}
    ],
    "filter_suggestions": {{
        "age_range": [최소나이, 최대나이] 또는 null,
        "location_radius_km": 숫자 또는 null,
        "priority_changes": ["우선순위 변경 제안"]
    }},
    "avatar_message": "아바타가 사용자에게 전할 공감+안내 메시지 (2-3문장, 따뜻한 톤)"
}}"""

        response = self._generate(prompt, max_tokens=1500)
        
        try:
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse reshuffle analysis: {response}")
            return {
                "analysis": "리셔플 요청을 분석 중입니다",
                "user_intent": "더 나은 매칭을 원함",
                "missing_info": [],
                "needs_questions": True,
                "suggested_questions": [{
                    "question": "어떤 점이 가장 마음에 안 드셨나요?",
                    "category": "일반",
                    "reason": "불만족 원인 파악"
                }],
                "filter_suggestions": {},
                "avatar_message": "알겠어요! 더 나은 매칭을 위해 몇 가지만 더 여쭤볼게요. 😊"
            }
    
    def generate_match_explanation(
        self,
        profile_a: Dict,
        profile_b: Dict,
        match_score: float
    ) -> Dict[str, Any]:
        """
        Generate human-readable explanation for why two profiles match
        """
        prompt = f"""당신은 FLIO 데이팅 앱의 AI 매칭 설명가입니다.
두 사용자가 왜 호환성이 높은지 따뜻하고 긍정적인 톤으로 설명하세요.

## 사용자 A
{json.dumps(profile_a, ensure_ascii=False, indent=2)}

## 사용자 B
{json.dumps(profile_b, ensure_ascii=False, indent=2)}

## 매칭 점수
{match_score:.1f}%

JSON으로 응답하세요 (다른 텍스트 없이 JSON만):
{{
    "summary": "한 줄 요약 (긍정적 톤)",
    "match_points": [
        {{
            "category": "카테고리",
            "type": "match" 또는 "partial" 또는 "discuss",
            "icon": "✅" 또는 "🔶" 또는 "💬",
            "description": "설명 (1-2문장)"
        }}
    ],
    "conversation_starters": ["첫 대화 주제 제안 3개"]
}}"""

        response = self._generate(prompt)
        
        try:
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {
                "summary": f"{match_score:.0f}% 매칭! 서로에게 좋은 인연이 될 수 있어요.",
                "match_points": [],
                "conversation_starters": ["취미에 대해 이야기해보세요"]
            }
    
    def _generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """Internal generation method"""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        messages = [{"role": "user", "content": prompt}]
        
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        response = self.tokenizer.decode(
            outputs[0][len(inputs['input_ids'][0]):],
            skip_special_tokens=True
        )
        
        return response.strip()
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that might contain other content"""
        # Try to find JSON array or object
        import re
        
        # Look for JSON object
        obj_match = re.search(r'\{[\s\S]*\}', text)
        if obj_match:
            return obj_match.group()
        
        # Look for JSON array
        arr_match = re.search(r'\[[\s\S]*\]', text)
        if arr_match:
            return arr_match.group()
        
        return text
