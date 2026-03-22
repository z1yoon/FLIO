"""
FLIO Trust Score Service
Korean Marriage Agency Style (결혼정보회사)

6 document categories — points sum to 100 (다이아 = 6개 전부 인증):
  id_card: 20 pts (첫 인증 시 바로 등급 상승 체감)
  나머지 5종 각 16 pts → 20 + 16×5 = 100

Reputation penalty: -5 pts per confirmed 신고
Total stored as 0.0–1.0 (pts / 100)
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

from ..models.database import get_supabase_client

logger = logging.getLogger(__name__)


class TrustTier(str, Enum):
    """Trust tiers — Ocean Pearl Theme"""
    DIAMOND = "diamond"  # 다이아  80–100 pts
    CORAL   = "coral"    # 산호    60–79 pts
    PEARL   = "pearl"    # 진주    40–59 pts
    SHELL   = "shell"    # 조개    20–39 pts
    PEBBLE  = "pebble"   # 조약돌   0–19 pts


class TrustScoreResponse(BaseModel):
    user_id: str
    total_trust_score: float
    trust_tier: str
    trust_points: int                 # 0–100 (6 docs, see DOCUMENT_CONFIG points)
    verified_documents: List[str]
    field_verifications: Dict[str, bool]
    reputation_penalty: int
    nli_penalty: int
    nli_contradictions: List[Dict]
    is_matching_blocked: bool
    last_calculated_at: datetime


class TrustSummary(BaseModel):
    trust_score: float
    trust_tier: str
    verified_items: List[str]
    profile_completeness: float
    is_matching_enabled: bool


class TrustScoreService:
    """
    Calculates trust score by summing verification document points.
    One verified document = one tier upgrade.
    """

    # 6 categories × points = 100 max (20 + 16×5)
    DOCUMENT_CONFIG: Dict[str, Dict] = {
        'id_card': {
            'points': 20,
            'label': '신분증',
            'label_detail': '주민등록증, 운전면허증, 여권',
            'issue_from': '본인 소지 서류',
            'verifies': ['real_name', 'age'],
            'verifies_label': '이름, 나이',
            'icon': '🪪',
        },
        'health_checkup': {
            'points': 16,
            'label': '건강검진서',
            'label_detail': '국민건강보험공단 건강검진 결과지',
            'issue_from': '국민건강보험공단 (건강iN)',
            'verifies': ['height_cm', 'weight_kg'],
            'verifies_label': '키, 몸무게',
            'icon': '🏥',
        },
        'diploma': {
            'points': 16,
            'label': '졸업증명서',
            'label_detail': '대학교 졸업증명서 또는 학위증명서',
            'issue_from': '대학교 학생처 또는 정부24',
            'verifies': ['university_name', 'education_level'],
            'verifies_label': '학교, 학력',
            'icon': '🎓',
        },
        'employment_cert': {
            'points': 16,
            'label': '재직증명서',
            'label_detail': '회사 발급 재직증명서',
            'issue_from': '재직 중인 회사 HR/인사팀',
            'verifies': ['company_name', 'job_title'],
            'verifies_label': '회사, 직책',
            'icon': '💼',
        },
        'income_proof': {
            'points': 16,
            'label': '소득증명서',
            'label_detail': '소득금액증명원 (국세청)',
            'issue_from': '홈택스 또는 정부24 (무료)',
            'verifies': ['annual_income_range'],
            'verifies_label': '연봉',
            'icon': '💰',
        },
        'criminal_check': {
            'points': 16,
            'label': '범죄이력조회서',
            'label_detail': '범죄·수사 경력 회보서 등',
            'issue_from': '경찰청 범죄경력조회 또는 정부24 (무료)',
            'verifies': ['criminal_record_clear'],
            'verifies_label': '범죄 이력 없음',
            'icon': '🛡️',
        },
    }

    # Points deducted per confirmed 신고
    REPORT_PENALTY = 5

    # Points deducted per unresolved high-confidence NLI contradiction (score >= 0.7)
    NLI_CONTRADICTION_PENALTY = 5
    NLI_PENALTY_CAP = 20  # max 4 contradictions' worth (-20 pts)

    # Tier thresholds (in raw points 0–100)
    TIER_THRESHOLDS = {
        TrustTier.DIAMOND: 80,
        TrustTier.CORAL:   60,
        TrustTier.PEARL:   40,
        TrustTier.SHELL:   20,
        TrustTier.PEBBLE:  0,
    }

    # Tier benefits
    TIER_BENEFITS = {
        TrustTier.DIAMOND: {
            'daily_matches': 15,
            'daily_reshuffles': 5,
            'can_see_tiers': ['diamond', 'coral', 'pearl', 'shell', 'pebble'],
            'badge': '다이아',
            'priority_matching': True,
        },
        TrustTier.CORAL: {
            'daily_matches': 10,
            'daily_reshuffles': 4,
            'can_see_tiers': ['coral', 'pearl', 'shell', 'pebble'],
            'badge': '산호',
            'priority_matching': True,
        },
        TrustTier.PEARL: {
            'daily_matches': 7,
            'daily_reshuffles': 3,
            'can_see_tiers': ['pearl', 'shell', 'pebble'],
            'badge': '진주',
            'priority_matching': False,
        },
        TrustTier.SHELL: {
            'daily_matches': 5,
            'daily_reshuffles': 2,
            'can_see_tiers': ['shell', 'pebble'],
            'badge': '조개',
            'priority_matching': False,
        },
        TrustTier.PEBBLE: {
            'daily_matches': 3,
            'daily_reshuffles': 1,
            'can_see_tiers': ['pebble'],
            'badge': '조약돌',
            'priority_matching': False,
        },
    }

    def __init__(self):
        self.supabase = get_supabase_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def calculate_trust_score(self, user_id: str) -> TrustScoreResponse:
        """
        Calculate trust score by summing verified document points.
        Deducts REPORT_PENALTY per confirmed 신고.
        Deducts NLI_CONTRADICTION_PENALTY per unresolved NLI contradiction (score >= 0.7).
        Blocks matching if 2+ contradictions have score >= 0.8.
        """
        logger.info(f"Calculating trust score for user {user_id}")

        verified_docs = self._get_verified_documents(user_id)
        reputation_penalty = self._get_reputation_penalty(user_id)
        nli_penalty, nli_contradictions = self._get_nli_penalty(user_id)

        raw_points = min(100, sum(
            self.DOCUMENT_CONFIG[doc]['points']
            for doc in verified_docs
            if doc in self.DOCUMENT_CONFIG
        ))
        points = max(0, raw_points - reputation_penalty - nli_penalty)

        trust_tier = self._determine_tier(points)
        trust_score = round(points / 100, 2)
        field_verifications = self._build_field_verifications(verified_docs)
        severe = [c for c in nli_contradictions if c.get('contradiction_score', 0) >= 0.8]
        is_matching_blocked = len(severe) >= 2

        result = TrustScoreResponse(
            user_id=user_id,
            total_trust_score=trust_score,
            trust_tier=trust_tier,
            trust_points=points,
            verified_documents=verified_docs,
            field_verifications=field_verifications,
            reputation_penalty=reputation_penalty,
            nli_penalty=nli_penalty,
            nli_contradictions=nli_contradictions,
            is_matching_blocked=is_matching_blocked,
            last_calculated_at=datetime.now(),
        )

        self._store_trust_score(user_id, result)
        return result

    async def get_trust_score(self, user_id: str) -> Optional[TrustScoreResponse]:
        """
        Return cached trust score from DB, recalculate if missing.
        """
        result = self.supabase.table('user_trust_scores').select('*').eq(
            'user_id', user_id
        ).maybe_single().execute()

        if result.data:
            data = result.data
            pts = int((data.get('total_trust_score', 0.0)) * 100)
            return TrustScoreResponse(
                user_id=user_id,
                total_trust_score=data.get('total_trust_score', 0.0),
                trust_tier=data.get('trust_tier', 'pebble'),
                trust_points=pts,
                verified_documents=data.get('verified_documents', []),
                field_verifications=data.get('field_verifications', {}),
                reputation_penalty=data.get('reputation_penalty', 0),
                nli_penalty=data.get('nli_penalty', 0),
                nli_contradictions=data.get('nli_contradictions', []),
                is_matching_blocked=data.get('is_matching_blocked', False),
                last_calculated_at=datetime.fromisoformat(
                    data['last_calculated_at'].replace('Z', '+00:00')
                ) if data.get('last_calculated_at') else datetime.now(),
            )

        return await self.calculate_trust_score(user_id)

    def get_field_verification_map(self) -> Dict[str, Dict]:
        """
        Returns which document verifies each profile field.
        Used by the frontend to show "X로 인증하기" buttons.
        """
        field_map = {}
        for doc_type, config in self.DOCUMENT_CONFIG.items():
            for field in config['verifies']:
                field_map[field] = {
                    'document_type': doc_type,
                    'document_label': config['label'],
                    'points': config['points'],
                }
        return field_map

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_verified_documents(self, user_id: str) -> List[str]:
        result = self.supabase.table('user_documents').select(
            'document_type'
        ).eq('user_id', user_id).eq('verification_status', 'verified').execute()

        return [row['document_type'] for row in (result.data or [])]

    def _get_reputation_penalty(self, user_id: str) -> int:
        result = self.supabase.table('user_reports').select(
            'id', count='exact'
        ).eq('reported_user_id', user_id).eq('status', 'confirmed').execute()

        confirmed_reports = result.count or 0
        return confirmed_reports * self.REPORT_PENALTY

    def _get_nli_penalty(self, user_id: str):
        """
        Returns (penalty_points, contradiction_list).
        Only counts unresolved contradictions with score >= 0.7.
        Penalty capped at NLI_PENALTY_CAP.
        """
        result = self.supabase.table('consistency_checks').select(
            'id, source_a, source_b, statement_a, statement_b, '
            'contradiction_score, ai_reasoning'
        ).eq('user_id', user_id).eq('is_resolved', False).gte(
            'contradiction_score', 0.7
        ).order('contradiction_score', desc=True).execute()

        contradictions = result.data or []
        penalty = min(len(contradictions) * self.NLI_CONTRADICTION_PENALTY, self.NLI_PENALTY_CAP)
        return penalty, contradictions

    def _build_field_verifications(self, verified_docs: List[str]) -> Dict[str, bool]:
        verifications: Dict[str, bool] = {}
        for doc_type, config in self.DOCUMENT_CONFIG.items():
            is_verified = doc_type in verified_docs
            for field in config['verifies']:
                verifications[field] = is_verified
        return verifications

    def _determine_tier(self, points: int) -> str:
        for tier, threshold in self.TIER_THRESHOLDS.items():
            if points >= threshold:
                return tier.value
        return TrustTier.PEBBLE.value

    def _store_trust_score(self, user_id: str, result: TrustScoreResponse) -> None:
        self.supabase.table('user_trust_scores').upsert({
            'user_id': user_id,
            'total_trust_score': result.total_trust_score,
            'trust_tier': result.trust_tier,
            'verified_documents': result.verified_documents,
            'field_verifications': result.field_verifications,
            'reputation_penalty': result.reputation_penalty,
            'nli_penalty': result.nli_penalty,
            'nli_contradictions': result.nli_contradictions,
            'is_matching_blocked': result.is_matching_blocked,
            'last_calculated_at': result.last_calculated_at.isoformat(),
            'updated_at': datetime.now().isoformat(),
        }, on_conflict='user_id').execute()

    # ------------------------------------------------------------------
    # Compatibility helpers (used by matching router)
    # ------------------------------------------------------------------

    @staticmethod
    def get_tier_from_score(score: float) -> str:
        points = int(score * 100)
        if points >= 80: return TrustTier.DIAMOND.value
        if points >= 60: return TrustTier.CORAL.value
        if points >= 40: return TrustTier.PEARL.value
        if points >= 20: return TrustTier.SHELL.value
        return TrustTier.PEBBLE.value

    async def get_tier_benefits(self, tier: str) -> Dict:
        """Return benefits dict for the given tier string."""
        try:
            tier_enum = TrustTier(tier)
        except ValueError:
            tier_enum = TrustTier.PEBBLE
        return self.TIER_BENEFITS.get(tier_enum, self.TIER_BENEFITS[TrustTier.PEBBLE])


trust_score_service = TrustScoreService()
