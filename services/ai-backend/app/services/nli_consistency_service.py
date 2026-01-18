"""
FLIO NLI Consistency Service
Natural Language Inference for detecting contradictions

Uses Azure OpenAI GPT-4o-mini to detect logical inconsistencies in user statements.
Part of the Trust Score system for Korean marriage agency style verification.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

from .azure_openai_service import azure_openai_service
from ..models.database import get_supabase_client

logger = logging.getLogger(__name__)


class NLIRelationship(str, Enum):
    """NLI relationship types"""
    ENTAILMENT = "entailment"      # Statements support each other
    NEUTRAL = "neutral"            # Statements are unrelated
    CONTRADICTION = "contradiction" # Statements conflict


class ConsistencyCheckType(str, Enum):
    """Types of consistency checks"""
    PROFILE_VS_ANSWERS = "profile_vs_answers"
    CROSS_SECTION = "cross_section"
    TEXT_INTERNAL = "text_answers_internal"
    TEMPORAL = "temporal"
    PROFILE_VS_DOCUMENTS = "profile_vs_documents"


class ContradictionResult(BaseModel):
    """Result of a single contradiction check"""
    source_a: str
    statement_a: str
    source_b: str
    statement_b: str
    relationship: str
    contradiction_score: float
    confidence: float
    reasoning: str


class ConsistencyCheckResult(BaseModel):
    """Result of full consistency check"""
    user_id: str
    overall_score: float  # 1.0 = fully consistent, 0.0 = major contradictions
    check_count: int
    contradictions_found: int
    contradiction_details: List[ContradictionResult]
    check_timestamp: datetime


class NLIConsistencyService:
    """
    Service for detecting logical contradictions in user profiles
    Uses Azure OpenAI for Natural Language Inference
    """

    # Statement extraction mappings
    PROFILE_STATEMENT_FIELDS = {
        'annual_income_range': '연봉이 {value}입니다',
        'education_level': '학력이 {value}입니다',
        'employment_status': '고용 상태가 {value}입니다',
        'marital_status': '혼인 상태가 {value}입니다',
        'job_title': '직업이 {value}입니다'
    }

    # Question ID to statement mappings
    ANSWER_STATEMENT_MAPPINGS = {
        'marriage_timeline': '결혼 시기에 대해 "{value}"라고 답했습니다',
        'children_plan': '자녀 계획에 대해 "{value}"라고 답했습니다',
        'career_priority': '일과 가정의 우선순위에 대해 "{value}"라고 답했습니다',
        'financial_transparency': '재정 투명성에 대해 "{value}"라고 답했습니다',
        'personal_values_lifestyle': '개인 가치관에 대해 "{value}"라고 답했습니다',
        'ideal_relationship_dynamic': '이상적인 관계에 대해 "{value}"라고 답했습니다'
    }

    # Known compatible statement pairs (to avoid false positives)
    COMPATIBLE_PAIRS = [
        ('높은 연봉', '돈보다 사람이 중요'),  # Can have high income but value people
        ('안정적인 직장', '도전적인 삶'),      # Stable job but adventurous personality
    ]

    def __init__(self):
        self.supabase = get_supabase_client()

    async def check_user_consistency(self, user_id: str) -> ConsistencyCheckResult:
        """
        Run full consistency check on a user's profile and answers

        Checks:
        1. Profile vs questionnaire answers
        2. Cross-section validation
        3. Text answer internal consistency
        """
        try:
            logger.info(f"Running consistency check for user {user_id}")

            all_contradictions = []
            checks_performed = 0

            # 1. Profile vs Answers check
            profile_answer_contradictions = await self._check_profile_vs_answers(user_id)
            all_contradictions.extend(profile_answer_contradictions)
            checks_performed += 1

            # 2. Cross-section validation
            cross_section_contradictions = await self._check_cross_section(user_id)
            all_contradictions.extend(cross_section_contradictions)
            checks_performed += 1

            # 3. Text answers internal consistency
            text_contradictions = await self._check_text_answers_internal(user_id)
            all_contradictions.extend(text_contradictions)
            checks_performed += 1

            # Calculate overall consistency score
            if all_contradictions:
                avg_contradiction = sum(c.contradiction_score for c in all_contradictions) / len(all_contradictions)
                count_penalty = min(0.05 * len(all_contradictions), 0.2)
                overall_score = max(0.0, 1.0 - avg_contradiction - count_penalty)
            else:
                overall_score = 1.0

            # Store results in database
            await self._store_consistency_results(user_id, all_contradictions)

            result = ConsistencyCheckResult(
                user_id=user_id,
                overall_score=overall_score,
                check_count=checks_performed,
                contradictions_found=len(all_contradictions),
                contradiction_details=all_contradictions,
                check_timestamp=datetime.now()
            )

            logger.info(f"Consistency check completed for {user_id}: score={overall_score:.2f}, contradictions={len(all_contradictions)}")

            return result

        except Exception as e:
            logger.error(f"Consistency check failed for user {user_id}: {e}")
            # Return default (no issues) on error
            return ConsistencyCheckResult(
                user_id=user_id,
                overall_score=1.0,
                check_count=0,
                contradictions_found=0,
                contradiction_details=[],
                check_timestamp=datetime.now()
            )

    async def _check_profile_vs_answers(self, user_id: str) -> List[ContradictionResult]:
        """
        Check for contradictions between profile fields and questionnaire answers
        """
        try:
            # Get profile data
            profile_result = self.supabase.table('profiles').select(
                'annual_income_range, education_level, employment_status, '
                'marital_status, job_title, career_priority'
            ).eq('user_id', user_id).single().execute()

            if not profile_result.data:
                return []

            profile = profile_result.data

            # Get relevant answers
            answers_result = self.supabase.table('user_answers').select(
                'question_id, answer_value, answer_text'
            ).eq('user_id', user_id).execute()

            if not answers_result.data:
                return []

            answers = {
                a['question_id']: a.get('answer_text') or a.get('answer_value')
                for a in answers_result.data
            }

            # Generate statement pairs to check
            statement_pairs = []

            # Education vs career answers
            if profile.get('education_level') and answers.get('career_priority'):
                statement_pairs.append((
                    ('profile.education', f"학력이 {profile['education_level']}입니다"),
                    ('answer.career', answers['career_priority'])
                ))

            # Employment vs work-life balance
            if profile.get('employment_status') and answers.get('career_priority'):
                statement_pairs.append((
                    ('profile.employment', f"직업 상태가 {profile['employment_status']}입니다"),
                    ('answer.career', answers['career_priority'])
                ))

            # Check each pair for contradictions
            contradictions = []
            for (source_a, stmt_a), (source_b, stmt_b) in statement_pairs:
                if stmt_a and stmt_b:
                    result = await self._detect_contradiction(
                        source_a, stmt_a, source_b, stmt_b,
                        ConsistencyCheckType.PROFILE_VS_ANSWERS
                    )
                    if result and result.contradiction_score > 0.5:
                        contradictions.append(result)

            return contradictions

        except Exception as e:
            logger.error(f"Profile vs answers check failed: {e}")
            return []

    async def _check_cross_section(self, user_id: str) -> List[ContradictionResult]:
        """
        Check for contradictions across different profile sections
        """
        try:
            # Get profile with all sections
            profile_result = self.supabase.table('profiles').select(
                'annual_income_range, employment_status, job_title, education_level'
            ).eq('user_id', user_id).single().execute()

            if not profile_result.data:
                return []

            profile = profile_result.data
            contradictions = []

            # Check income vs employment status consistency
            if profile.get('annual_income_range') and profile.get('employment_status'):
                income = profile['annual_income_range']
                employment = profile['employment_status']

                # High income but unemployed is suspicious
                if '1억' in income and employment == '무직':
                    result = await self._detect_contradiction(
                        'profile.income', f"연봉이 {income}입니다",
                        'profile.employment', f"현재 {employment} 상태입니다",
                        ConsistencyCheckType.CROSS_SECTION
                    )
                    if result:
                        contradictions.append(result)

            # Check job title vs income consistency
            if profile.get('job_title') and profile.get('annual_income_range'):
                job = profile['job_title']
                income = profile['annual_income_range']

                # This would check if job title matches expected income range
                result = await self._detect_contradiction(
                    'profile.job', f"직업이 {job}입니다",
                    'profile.income', f"연봉이 {income}입니다",
                    ConsistencyCheckType.CROSS_SECTION
                )
                if result and result.contradiction_score > 0.6:
                    contradictions.append(result)

            return contradictions

        except Exception as e:
            logger.error(f"Cross-section check failed: {e}")
            return []

    async def _check_text_answers_internal(self, user_id: str) -> List[ContradictionResult]:
        """
        Check for contradictions within text (open-ended) answers
        """
        try:
            # Get text question answers
            text_question_ids = [
                'personal_values_lifestyle',
                'ideal_relationship_dynamic',
                'conflict_growth_philosophy'
            ]

            answers_result = self.supabase.table('user_answers').select(
                'question_id, answer_text'
            ).eq('user_id', user_id).in_('question_id', text_question_ids).execute()

            if not answers_result.data or len(answers_result.data) < 2:
                return []

            answers = {a['question_id']: a['answer_text'] for a in answers_result.data if a.get('answer_text')}

            if len(answers) < 2:
                return []

            contradictions = []

            # Compare pairs of text answers
            answer_list = list(answers.items())
            for i in range(len(answer_list)):
                for j in range(i + 1, len(answer_list)):
                    q1_id, answer1 = answer_list[i]
                    q2_id, answer2 = answer_list[j]

                    if answer1 and answer2:
                        result = await self._detect_contradiction(
                            f'answer.{q1_id}', answer1,
                            f'answer.{q2_id}', answer2,
                            ConsistencyCheckType.TEXT_INTERNAL
                        )
                        if result and result.contradiction_score > 0.5:
                            contradictions.append(result)

            return contradictions

        except Exception as e:
            logger.error(f"Text answers internal check failed: {e}")
            return []

    async def _detect_contradiction(
        self,
        source_a: str,
        statement_a: str,
        source_b: str,
        statement_b: str,
        check_type: ConsistencyCheckType
    ) -> Optional[ContradictionResult]:
        """
        Use Azure OpenAI to detect contradiction between two statements
        """
        try:
            system_prompt = """당신은 결혼정보회사의 프로필 검증 전문가입니다.
두 진술 간의 논리적 일관성을 분석하세요.

중요한 구분 (False Positive 방지):
- 사실(fact) vs 가치관(value): 높은 연봉을 받는 것과 돈을 중요하게 생각하는 것은 다릅니다
  예: "연봉 1억 이상" + "돈은 중요하지 않아요" → 중립적 (모순 아님)
- 소유(possession) vs 중요성(importance): 돈이 있어도 돈을 중요하지 않게 생각할 수 있습니다
- 직업적 성취 vs 개인적 가치: 성공적인 직업과 개인적 가치관은 독립적입니다
- 한국 문화적 맥락: 높은 연봉이지만 검소한 생활, 돈보다 사람을 중시하는 것은 정상적입니다

분석 기준:
1. 두 진술이 서로 모순되는지 확인 (사실적 모순만 탐지)
2. 한국 문화적 맥락 고려 (예: 높은 연봉이지만 검소한 생활 가능)
3. 명백한 거짓말이나 과장 탐지 (예: "수입 없음" vs "연봉 1억")
4. 사소한 차이와 심각한 모순 구분
5. 사실적 모순만 탐지, 가치관 차이는 정상으로 간주

실제 모순 예시:
- "연봉 1억 이상" vs "현재 수입이 전혀 없어요" → 모순 (0.9)
- "대기업 임원" vs "무직" → 모순 (0.9)
- "대학 졸업" vs "고등학교도 졸업 안 했어요" → 모순 (0.9)

모순이 아닌 예시:
- "연봉 1억 이상" vs "돈은 중요하지 않아요" → 중립 (0.0)
- "높은 연봉" vs "돈보다 사람이 중요" → 중립 (0.0)
- "안정적인 직장" vs "도전적인 삶" → 중립 (0.0)

결과는 JSON 형식으로 반환하세요:
{
    "relationship": "entailment|neutral|contradiction",
    "contradiction_score": 0.0에서 1.0 사이 (1.0이 완전 모순),
    "confidence": 0.0에서 1.0 사이,
    "reasoning": "한국어로 분석 이유 설명"
}"""

            user_prompt = f"""다음 두 진술의 논리적 일관성을 분석하세요:

진술 A ({source_a}): "{statement_a}"

진술 B ({source_b}): "{statement_b}"

두 진술이 모순되는지, 중립적인지, 서로 지지하는지 분석해주세요."""

            response = await azure_openai_service.client.chat.completions.create(
                model=azure_openai_service.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=500
            )

            content = response.choices[0].message.content

            # Parse JSON response
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result_data = json.loads(content)

            return ContradictionResult(
                source_a=source_a,
                statement_a=statement_a,
                source_b=source_b,
                statement_b=statement_b,
                relationship=result_data.get('relationship', 'neutral'),
                contradiction_score=result_data.get('contradiction_score', 0.0),
                confidence=result_data.get('confidence', 0.5),
                reasoning=result_data.get('reasoning', '')
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse NLI response: {e}")
            return None
        except Exception as e:
            logger.error(f"Contradiction detection failed: {e}")
            return None

    async def _store_consistency_results(
        self,
        user_id: str,
        contradictions: List[ContradictionResult]
    ):
        """Store consistency check results in database"""
        try:
            for contradiction in contradictions:
                self.supabase.table('consistency_checks').insert({
                    'user_id': user_id,
                    'check_type': 'nli_analysis',
                    'source_a': contradiction.source_a,
                    'statement_a': contradiction.statement_a,
                    'source_b': contradiction.source_b,
                    'statement_b': contradiction.statement_b,
                    'relationship': contradiction.relationship,
                    'contradiction_score': contradiction.contradiction_score,
                    'confidence_score': contradiction.confidence,
                    'ai_reasoning': contradiction.reasoning,
                    'ai_model_used': 'gpt-4o-mini'
                }).execute()

        except Exception as e:
            logger.error(f"Failed to store consistency results: {e}")

    async def get_unresolved_contradictions(self, user_id: str) -> List[Dict]:
        """Get list of unresolved contradictions for a user"""
        try:
            result = self.supabase.table('consistency_checks').select(
                '*'
            ).eq('user_id', user_id).eq('is_resolved', False).order(
                'contradiction_score', desc=True
            ).execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Failed to get unresolved contradictions: {e}")
            return []

    async def resolve_contradiction(
        self,
        contradiction_id: str,
        resolution_notes: str
    ) -> bool:
        """Mark a contradiction as resolved with notes"""
        try:
            self.supabase.table('consistency_checks').update({
                'is_resolved': True,
                'resolution_notes': resolution_notes,
                'resolved_at': datetime.now().isoformat()
            }).eq('id', contradiction_id).execute()

            return True

        except Exception as e:
            logger.error(f"Failed to resolve contradiction: {e}")
            return False

    async def get_consistency_score(self, user_id: str) -> float:
        """
        Get current consistency score for a user
        Returns 1.0 if no issues, lower if contradictions exist
        """
        try:
            result = self.supabase.table('consistency_checks').select(
                'contradiction_score'
            ).eq('user_id', user_id).eq('is_resolved', False).execute()

            if not result.data:
                return 1.0

            scores = [r['contradiction_score'] for r in result.data if r.get('contradiction_score')]

            if not scores:
                return 1.0

            avg_score = sum(scores) / len(scores)
            count_penalty = min(0.05 * len(scores), 0.2)

            return max(0.0, 1.0 - avg_score - count_penalty)

        except Exception as e:
            logger.error(f"Failed to get consistency score: {e}")
            return 1.0


# Singleton instance
nli_consistency_service = NLIConsistencyService()
