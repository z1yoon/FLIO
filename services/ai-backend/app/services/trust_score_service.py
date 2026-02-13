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
    """Trust tiers - Ocean Pearl Theme"""
    DIAMOND = "diamond"  # 다이아 - 0.80+
    CORAL = "coral"      # 산호 - 0.60-0.79
    PEARL = "pearl"      # 진주 - 0.40-0.59
    SHELL = "shell"      # 조개 - 0.20-0.39
    PEBBLE = "pebble"    # 조약돌 - 0.00-0.19


class TrustScoreResponse(BaseModel):
    """Trust score calculation result - all 7 components"""
    user_id: str
    document_score: float
    photo_score: float
    consistency_score: float
    behavioral_score: float
    social_score: float
    completeness_score: float
    reputation_score: float
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

    # Trust Score Component Weights (7 components - matches database)
    WEIGHTS = {
        'document': 0.25,      # Document verification (신분증, 학력, 소득, 재직)
        'photo': 0.20,         # Photo verification (필수)
        'consistency': 0.15,   # NLI logical consistency
        'behavioral': 0.15,    # Edit patterns, stability
        'social': 0.10,        # Social verification (LinkedIn, Instagram, etc)
        'completeness': 0.10,  # Profile completeness
        'reputation': 0.05     # Reputation score (reports, feedback)
    }
    # Total: 100%

    # Trust Tier Thresholds
    TIER_THRESHOLDS = {
        TrustTier.DIAMOND: 0.80,
        TrustTier.CORAL: 0.60,
        TrustTier.PEARL: 0.40,
        TrustTier.SHELL: 0.20,
        TrustTier.PEBBLE: 0.0
    }

    # Tier Benefits
    TIER_BENEFITS = {
        TrustTier.DIAMOND: {
            'daily_matches': 30,
            'can_see_tiers': ['diamond', 'coral', 'pearl', 'shell', 'pebble'],
            'badge': '다이아',
            'priority_matching': True
        },
        TrustTier.CORAL: {
            'daily_matches': 20,
            'can_see_tiers': ['coral', 'pearl', 'shell', 'pebble'],
            'badge': '산호',
            'priority_matching': True
        },
        TrustTier.PEARL: {
            'daily_matches': 15,
            'can_see_tiers': ['pearl', 'shell', 'pebble'],
            'badge': '진주',
            'priority_matching': False
        },
        TrustTier.SHELL: {
            'daily_matches': 10,
            'can_see_tiers': ['shell', 'pebble'],
            'badge': '조개',
            'priority_matching': False
        },
        TrustTier.PEBBLE: {
            'daily_matches': 5,
            'can_see_tiers': ['pebble'],
            'badge': '조약돌',
            'priority_matching': False
        }
    }

    # Required documents for full verification
    DOCUMENT_TYPES = ['id_card', 'diploma', 'income_cert', 'employment_cert']

    # Dynamic question count (cached for 5 minutes)
    _question_count_cache = None
    _cache_time = None
    CACHE_DURATION = 300  # 5 minutes

    def __init__(self):
        self.supabase = get_supabase_client()

    def get_total_questions(self) -> int:
        """Get total question count from database (cached for 5 minutes)"""
        from datetime import datetime, timedelta

        now = datetime.now()

        # Return cached value if still valid
        if (TrustScoreService._question_count_cache is not None and
            TrustScoreService._cache_time is not None and
            now - TrustScoreService._cache_time < timedelta(seconds=self.CACHE_DURATION)):
            return TrustScoreService._question_count_cache

        # Fetch from database
        result = self.supabase.table('system_settings').select('value').eq(
            'key', 'active_question_count'
        ).execute()

        if result.data and len(result.data) > 0:
            count = result.data[0]['value']['count']
            TrustScoreService._question_count_cache = count
            TrustScoreService._cache_time = now
            return count

        # Fallback: count directly from questions table
        result = self.supabase.table('questions').select('id', count='exact').execute()
        count = result.count if result.count else 40
        TrustScoreService._question_count_cache = count
        TrustScoreService._cache_time = now
        return count

    async def calculate_trust_score(self, user_id: str) -> TrustScoreResponse:
        """
        Calculate comprehensive trust score for a user
        Uses database RPC function for atomic calculation

        Returns:
            TrustScoreResponse with all 7 component scores and tier

        Raises:
            Exception if calculation fails - no fallback logic
        """
        logger.info(f"Calculating trust score for user {user_id}")

        # Use database RPC function for atomic calculation
        result = self.supabase.rpc('calculate_trust_score', {
            'p_user_id': user_id
        }).execute()

        # No fallback - will raise if data is missing
        data = result.data

        return TrustScoreResponse(
            user_id=user_id,
            document_score=data['document_score'],
            photo_score=data.get('photo_score', 0.0),
            consistency_score=data['consistency_score'],
            behavioral_score=data['behavioral_score'],
            social_score=data.get('social_score', 0.0),
            completeness_score=data['completeness_score'],
            reputation_score=data.get('reputation_score', 1.0),
            total_trust_score=data['total_score'],
            trust_tier=data['trust_tier'],
            calculation_details=data,
            last_calculated_at=datetime.fromisoformat(
                data['calculated_at'].replace('Z', '+00:00')
            )
        )

    async def _calculate_trust_score_manual(self, user_id: str) -> TrustScoreResponse:
        """
        Manual trust score calculation - matches database function calculate_trust_score()

        All 7 components fully implemented:
        1. Document (25%)
        2. Photo (20%)
        3. Consistency (15%)
        4. Behavioral (15%)
        5. Social (10%)
        6. Completeness (10%)
        7. Reputation (5%)
        """
        # Calculate all 7 components
        doc_score = await self._calculate_document_score(user_id)
        photo_score = await self._calculate_photo_score(user_id)
        consistency_score = await self._calculate_consistency_score(user_id)
        behavioral_score = await self._calculate_behavioral_score(user_id)
        social_score = await self._calculate_social_score(user_id)
        completeness_score = await self._calculate_completeness_score(user_id)
        reputation_score = await self._calculate_reputation_score(user_id)

        # Calculate weighted total (7 components matching database weights)
        total_score = (
            doc_score * self.WEIGHTS['document'] +
            photo_score * self.WEIGHTS['photo'] +
            consistency_score * self.WEIGHTS['consistency'] +
            behavioral_score * self.WEIGHTS['behavioral'] +
            social_score * self.WEIGHTS['social'] +
            completeness_score * self.WEIGHTS['completeness'] +
            reputation_score * self.WEIGHTS['reputation']
        )

        # Clamp to 0-1
        total_score = max(0.0, min(1.0, total_score))

        # Determine tier
        trust_tier = self._determine_tier(total_score)

        # Store results (all 7 components)
        await self._store_trust_score(
            user_id, doc_score, photo_score, consistency_score,
            behavioral_score, social_score, completeness_score,
            reputation_score, total_score, trust_tier
        )

        return TrustScoreResponse(
            user_id=user_id,
            document_score=doc_score,
            photo_score=photo_score,
            consistency_score=consistency_score,
            behavioral_score=behavioral_score,
            social_score=social_score,
            completeness_score=completeness_score,
            reputation_score=reputation_score,
            total_trust_score=total_score,
            trust_tier=trust_tier,
            calculation_details={
                'weights': self.WEIGHTS,
                'method': 'manual'
            },
            last_calculated_at=datetime.now()
        )

    async def _calculate_document_score(self, user_id: str) -> float:
        """
        Calculate document verification score

        Matches database function calculate_trust_score():
        - Simple average of match_score for all verified documents
        - All document types are weighted equally
        """
        result = self.supabase.table('user_documents').select(
            'match_score, verification_status'
        ).eq('user_id', user_id).eq('verification_status', 'verified').execute()

        if not result.data:
            return 0.0

        # Simple average of match_scores (same as database: AVG(match_score))
        match_scores = [doc['match_score'] for doc in result.data if doc['match_score'] is not None]

        if not match_scores:
            return 0.0

        return sum(match_scores) / len(match_scores)

    async def _calculate_consistency_score(self, user_id: str) -> float:
        """
        Calculate logical consistency score based on NLI checks

        Matches database function calculate_trust_score():
        - New users with < 10 answers: Low base score (0.3-0.6)
        - Users with 10+ answers and no contradictions: High score (0.8-1.0)
        - Unresolved contradictions decrease trust
        """
        # Check how many answers user has
        answers_result = self.supabase.table('user_answers').select(
            'question_id', count='exact'
        ).eq('user_id', user_id).execute()

        answer_count = answers_result.count

        # New users with insufficient data get lower base score
        if answer_count < 10:
            # Gradually increase base score from 0.3 to 0.6 as they answer more
            base_score = 0.3 + (answer_count / 10) * 0.3
            return base_score

        # Check for contradictions
        result = self.supabase.table('consistency_checks').select(
            'contradiction_score, is_resolved'
        ).eq('user_id', user_id).eq('is_resolved', False).execute()

        if not result.data:
            # User has enough answers and no contradictions
            # Give high score that increases with more answers
            if answer_count >= 30:
                return 1.0
            elif answer_count >= 20:
                return 0.9
            else:
                return 0.8

        # Calculate average contradiction score
        contradiction_scores = [
            check['contradiction_score']
            for check in result.data
            if check['contradiction_score'] is not None
        ]

        if not contradiction_scores:
            return 0.8

        avg_contradiction = sum(contradiction_scores) / len(contradiction_scores)

        # Penalize for number of contradictions
        count_penalty = min(0.1 * len(contradiction_scores), 0.3)

        consistency_score = 1.0 - avg_contradiction - count_penalty

        return max(0.0, consistency_score)

    async def _calculate_behavioral_score(self, user_id: str) -> float:
        """
        Calculate behavioral trust score based on user actions

        Matches database function calculate_trust_score():
        - New accounts start at 0.5 (50%) base score
        - Build up with account age (max +0.3)
        - Lose points for suspicious behavior

        New users must build trust over time!
        """
        # Get account age first - this determines base score
        profile_result = self.supabase.table('profiles').select(
            'created_at'
        ).eq('user_id', user_id).single().execute()

        # Base score starts at 0.5 for new accounts
        base_score = 0.5
        age_bonus = 0.0

        if profile_result.data:
            created_at = datetime.fromisoformat(
                profile_result.data['created_at'].replace('Z', '+00:00')
            )
            account_age_days = (datetime.now(created_at.tzinfo) - created_at).days

            # Build trust over time
            if account_age_days >= 180:  # 6+ months
                age_bonus = 0.30
            elif account_age_days >= 90:  # 3+ months
                age_bonus = 0.20
            elif account_age_days >= 30:  # 1+ month
                age_bonus = 0.10
            elif account_age_days >= 7:   # 1+ week
                age_bonus = 0.05
            # New accounts (< 7 days) get no bonus

        # Check for negative behavior
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        result = self.supabase.table('user_behavior_logs').select(
            'event_type, risk_level, created_at'
        ).eq('user_id', user_id).gte('created_at', thirty_days_ago).execute()

        total_penalty = 0.0

        if result.data:
            # Calculate risk penalties
            risk_penalties = {
                'critical': 0.25,
                'high': 0.15,
                'medium': 0.05,
                'low': 0.01
            }

            for log in result.data:
                risk_level = log['risk_level']
                penalty = risk_penalties[risk_level]
                total_penalty += penalty

            # Cap total penalty at 0.4
            total_penalty = min(total_penalty, 0.4)

        # Final score: base + age bonus - penalties
        behavioral_score = base_score + age_bonus - total_penalty

        return max(0.0, min(1.0, behavioral_score))

    async def _calculate_completeness_score(self, user_id: str) -> float:
        """
        Calculate profile completeness score

        Matches database function calculate_trust_score():
        - Basic profile fields (30%)
        - Questions answered (40%)
        - Family background (15%)
        - Documents uploaded (15%)
        """
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
            total_questions = self.get_total_questions()
            questions_score = min(answers_result.count / total_questions, 1.0)
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

    async def _calculate_photo_score(self, user_id: str) -> float:
        """
        Calculate photo verification score

        Matches database function calculate_photo_verification_score():
        - Checks photo_verifications table for most recent verified photo
        - Scores based on quality and freshness (expiration)
        """
        result = self.supabase.table('photo_verifications').select(
            'verified_at, verification_score, expires_at, verification_status'
        ).eq('user_id', user_id).eq('verification_status', 'verified').order(
            'verified_at', desc=True
        ).limit(1).execute()

        if not result.data:
            return 0.0

        photo = result.data[0]
        verification_score = photo['verification_score']
        expires_at = datetime.fromisoformat(photo['expires_at'].replace('Z', '+00:00'))
        now = datetime.now(expires_at.tzinfo)

        # Score based on quality and freshness
        if expires_at > now and verification_score >= 0.90:
            return 1.0  # Recent + high quality
        elif expires_at > now and verification_score >= 0.75:
            return 0.8  # Recent + good quality
        elif expires_at <= now:
            return 0.5  # Expired - needs re-verification
        else:
            return 0.6

    async def _calculate_social_score(self, user_id: str) -> float:
        """
        Calculate social verification score

        Matches database function calculate_social_verification_score():
        - LinkedIn: 40% + 10% bonus if account age > 2 years
        - Instagram: 30% + 5% bonus if followers > 500
        - KakaoTalk: 20%
        - Naver: 10%
        - Verified accounts: +15% bonus
        """
        result = self.supabase.table('social_verifications').select(
            'platform, account_age_days, follower_count, is_verified_account, verification_status'
        ).eq('user_id', user_id).eq('verification_status', 'verified').execute()

        if not result.data:
            return 0.0

        score = 0.0

        for social in result.data:
            platform = social['platform']
            account_age_days = social.get('account_age_days', 0)
            follower_count = social.get('follower_count', 0)
            is_verified = social.get('is_verified_account', False)

            # Base platform scores
            if platform == 'linkedin':
                score += 0.40
                if account_age_days > 730:  # > 2 years
                    score += 0.10
            elif platform == 'instagram':
                score += 0.30
                if follower_count > 500:
                    score += 0.05
            elif platform == 'kakao':
                score += 0.20
            elif platform == 'naver':
                score += 0.10

            # Verified account bonus
            if is_verified:
                score += 0.15

        return min(1.0, score)

    async def _calculate_reputation_score(self, user_id: str) -> float:
        """
        Calculate reputation score

        Matches database function calculate_reputation_score():
        - Starts at 1.0
        - Confirmed reports: -0.20 each (last 180 days)
        - Ghosting rate: -0.10
        - Positive outcome rate: +0.10
        """
        score = 1.0

        # Confirmed reports (severe penalty: -0.20 each)
        six_months_ago = (datetime.now() - timedelta(days=180)).isoformat()
        reports_result = self.supabase.table('user_reports').select(
            'id', count='exact'
        ).eq('reported_user_id', user_id).eq('status', 'confirmed').gte(
            'created_at', six_months_ago
        ).execute()

        confirmed_reports = reports_result.count if reports_result.count else 0
        score -= confirmed_reports * 0.20

        # Ghosting rate and positive outcomes from conversation analytics
        analytics_result = self.supabase.table('conversation_analytics').select(
            'ghosting_pattern, positive_outcome, total_messages'
        ).eq('user_id', user_id).execute()

        if analytics_result.data:
            # Ghosting rate (only conversations with >= 10 messages)
            relevant_convos = [c for c in analytics_result.data if c.get('total_messages', 0) >= 10]
            if relevant_convos:
                ghosting_count = sum(1 for c in relevant_convos if c.get('ghosting_pattern', False))
                ghosting_rate = ghosting_count / len(relevant_convos)
                score -= ghosting_rate * 0.10

            # Positive outcome rate
            if analytics_result.data:
                positive_count = sum(1 for c in analytics_result.data if c.get('positive_outcome', False))
                positive_rate = positive_count / len(analytics_result.data)
                score += positive_rate * 0.10

        return max(0.0, min(1.0, score))

    def _determine_tier(self, total_score: float) -> str:
        """Determine trust tier based on total score"""
        for tier, threshold in self.TIER_THRESHOLDS.items():
            if total_score >= threshold:
                return tier.value
        return TrustTier.PEBBLE.value

    async def _store_trust_score(
        self,
        user_id: str,
        doc_score: float,
        photo_score: float,
        consistency_score: float,
        behavioral_score: float,
        social_score: float,
        completeness_score: float,
        reputation_score: float,
        total_score: float,
        trust_tier: str
    ):
        """
        Store calculated trust score in database

        UPDATED: Now stores all 7 components for consistency
        - Document (25%), Photo (20%), Consistency (15%), Behavioral (15%)
        - Social (10%), Completeness (10%), Reputation (5%)
        """
        self.supabase.table('user_trust_scores').upsert({
            'user_id': user_id,
            'document_score': doc_score,
            'photo_score': photo_score,
            'consistency_score': consistency_score,
            'behavioral_score': behavioral_score,
            'social_score': social_score,
            'completeness_score': completeness_score,
            'reputation_score': reputation_score,
            'total_trust_score': total_score,
            'trust_tier': trust_tier,
            'last_calculated_at': datetime.now().isoformat()
        }).execute()

        # Also update profile
        self.supabase.table('profiles').update({
            'trust_tier': trust_tier
        }).eq('user_id', user_id).execute()

    async def get_trust_score(self, user_id: str) -> Optional[TrustScoreResponse]:
        """
        Get existing trust score for a user
        Returns None if not calculated yet
        UPDATED: Now reads all 7 components from database (no on-the-fly calculation)
        """
        result = self.supabase.table('user_trust_scores').select(
            '*'
        ).eq('user_id', user_id).single().execute()

        if not result.data:
            return None

        data = result.data

        return TrustScoreResponse(
            user_id=user_id,
            document_score=data['document_score'],
            photo_score=data.get('photo_score', 0.0),
            consistency_score=data['consistency_score'],
            behavioral_score=data['behavioral_score'],
            social_score=data.get('social_score', 0.0),
            completeness_score=data['completeness_score'],
            reputation_score=data.get('reputation_score', 1.0),
            total_trust_score=data['total_trust_score'],
            trust_tier=data['trust_tier'],
            calculation_details=data.get('calculation_details', {}),
            last_calculated_at=datetime.fromisoformat(
                data['last_calculated_at'].replace('Z', '+00:00')
            )
        )

    async def get_trust_summary(self, user_id: str) -> TrustSummary:
        """
        Get simplified trust summary for API responses
        Raises exception on errors - no fallback logic
        """
        # Use RPC function
        result = self.supabase.rpc('get_user_trust_summary', {
            'p_user_id': user_id
        }).execute()

        # No fallback - will raise if data is missing
        data = result.data
        verification_status = data['verification_status']

        verified_items = []
        if verification_status['id_verified']:
            verified_items.append('신분증')
        if verification_status['education_verified']:
            verified_items.append('학력')
        if verification_status['income_verified']:
            verified_items.append('소득')
        if verification_status['employment_verified']:
            verified_items.append('재직')
        if verification_status['phone_verified']:
            verified_items.append('전화번호')

        trust_tier = data['trust_tier']

        return TrustSummary(
            trust_score=data['trust_score'],
            trust_tier=trust_tier,
            verified_items=verified_items,
            profile_completeness=data['component_scores']['completeness'],
            is_matching_enabled=trust_tier != 'pebble'
        )

    async def get_tier_benefits(self, trust_tier: str) -> Dict[str, Any]:
        """
        Get benefits associated with a trust tier
        """
        # No fallback - will raise ValueError if invalid tier
        tier = TrustTier(trust_tier)
        return self.TIER_BENEFITS[tier]

    async def get_minimum_tier_for_matching(self, user_tier: str) -> List[str]:
        """
        Get minimum tiers that a user can see in matches
        Higher tier users see only similar or higher tier profiles
        """
        benefits = await self.get_tier_benefits(user_tier)
        return benefits['can_see_tiers']

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
