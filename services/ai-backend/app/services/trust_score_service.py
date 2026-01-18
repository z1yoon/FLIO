"""
FLIO Trust Score Service
Korean Marriage Agency Style (결혼정보회사)

Calculates user trustworthiness based on:
1. Document verification (OCR match)
2. Logical consistency (NLI)
3. Behavioral stability
4. Profile completeness

Trust by System, Not by People.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
from enum import Enum

from ..models.database import get_supabase_client

logger = logging.getLogger(__name__)


class TrustTier(str, Enum):
    """Trust tiers for Korean marriage agency style ranking"""
    PLATINUM = "platinum"  # VIP회원 - 0.90+
    GOLD = "gold"          # 우수회원 - 0.75-0.89
    SILVER = "silver"      # 인증회원 - 0.60-0.74
    BRONZE = "bronze"      # 기본회원 - 0.40-0.59
    UNVERIFIED = "unverified"  # 미인증 - 0.00-0.39


class TrustScoreResponse(BaseModel):
    """Trust score calculation result"""
    user_id: str
    document_score: float
    consistency_score: float
    behavioral_score: float
    completeness_score: float
    total_trust_score: float
    trust_tier: str
    calculation_details: Dict[str, Any]
    last_calculated_at: datetime


class TrustSummary(BaseModel):
    """Simplified trust summary for API responses"""
    trust_score: float
    trust_tier: str
    verified_items: List[str]
    profile_completeness: float
    is_matching_enabled: bool


class TrustScoreService:
    """
    Service to calculate and manage user trust scores
    Implements Korean marriage agency (결혼정보회사) style credibility system
    """

    # Trust Score Component Weights
    WEIGHTS = {
        'document': 0.35,      # Document verification (가장 중요)
        'consistency': 0.25,   # NLI logical consistency
        'behavioral': 0.20,    # Edit patterns, stability
        'completeness': 0.20   # Profile completeness
    }

    # Trust Tier Thresholds
    TIER_THRESHOLDS = {
        TrustTier.PLATINUM: 0.90,
        TrustTier.GOLD: 0.75,
        TrustTier.SILVER: 0.60,
        TrustTier.BRONZE: 0.40,
        TrustTier.UNVERIFIED: 0.0
    }

    # Tier Benefits
    TIER_BENEFITS = {
        TrustTier.PLATINUM: {
            'daily_matches': -1,  # Unlimited
            'can_see_tiers': ['gold', 'platinum'],
            'badge': 'VIP회원',
            'priority_matching': True
        },
        TrustTier.GOLD: {
            'daily_matches': 20,
            'can_see_tiers': ['silver', 'gold', 'platinum'],
            'badge': '우수회원',
            'priority_matching': True
        },
        TrustTier.SILVER: {
            'daily_matches': 10,
            'can_see_tiers': ['bronze', 'silver', 'gold', 'platinum'],
            'badge': '인증회원',
            'priority_matching': False
        },
        TrustTier.BRONZE: {
            'daily_matches': 5,
            'can_see_tiers': ['unverified', 'bronze', 'silver', 'gold', 'platinum'],
            'badge': '기본회원',
            'priority_matching': False
        },
        TrustTier.UNVERIFIED: {
            'daily_matches': 0,
            'can_see_tiers': [],
            'badge': '미인증',
            'priority_matching': False
        }
    }

    # Required documents for full verification
    DOCUMENT_TYPES = ['id_card', 'diploma', 'income_cert', 'employment_cert']

    # Total questions count
    TOTAL_QUESTIONS = 44

    def __init__(self):
        self.supabase = get_supabase_client()

    async def calculate_trust_score(self, user_id: str) -> TrustScoreResponse:
        """
        Calculate comprehensive trust score for a user
        Uses database RPC function for atomic calculation

        Returns:
            TrustScoreResponse with all component scores and tier
        """
        try:
            logger.info(f"Calculating trust score for user {user_id}")

            # Use database RPC function for atomic calculation
            result = self.supabase.rpc('calculate_trust_score', {
                'p_user_id': user_id
            }).execute()

            if result.data:
                data = result.data
                return TrustScoreResponse(
                    user_id=user_id,
                    document_score=data.get('document_score', 0.0),
                    consistency_score=data.get('consistency_score', 1.0),
                    behavioral_score=data.get('behavioral_score', 1.0),
                    completeness_score=data.get('completeness_score', 0.0),
                    total_trust_score=data.get('total_score', 0.0),
                    trust_tier=data.get('trust_tier', 'unverified'),
                    calculation_details=data,
                    last_calculated_at=datetime.fromisoformat(
                        data.get('calculated_at', datetime.now().isoformat()).replace('Z', '+00:00')
                    )
                )

            # Fallback to manual calculation if RPC fails
            return await self._calculate_trust_score_manual(user_id)

        except Exception as e:
            logger.error(f"Failed to calculate trust score for user {user_id}: {e}")
            # Return default scores on error
            return TrustScoreResponse(
                user_id=user_id,
                document_score=0.0,
                consistency_score=1.0,
                behavioral_score=1.0,
                completeness_score=0.0,
                total_trust_score=0.0,
                trust_tier='unverified',
                calculation_details={'error': str(e)},
                last_calculated_at=datetime.now()
            )

    async def _calculate_trust_score_manual(self, user_id: str) -> TrustScoreResponse:
        """
        Manual trust score calculation (fallback)
        Used when database RPC is not available
        """
        try:
            # 1. Calculate Document Score
            doc_score = await self._calculate_document_score(user_id)

            # 2. Calculate Consistency Score
            consistency_score = await self._calculate_consistency_score(user_id)

            # 3. Calculate Behavioral Score
            behavioral_score = await self._calculate_behavioral_score(user_id)

            # 4. Calculate Completeness Score
            completeness_score = await self._calculate_completeness_score(user_id)

            # 5. Calculate weighted total
            total_score = (
                doc_score * self.WEIGHTS['document'] +
                consistency_score * self.WEIGHTS['consistency'] +
                behavioral_score * self.WEIGHTS['behavioral'] +
                completeness_score * self.WEIGHTS['completeness']
            )

            # Clamp to 0-1
            total_score = max(0.0, min(1.0, total_score))

            # 6. Determine tier
            trust_tier = self._determine_tier(total_score)

            # 7. Store results
            await self._store_trust_score(
                user_id, doc_score, consistency_score,
                behavioral_score, completeness_score,
                total_score, trust_tier
            )

            return TrustScoreResponse(
                user_id=user_id,
                document_score=doc_score,
                consistency_score=consistency_score,
                behavioral_score=behavioral_score,
                completeness_score=completeness_score,
                total_trust_score=total_score,
                trust_tier=trust_tier,
                calculation_details={
                    'weights': self.WEIGHTS,
                    'method': 'manual'
                },
                last_calculated_at=datetime.now()
            )

        except Exception as e:
            logger.error(f"Manual trust score calculation failed: {e}")
            raise

    async def _calculate_document_score(self, user_id: str) -> float:
        """
        Calculate document verification score

        Score components:
        - Each verified document contributes equally
        - Combined score: (match_score * 0.7) + (authenticity_score * 0.3)
        - Only documents with authenticity_score >= 0.5 are included
        """
        try:
            result = self.supabase.table('user_documents').select(
                'document_type, match_score, authenticity_score, verification_status'
            ).eq('user_id', user_id).execute()

            if not result.data:
                return 0.0

            # Calculate score based on verified documents with valid authenticity
            verified_docs = [
                doc for doc in result.data
                if doc['verification_status'] == 'verified'
                and (doc.get('authenticity_score') is None or doc.get('authenticity_score', 0.0) >= 0.5)
            ]

            if not verified_docs:
                return 0.0

            # Weight by document type importance
            doc_weights = {
                'id_card': 0.30,
                'diploma': 0.25,
                'income_cert': 0.25,
                'employment_cert': 0.20
            }

            total_score = 0.0
            total_weight = 0.0

            for doc in verified_docs:
                doc_type = doc['document_type']
                match_score = doc.get('match_score', 0.0) or 0.0
                authenticity_score = doc.get('authenticity_score', 1.0) or 1.0
                
                # Combine match and authenticity scores
                # Weight: 70% match, 30% authenticity
                combined_score = (match_score * 0.7) + (authenticity_score * 0.3)
                
                weight = doc_weights.get(doc_type, 0.1)

                total_score += combined_score * weight
                total_weight += weight

            # Normalize by total possible weight (if partial verification)
            # Also give bonus for having more documents verified
            coverage_bonus = len(verified_docs) / len(self.DOCUMENT_TYPES) * 0.2

            final_score = (total_score / total_weight if total_weight > 0 else 0.0) + coverage_bonus

            return min(1.0, final_score)

        except Exception as e:
            logger.error(f"Document score calculation failed: {e}")
            return 0.0

    async def _calculate_consistency_score(self, user_id: str) -> float:
        """
        Calculate logical consistency score based on NLI checks

        Score = 1.0 - average(contradiction_scores)
        Unresolved contradictions decrease trust
        """
        try:
            result = self.supabase.table('consistency_checks').select(
                'contradiction_score, is_resolved'
            ).eq('user_id', user_id).eq('is_resolved', False).execute()

            if not result.data:
                return 1.0  # Perfect consistency if no issues found

            # Calculate average contradiction score
            contradiction_scores = [
                check['contradiction_score']
                for check in result.data
                if check['contradiction_score'] is not None
            ]

            if not contradiction_scores:
                return 1.0

            avg_contradiction = sum(contradiction_scores) / len(contradiction_scores)

            # Penalize for number of contradictions too
            count_penalty = min(0.1 * len(contradiction_scores), 0.3)

            consistency_score = 1.0 - avg_contradiction - count_penalty

            return max(0.0, consistency_score)

        except Exception as e:
            logger.error(f"Consistency score calculation failed: {e}")
            return 1.0  # Default to no issues on error

    async def _calculate_behavioral_score(self, user_id: str) -> float:
        """
        Calculate behavioral trust score based on user actions

        Negative signals:
        - Frequent critical field changes
        - Suspicious edit patterns
        - Multiple high-risk events

        Positive signals:
        - Account age
        - Stable profile
        """
        try:
            # Get recent behavior logs (last 30 days)
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()

            result = self.supabase.table('user_behavior_logs').select(
                'event_type, risk_level, created_at'
            ).eq('user_id', user_id).gte('created_at', thirty_days_ago).execute()

            if not result.data:
                return 1.0  # No negative behavior recorded

            # Calculate risk penalties
            risk_penalties = {
                'critical': 0.25,
                'high': 0.15,
                'medium': 0.05,
                'low': 0.01
            }

            total_penalty = 0.0

            for log in result.data:
                risk_level = log.get('risk_level', 'low')
                penalty = risk_penalties.get(risk_level, 0.01)
                total_penalty += penalty

            # Cap total penalty at 0.8 (minimum score of 0.2)
            total_penalty = min(total_penalty, 0.8)

            # Get account age bonus
            profile_result = self.supabase.table('profiles').select(
                'created_at'
            ).eq('user_id', user_id).single().execute()

            age_bonus = 0.0
            if profile_result.data:
                created_at = datetime.fromisoformat(
                    profile_result.data['created_at'].replace('Z', '+00:00')
                )
                account_age_days = (datetime.now(created_at.tzinfo) - created_at).days

                if account_age_days >= 180:
                    age_bonus = 0.10
                elif account_age_days >= 90:
                    age_bonus = 0.05
                elif account_age_days >= 30:
                    age_bonus = 0.02

            behavioral_score = 1.0 - total_penalty + age_bonus

            return max(0.0, min(1.0, behavioral_score))

        except Exception as e:
            logger.error(f"Behavioral score calculation failed: {e}")
            return 1.0

    async def _calculate_completeness_score(self, user_id: str) -> float:
        """
        Calculate profile completeness score

        Components:
        - Basic profile fields (30%)
        - Questions answered (40%)
        - Family background (15%)
        - Documents uploaded (15%)
        """
        try:
            score = 0.0

            # 1. Profile fields (30%)
            profile_result = self.supabase.table('profiles').select(
                'real_name, height_cm, weight_kg, education_level, '
                'university_name, employment_status, company_name, '
                'job_title, annual_income_range, marital_status'
            ).eq('user_id', user_id).single().execute()

            if profile_result.data:
                profile = profile_result.data
                required_fields = [
                    'real_name', 'height_cm', 'education_level',
                    'employment_status', 'annual_income_range', 'marital_status'
                ]
                optional_fields = [
                    'weight_kg', 'university_name', 'company_name', 'job_title'
                ]

                # Required fields worth 20%
                filled_required = sum(
                    1 for field in required_fields
                    if profile.get(field) is not None
                )
                score += (filled_required / len(required_fields)) * 0.20

                # Optional fields worth 10%
                filled_optional = sum(
                    1 for field in optional_fields
                    if profile.get(field) is not None
                )
                score += (filled_optional / len(optional_fields)) * 0.10

            # 2. Questions answered (40%)
            answers_result = self.supabase.table('user_answers').select(
                'question_id', count='exact'
            ).eq('user_id', user_id).execute()

            if answers_result.count:
                questions_score = min(answers_result.count / self.TOTAL_QUESTIONS, 1.0)
                score += questions_score * 0.40

            # 3. Family background (15%)
            family_result = self.supabase.table('user_family_background').select(
                'father_occupation, mother_occupation, parents_status'
            ).eq('user_id', user_id).execute()

            if family_result.data:
                family = family_result.data[0] if family_result.data else {}
                family_fields = ['father_occupation', 'mother_occupation', 'parents_status']
                filled_family = sum(
                    1 for field in family_fields
                    if family.get(field) is not None
                )
                score += (filled_family / len(family_fields)) * 0.15

            # 4. Documents uploaded (15%)
            docs_result = self.supabase.table('user_documents').select(
                'document_type', count='exact'
            ).eq('user_id', user_id).execute()

            if docs_result.count:
                docs_score = min(docs_result.count / len(self.DOCUMENT_TYPES), 1.0)
                score += docs_score * 0.15

            return min(1.0, score)

        except Exception as e:
            logger.error(f"Completeness score calculation failed: {e}")
            return 0.0

    def _determine_tier(self, total_score: float) -> str:
        """Determine trust tier based on total score"""
        for tier, threshold in self.TIER_THRESHOLDS.items():
            if total_score >= threshold:
                return tier.value
        return TrustTier.UNVERIFIED.value

    async def _store_trust_score(
        self,
        user_id: str,
        doc_score: float,
        consistency_score: float,
        behavioral_score: float,
        completeness_score: float,
        total_score: float,
        trust_tier: str
    ):
        """Store calculated trust score in database"""
        try:
            self.supabase.table('user_trust_scores').upsert({
                'user_id': user_id,
                'document_score': doc_score,
                'consistency_score': consistency_score,
                'behavioral_score': behavioral_score,
                'completeness_score': completeness_score,
                'total_trust_score': total_score,
                'trust_tier': trust_tier,
                'weights_used': self.WEIGHTS,
                'calculation_details': {
                    'method': 'manual',
                    'calculated_at': datetime.now().isoformat()
                },
                'last_calculated_at': datetime.now().isoformat()
            }).execute()

            # Also update profile
            self.supabase.table('profiles').update({
                'trust_tier': trust_tier
            }).eq('user_id', user_id).execute()

        except Exception as e:
            logger.error(f"Failed to store trust score: {e}")

    async def get_trust_score(self, user_id: str) -> Optional[TrustScoreResponse]:
        """
        Get existing trust score for a user
        Returns None if not calculated yet
        """
        try:
            result = self.supabase.table('user_trust_scores').select(
                '*'
            ).eq('user_id', user_id).single().execute()

            if result.data:
                data = result.data
                return TrustScoreResponse(
                    user_id=user_id,
                    document_score=data['document_score'],
                    consistency_score=data['consistency_score'],
                    behavioral_score=data['behavioral_score'],
                    completeness_score=data['completeness_score'],
                    total_trust_score=data['total_trust_score'],
                    trust_tier=data['trust_tier'],
                    calculation_details=data.get('calculation_details', {}),
                    last_calculated_at=datetime.fromisoformat(
                        data['last_calculated_at'].replace('Z', '+00:00')
                    )
                )

            return None

        except Exception as e:
            logger.error(f"Failed to get trust score for user {user_id}: {e}")
            return None

    async def get_trust_summary(self, user_id: str) -> TrustSummary:
        """
        Get simplified trust summary for API responses
        """
        try:
            # Use RPC function
            result = self.supabase.rpc('get_user_trust_summary', {
                'p_user_id': user_id
            }).execute()

            if result.data:
                data = result.data
                verification_status = data.get('verification_status', {})

                verified_items = []
                if verification_status.get('id_verified'):
                    verified_items.append('신분증')
                if verification_status.get('education_verified'):
                    verified_items.append('학력')
                if verification_status.get('income_verified'):
                    verified_items.append('소득')
                if verification_status.get('employment_verified'):
                    verified_items.append('재직')
                if verification_status.get('phone_verified'):
                    verified_items.append('전화번호')

                trust_tier = data.get('trust_tier', 'unverified')

                return TrustSummary(
                    trust_score=data.get('trust_score', 0),
                    trust_tier=trust_tier,
                    verified_items=verified_items,
                    profile_completeness=data.get('component_scores', {}).get('completeness', 0),
                    is_matching_enabled=trust_tier != 'unverified'
                )

            # Default response
            return TrustSummary(
                trust_score=0,
                trust_tier='unverified',
                verified_items=[],
                profile_completeness=0,
                is_matching_enabled=False
            )

        except Exception as e:
            logger.error(f"Failed to get trust summary: {e}")
            return TrustSummary(
                trust_score=0,
                trust_tier='unverified',
                verified_items=[],
                profile_completeness=0,
                is_matching_enabled=False
            )

    async def get_tier_benefits(self, trust_tier: str) -> Dict[str, Any]:
        """
        Get benefits associated with a trust tier
        """
        tier = TrustTier(trust_tier) if trust_tier in [t.value for t in TrustTier] else TrustTier.UNVERIFIED
        return self.TIER_BENEFITS.get(tier, self.TIER_BENEFITS[TrustTier.UNVERIFIED])

    async def get_minimum_tier_for_matching(self, user_tier: str) -> List[str]:
        """
        Get minimum tiers that a user can see in matches
        Higher tier users see only similar or higher tier profiles
        """
        tier_order = ['unverified', 'bronze', 'silver', 'gold', 'platinum']

        benefits = await self.get_tier_benefits(user_tier)
        return benefits.get('can_see_tiers', [])

    async def log_behavior(
        self,
        user_id: str,
        event_type: str,
        event_data: Dict = None,
        field_changed: str = None,
        old_value: str = None,
        new_value: str = None
    ) -> Optional[str]:
        """
        Log user behavior for trust scoring
        Uses database RPC function
        """
        try:
            result = self.supabase.rpc('log_user_behavior', {
                'p_user_id': user_id,
                'p_event_type': event_type,
                'p_event_data': event_data or {},
                'p_field_changed': field_changed,
                'p_old_value': old_value,
                'p_new_value': new_value
            }).execute()

            return result.data if result.data else None

        except Exception as e:
            logger.error(f"Failed to log behavior: {e}")
            return None

    async def recalculate_all_trust_scores(self) -> int:
        """
        Recalculate trust scores for all users
        Used for batch updates or maintenance

        Returns:
            Number of users processed
        """
        try:
            # Get all user IDs
            result = self.supabase.table('profiles').select('user_id').execute()

            if not result.data:
                return 0

            count = 0
            for profile in result.data:
                user_id = profile['user_id']
                try:
                    await self.calculate_trust_score(user_id)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to recalculate trust for {user_id}: {e}")

            logger.info(f"Recalculated trust scores for {count} users")
            return count

        except Exception as e:
            logger.error(f"Batch trust recalculation failed: {e}")
            return 0


# Singleton instance
trust_score_service = TrustScoreService()
