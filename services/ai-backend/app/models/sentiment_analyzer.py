"""
Sentiment & Personality Analyzer
Analyzes user answers for emotional state and personality traits

Features:
1. Sentiment Analysis - Detect vague/unclear answers
2. Personality Embedding - Extract Big 5 traits for matching
3. Communication Style - Understand how user prefers to communicate

⚠️ IMPORTANT: Never skip questions!
- If user is hesitant → Ask follow-up to get CLEAR answer
- If user is vague → Provide specific options to choose from
- Goal: Get clear answers for better matching, not avoid topics
"""

import logging
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Analyze user answers for sentiment and emotional state
    
    Uses Qwen2.5 for Korean sentiment understanding
    """
    
    def __init__(self, llm_model=None):
        """
        Args:
            llm_model: Pre-loaded Qwen2.5 model (optional, uses shared model)
        """
        self.llm = llm_model
        self._load_model()
    
    def _load_model(self):
        """Load Qwen2.5 if not provided"""
        if self.llm is not None:
            return
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            model_name = "Qwen/Qwen2.5-7B-Instruct"
            logger.info(f"Loading sentiment analyzer: {model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype="auto",
                device_map="auto"
            )
            self.llm = True
            logger.info("Sentiment analyzer loaded")
            
        except Exception as e:
            logger.error(f"Failed to load sentiment analyzer: {e}")
            self.llm = None
    
    def analyze_sentiment(self, answer: str, question: str = None) -> Dict[str, Any]:
        """
        Analyze sentiment of user's answer
        
        Returns:
            {
                "primary_emotion": "hesitation" | "enthusiasm" | "neutral" | "discomfort" | "honesty",
                "confidence": 0.0-1.0,
                "emotions": {
                    "hesitation": 0.3,
                    "enthusiasm": 0.1,
                    "discomfort": 0.0,
                    "honesty": 0.5,
                    "defensiveness": 0.1
                },
                "communication_style": "direct" | "indirect" | "thoughtful" | "evasive",
                "engagement_level": "high" | "medium" | "low",
                "suggestion": "답변이 다소 모호합니다. 구체적인 예시를 요청해보세요."
            }
        """
        if self.llm is None:
            return self._rule_based_sentiment(answer)
        
        return self._llm_sentiment(answer, question)
    
    def _rule_based_sentiment(self, answer: str) -> Dict[str, Any]:
        """Rule-based sentiment analysis (fallback)"""
        emotions = {
            "hesitation": 0.0,
            "enthusiasm": 0.0,
            "discomfort": 0.0,
            "honesty": 0.5,
            "defensiveness": 0.0
        }
        
        # Hesitation markers
        hesitation_words = ["글쎄", "모르겠", "생각 중", "아직", "잘", "음", "어", "그게"]
        for word in hesitation_words:
            if word in answer:
                emotions["hesitation"] += 0.15
        
        # Enthusiasm markers
        enthusiasm_words = ["정말", "진짜", "너무", "완전", "좋아", "사랑", "확실", "당연"]
        for word in enthusiasm_words:
            if word in answer:
                emotions["enthusiasm"] += 0.15
        
        # Discomfort markers
        discomfort_words = ["그건", "왜", "굳이", "싫", "불편"]
        for word in discomfort_words:
            if word in answer:
                emotions["discomfort"] += 0.2
        
        # Normalize
        for key in emotions:
            emotions[key] = min(1.0, emotions[key])
        
        # Determine primary emotion
        primary = max(emotions.items(), key=lambda x: x[1])
        
        # Determine engagement
        if len(answer) > 100:
            engagement = "high"
        elif len(answer) > 30:
            engagement = "medium"
        else:
            engagement = "low"
        
        return {
            "primary_emotion": primary[0] if primary[1] > 0.3 else "neutral",
            "confidence": primary[1] if primary[1] > 0.3 else 0.5,
            "emotions": emotions,
            "communication_style": "indirect" if emotions["hesitation"] > 0.3 else "direct",
            "engagement_level": engagement,
            "suggestion": self._get_suggestion(primary[0], engagement)
        }
    
    def _llm_sentiment(self, answer: str, question: str) -> Dict[str, Any]:
        """LLM-based sentiment analysis"""
        prompt = f"""사용자의 답변을 분석하여 감정 상태와 소통 스타일을 파악하세요.

질문: {question or "프로필 관련 질문"}
답변: {answer}

분석 기준:
1. 주요 감정: hesitation(망설임), enthusiasm(열정), discomfort(불편함), honesty(솔직함), defensiveness(방어적)
2. 소통 스타일: direct(직접적), indirect(간접적), thoughtful(신중함), evasive(회피적)
3. 참여도: high(적극적), medium(보통), low(소극적)

JSON 형식으로만 응답하세요:
{{
    "primary_emotion": "감정명",
    "confidence": 0.0-1.0,
    "emotions": {{"hesitation": 0.0, "enthusiasm": 0.0, "discomfort": 0.0, "honesty": 0.0, "defensiveness": 0.0}},
    "communication_style": "스타일",
    "engagement_level": "high/medium/low",
    "suggestion": "다음 질문 전략 제안"
}}"""

        try:
            response = self._generate(prompt)
            return json.loads(self._extract_json(response))
        except Exception as e:
            logger.warning(f"LLM sentiment failed: {e}")
            return self._rule_based_sentiment(answer)
    
    def _get_suggestion(self, emotion: str, engagement: str) -> str:
        """
        Get suggestion based on sentiment
        
        IMPORTANT: Never skip questions! Always get clear answers.
        If user is hesitant, ask follow-up to clarify, not change topic.
        """
        suggestions = {
            "hesitation": "답변이 모호합니다. '예를 들어 1년 안에? 3년 안에?' 처럼 구체적인 옵션을 제시해서 명확한 답변을 받으세요.",
            "enthusiasm": "긍정적인 반응입니다! 더 구체적인 후속 질문으로 자세히 알아보세요.",
            "discomfort": "불편해하는 것 같지만, 매칭에 중요한 질문입니다. 부드럽게 다시 질문해서 답변을 받으세요.",
            "honesty": "솔직한 답변입니다. 후속 질문으로 더 자세히 알아보세요.",
            "defensiveness": "방어적인 반응입니다. 왜 이 질문이 중요한지 설명하고 다시 답변을 받으세요.",
            "neutral": "적절한 답변입니다."
        }
        
        base = suggestions.get(emotion, suggestions["neutral"])
        
        if engagement == "low":
            base += " (답변이 짧습니다. 더 자세한 답변을 요청하세요.)"
        
        return base
    
    def _generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate response from LLM"""
        messages = [{"role": "user", "content": prompt}]
        
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.3,
            do_sample=True
        )
        
        return self.tokenizer.decode(
            outputs[0][len(inputs['input_ids'][0]):],
            skip_special_tokens=True
        )
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text"""
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        return match.group() if match else "{}"


class PersonalityEmbedding:
    """
    Extract personality traits from user answers
    
    Based on Big 5 (OCEAN) model:
    - Openness: 새로운 경험에 대한 개방성
    - Conscientiousness: 성실성, 계획성
    - Extraversion: 외향성
    - Agreeableness: 친화성
    - Neuroticism: 정서적 안정성
    
    Used for:
    - Compatibility scoring (similar/complementary personalities)
    - Communication style matching
    - Activity preference prediction
    """
    
    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model
        self.trait_weights = {
            "openness": 0.2,
            "conscientiousness": 0.2,
            "extraversion": 0.2,
            "agreeableness": 0.2,
            "neuroticism": 0.2
        }
    
    def extract_traits(self, answers: List[Dict[str, str]]) -> Dict[str, float]:
        """
        Extract Big 5 personality traits from user's answers
        
        Args:
            answers: List of {"question": "...", "answer": "..."}
        
        Returns:
            {
                "openness": 0.0-1.0,
                "conscientiousness": 0.0-1.0,
                "extraversion": 0.0-1.0,
                "agreeableness": 0.0-1.0,
                "neuroticism": 0.0-1.0
            }
        """
        traits = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5
        }
        
        for qa in answers:
            answer = qa.get("answer", "")
            question = qa.get("question", "")
            
            # Openness indicators
            if any(w in answer for w in ["새로운", "도전", "여행", "배우", "경험"]):
                traits["openness"] += 0.1
            
            # Conscientiousness indicators
            if any(w in answer for w in ["계획", "정리", "목표", "체계", "준비"]):
                traits["conscientiousness"] += 0.1
            
            # Extraversion indicators
            if any(w in answer for w in ["친구", "모임", "파티", "사람들", "외출"]):
                traits["extraversion"] += 0.1
            elif any(w in answer for w in ["혼자", "조용", "집", "내향"]):
                traits["extraversion"] -= 0.1
            
            # Agreeableness indicators
            if any(w in answer for w in ["배려", "도움", "양보", "이해", "공감"]):
                traits["agreeableness"] += 0.1
            
            # Neuroticism (inverse = emotional stability)
            if any(w in answer for w in ["걱정", "불안", "스트레스", "예민"]):
                traits["neuroticism"] += 0.1
            elif any(w in answer for w in ["편안", "차분", "안정", "여유"]):
                traits["neuroticism"] -= 0.1
        
        # Normalize to 0-1 range
        for key in traits:
            traits[key] = max(0.0, min(1.0, traits[key]))
        
        return traits
    
    def calculate_compatibility(
        self,
        traits_a: Dict[str, float],
        traits_b: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculate personality compatibility between two users
        
        Returns:
            {
                "overall_score": 0.0-1.0,
                "by_trait": {...},
                "compatibility_type": "similar" | "complementary" | "balanced",
                "strengths": ["...", "..."],
                "potential_conflicts": ["...", "..."]
            }
        """
        by_trait = {}
        total_score = 0.0
        
        for trait, weight in self.trait_weights.items():
            diff = abs(traits_a.get(trait, 0.5) - traits_b.get(trait, 0.5))
            
            # For some traits, similarity is good
            if trait in ["conscientiousness", "openness"]:
                score = 1.0 - diff
            # For some traits, moderate difference is good
            elif trait in ["extraversion"]:
                score = 1.0 - (diff * 0.5)  # Less penalty for difference
            # For neuroticism, lower is better for both
            elif trait == "neuroticism":
                avg = (traits_a.get(trait, 0.5) + traits_b.get(trait, 0.5)) / 2
                score = 1.0 - avg  # Both being calm is good
            else:
                score = 1.0 - diff
            
            by_trait[trait] = score
            total_score += score * weight
        
        # Determine compatibility type
        avg_diff = sum(
            abs(traits_a.get(t, 0.5) - traits_b.get(t, 0.5))
            for t in self.trait_weights
        ) / len(self.trait_weights)
        
        if avg_diff < 0.2:
            compat_type = "similar"
        elif avg_diff > 0.4:
            compat_type = "complementary"
        else:
            compat_type = "balanced"
        
        return {
            "overall_score": total_score,
            "by_trait": by_trait,
            "compatibility_type": compat_type,
            "strengths": self._get_strengths(traits_a, traits_b),
            "potential_conflicts": self._get_conflicts(traits_a, traits_b)
        }
    
    def _get_strengths(self, a: Dict, b: Dict) -> List[str]:
        """Identify relationship strengths"""
        strengths = []
        
        if a.get("agreeableness", 0) > 0.6 and b.get("agreeableness", 0) > 0.6:
            strengths.append("두 분 모두 배려심이 높아 갈등을 잘 해결할 수 있어요")
        
        if abs(a.get("extraversion", 0.5) - b.get("extraversion", 0.5)) < 0.2:
            strengths.append("사회적 활동에 대한 선호가 비슷해요")
        
        if a.get("openness", 0) > 0.6 and b.get("openness", 0) > 0.6:
            strengths.append("새로운 경험을 함께 즐길 수 있어요")
        
        return strengths or ["다양한 면에서 서로를 보완할 수 있어요"]
    
    def _get_conflicts(self, a: Dict, b: Dict) -> List[str]:
        """Identify potential conflicts"""
        conflicts = []
        
        if abs(a.get("conscientiousness", 0.5) - b.get("conscientiousness", 0.5)) > 0.4:
            conflicts.append("계획성에 대한 차이가 있을 수 있어요")
        
        if a.get("neuroticism", 0) > 0.7 or b.get("neuroticism", 0) > 0.7:
            conflicts.append("스트레스 상황에서 소통이 중요해요")
        
        return conflicts or []
