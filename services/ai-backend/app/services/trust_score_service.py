"""
FLIO Trust Score Service
Korean Marriage Agency Style (결혼정보회사)

Simple verification checklist — 1 document = 1 tier upgrade:
  신분증   (id_card)        20 pts → verifies 이름, 나이
  건강검진서 (health_checkup) 20 pts → verifies 키, 몸무게
  졸업증명서 (diploma)       20 pts → verifies 학교
  재직증명서 (employment_cert) 20 pts → verifies 회사
  소득증명서 (income_proof)  20 pts → verifies 연봉

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
    total_trust_score: float          # 0.0–1.0
    trust_tier: str
    trust_points: int                 # 0–100 raw points
    verified_documents: List[str]     # which docs are verified
    field_verifications: Dict[str, bool]  # field-level 인증됨 flags
    reputation_penalty: int           # confirmed reports × 5
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

    # Each document type, its point value, and the profile fields it verifies
    DOCUMENT_CONFIG: Dict[str, Dict] = {
        'id_card': {
            'points': 20,
            'label': '신분증',
            'verifies': ['real_name', 'age'],
        },
        'health_checkup': {
            'points': 20,
            'label': '건강검진서',
            'verifies': ['height_cm', 'weight_kg'],
        },
        'diploma': {
            'points': 20,
            'label': '졸업증명서',
            'verifies': ['university_name', 'education_level'],
        },
        'employment_cert': {
            'points': 20,
            'label': '재직증명서',
            'verifies': ['company_name', 'job_title'],
        },
        'income_proof': {
            'points': 20,
            'label': '소득증명서',
            'verifies': ['annual_income_range'],
        },
    }

    # Points deducted per confirmed 신고
    REPORT_PENALTY = 5

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
        Subtracts REPORT_PENALTY for each confirmed 신고.
        """
        logger.info(f"Calculating trust score for user {user_id}")

        verified_docs = self._get_verified_documents(user_id)
        reputation_penalty = self._get_reputation_penalty(user_id)

        raw_points = sum(
            self.DOCUMENT_CONFIG[doc]['points']
            for doc in verified_docs
            if doc in self.DOCUMENT_CONFIG
        )
        points = max(0, raw_points - reputation_penalty)

        trust_tier = self._determine_tier(points)
        trust_score = round(points / 100, 2)

        field_verifications = self._build_field_verifications(verified_docs)

        result = TrustScoreResponse(
            user_id=user_id,
            total_trust_score=trust_score,
            trust_tier=trust_tier,
            trust_points=points,
            verified_documents=verified_docs,
            field_verifications=field_verifications,
            reputation_penalty=reputation_penalty,
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
            return TrustScoreResponse(
                user_id=user_id,
                total_trust_score=data.get('total_trust_score', 0.0),
                trust_tier=data.get('trust_tier', 'pebble'),
                trust_points=int((data.get('total_trust_score', 0.0)) * 100),
                verified_documents=data.get('verified_documents', []),
                field_verifications=data.get('field_verifications', {}),
                reputation_penalty=data.get('reputation_penalty', 0),
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
