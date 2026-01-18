"""
FLIO Behavioral Tracking Service
Monitors user behavior patterns for trust scoring

Tracks:
- Profile edit patterns
- Critical field changes
- Answer modifications
- Login patterns
- Suspicious activities
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
from enum import Enum

from ..models.database import get_supabase_client

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of tracked events"""
    PROFILE_EDIT = "profile_edit"
    INCOME_CHANGE = "income_change"
    EDUCATION_CHANGE = "education_change"
    REAL_NAME_CHANGE = "real_name_change"
    ANSWER_CHANGE = "answer_change"
    ANSWER_REWRITE = "answer_rewrite"
    PHOTO_CHANGE = "photo_change"
    LOGIN = "login"
    PROFILE_VIEW = "profile_view"
    MATCH_ACTION = "match_action"
    DOCUMENT_UPLOAD = "document_upload"


class RiskLevel(str, Enum):
    """Risk levels for behavioral events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BehaviorEvent(BaseModel):
    """A single behavior event"""
    event_type: str
    event_category: str
    risk_level: str
    field_changed: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    risk_reason: Optional[str]
    created_at: datetime


class BehavioralReport(BaseModel):
    """Behavioral analysis report for a user"""
    user_id: str
    behavioral_score: float
    risk_assessment: str
    total_events: int
    high_risk_events: int
    recent_events: List[BehaviorEvent]
    patterns_detected: List[str]
    recommendations: List[str]


class BehavioralTrackingService:
    """
    Service for tracking and analyzing user behavior patterns
    Part of the Korean marriage agency style trust system
    """

    # Risk classification rules
    RISK_RULES = {
        EventType.REAL_NAME_CHANGE: RiskLevel.CRITICAL,
        EventType.INCOME_CHANGE: RiskLevel.HIGH,
        EventType.EDUCATION_CHANGE: RiskLevel.HIGH,
        EventType.ANSWER_REWRITE: RiskLevel.MEDIUM,
        EventType.PROFILE_EDIT: RiskLevel.LOW,
        EventType.PHOTO_CHANGE: RiskLevel.LOW,
        EventType.ANSWER_CHANGE: RiskLevel.LOW,
        EventType.LOGIN: RiskLevel.LOW,
        EventType.DOCUMENT_UPLOAD: RiskLevel.LOW,
    }

    # Penalty values for score calculation
    RISK_PENALTIES = {
        RiskLevel.CRITICAL: 0.25,
        RiskLevel.HIGH: 0.15,
        RiskLevel.MEDIUM: 0.05,
        RiskLevel.LOW: 0.01
    }

    # Suspicious pattern thresholds
    PATTERN_THRESHOLDS = {
        'high_risk_events_30d': 3,      # More than 3 high-risk events in 30 days
        'income_changes_90d': 2,        # More than 2 income changes in 90 days
        'answer_rewrites_7d': 5,        # More than 5 answer rewrites in 7 days
        'profile_edits_24h': 10,        # More than 10 profile edits in 24 hours
    }

    def __init__(self):
        self.supabase = get_supabase_client()

    async def log_event(
        self,
        user_id: str,
        event_type: EventType,
        event_data: Dict = None,
        field_changed: str = None,
        old_value: str = None,
        new_value: str = None,
        session_id: str = None,
        ip_address: str = None
    ) -> str:
        """
        Log a behavioral event

        Returns: event log ID
        """
        try:
            # Determine risk level
            risk_level = self._assess_risk(
                user_id, event_type, field_changed, old_value, new_value
            )

            # Generate risk reason
            risk_reason = self._generate_risk_reason(
                event_type, risk_level, field_changed, old_value, new_value
            )

            # Determine event category
            event_category = self._get_event_category(event_type)

            # Store in database
            result = self.supabase.table('user_behavior_logs').insert({
                'user_id': user_id,
                'event_type': event_type.value,
                'event_category': event_category,
                'event_data': event_data or {},
                'field_changed': field_changed,
                'old_value': old_value,
                'new_value': new_value,
                'risk_level': risk_level.value,
                'risk_reason': risk_reason,
                'session_id': session_id,
                'ip_address': ip_address
            }).execute()

            log_id = result.data[0]['id'] if result.data else ""

            # Check if trust score needs recalculation
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                await self._trigger_trust_recalculation(user_id)

            logger.info(f"Logged behavior event: user={user_id}, type={event_type.value}, risk={risk_level.value}")

            return log_id

        except Exception as e:
            logger.error(f"Failed to log behavior event: {e}")
            return ""

    def _assess_risk(
        self,
        user_id: str,
        event_type: EventType,
        field_changed: str,
        old_value: str,
        new_value: str
    ) -> RiskLevel:
        """Assess risk level for an event"""
        # Start with base risk for event type
        base_risk = self.RISK_RULES.get(event_type, RiskLevel.LOW)

        # Elevate risk for certain field changes
        if field_changed:
            critical_fields = ['real_name', 'birth_date', 'id_number']
            high_risk_fields = ['annual_income_range', 'education_level', 'employment_status']

            if field_changed in critical_fields:
                return RiskLevel.CRITICAL
            elif field_changed in high_risk_fields:
                return RiskLevel.HIGH

        # Check for suspicious value changes
        if old_value and new_value:
            # Large income changes are suspicious
            if 'income' in (field_changed or ''):
                try:
                    old_num = self._extract_number(old_value)
                    new_num = self._extract_number(new_value)
                    if old_num and new_num:
                        change_ratio = abs(new_num - old_num) / max(old_num, 1)
                        if change_ratio > 0.5:  # More than 50% change
                            return RiskLevel.HIGH
                except:
                    pass

        return base_risk

    def _extract_number(self, value: str) -> Optional[int]:
        """Extract numeric value from string"""
        import re
        numbers = re.findall(r'\d+', str(value).replace(',', ''))
        if numbers:
            return int(numbers[0])
        return None

    def _generate_risk_reason(
        self,
        event_type: EventType,
        risk_level: RiskLevel,
        field_changed: str,
        old_value: str,
        new_value: str
    ) -> str:
        """Generate human-readable risk reason"""
        reasons = {
            (EventType.REAL_NAME_CHANGE, RiskLevel.CRITICAL):
                "실명 변경은 재인증이 필요합니다",
            (EventType.INCOME_CHANGE, RiskLevel.HIGH):
                "소득 정보가 변경되었습니다",
            (EventType.EDUCATION_CHANGE, RiskLevel.HIGH):
                "학력 정보가 변경되었습니다",
            (EventType.ANSWER_REWRITE, RiskLevel.MEDIUM):
                "답변이 크게 수정되었습니다",
        }

        key = (event_type, risk_level)
        if key in reasons:
            return reasons[key]

        if field_changed:
            return f"{field_changed} 필드가 변경되었습니다"

        return f"{event_type.value} 이벤트 발생"

    def _get_event_category(self, event_type: EventType) -> str:
        """Get category for event type"""
        categories = {
            EventType.REAL_NAME_CHANGE: "critical",
            EventType.INCOME_CHANGE: "critical",
            EventType.EDUCATION_CHANGE: "critical",
            EventType.ANSWER_REWRITE: "important",
            EventType.PROFILE_EDIT: "general",
            EventType.PHOTO_CHANGE: "general",
            EventType.ANSWER_CHANGE: "general",
            EventType.LOGIN: "general",
            EventType.DOCUMENT_UPLOAD: "positive",
        }
        return categories.get(event_type, "general")

    async def _trigger_trust_recalculation(self, user_id: str):
        """Trigger trust score recalculation for high-risk events"""
        try:
            from .trust_score_service import trust_score_service
            await trust_score_service.calculate_trust_score(user_id)
        except Exception as e:
            logger.error(f"Failed to trigger trust recalculation: {e}")

    async def get_behavioral_report(self, user_id: str) -> BehavioralReport:
        """
        Generate comprehensive behavioral report for a user
        """
        try:
            # Get all events in last 30 days
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()

            result = self.supabase.table('user_behavior_logs').select(
                '*'
            ).eq('user_id', user_id).gte(
                'created_at', thirty_days_ago
            ).order('created_at', desc=True).execute()

            events = result.data if result.data else []

            # Count by risk level
            risk_counts = {level.value: 0 for level in RiskLevel}
            for event in events:
                risk = event.get('risk_level', 'low')
                risk_counts[risk] = risk_counts.get(risk, 0) + 1

            # Calculate behavioral score
            behavioral_score = self._calculate_behavioral_score(events)

            # Detect patterns
            patterns = await self._detect_patterns(user_id, events)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                behavioral_score, patterns, risk_counts
            )

            # Determine risk assessment
            risk_assessment = self._assess_overall_risk(behavioral_score, patterns)

            # Format recent events
            recent_events = [
                BehaviorEvent(
                    event_type=e['event_type'],
                    event_category=e['event_category'],
                    risk_level=e['risk_level'],
                    field_changed=e.get('field_changed'),
                    old_value=e.get('old_value'),
                    new_value=e.get('new_value'),
                    risk_reason=e.get('risk_reason'),
                    created_at=datetime.fromisoformat(e['created_at'].replace('Z', '+00:00'))
                )
                for e in events[:10]  # Last 10 events
            ]

            return BehavioralReport(
                user_id=user_id,
                behavioral_score=behavioral_score,
                risk_assessment=risk_assessment,
                total_events=len(events),
                high_risk_events=risk_counts.get('high', 0) + risk_counts.get('critical', 0),
                recent_events=recent_events,
                patterns_detected=patterns,
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"Failed to generate behavioral report: {e}")
            return BehavioralReport(
                user_id=user_id,
                behavioral_score=1.0,
                risk_assessment="unknown",
                total_events=0,
                high_risk_events=0,
                recent_events=[],
                patterns_detected=[],
                recommendations=[]
            )

    def _calculate_behavioral_score(self, events: List[Dict]) -> float:
        """Calculate behavioral score from events"""
        total_penalty = 0.0

        for event in events:
            risk_level = event.get('risk_level', 'low')
            try:
                penalty = self.RISK_PENALTIES.get(RiskLevel(risk_level), 0.01)
            except ValueError:
                penalty = 0.01
            total_penalty += penalty

        # Cap penalty at 0.8
        total_penalty = min(total_penalty, 0.8)

        return max(0.0, 1.0 - total_penalty)

    async def _detect_patterns(
        self,
        user_id: str,
        recent_events: List[Dict]
    ) -> List[str]:
        """Detect suspicious behavioral patterns"""
        patterns = []

        # Count high-risk events
        high_risk_count = sum(
            1 for e in recent_events
            if e.get('risk_level') in ['high', 'critical']
        )
        if high_risk_count >= self.PATTERN_THRESHOLDS['high_risk_events_30d']:
            patterns.append(f"30일 내 {high_risk_count}건의 고위험 이벤트 발생")

        # Check income changes (need 90 days)
        ninety_days_ago = (datetime.now() - timedelta(days=90)).isoformat()
        income_result = self.supabase.table('user_behavior_logs').select(
            'id', count='exact'
        ).eq('user_id', user_id).eq(
            'event_type', 'income_change'
        ).gte('created_at', ninety_days_ago).execute()

        if income_result.count and income_result.count >= self.PATTERN_THRESHOLDS['income_changes_90d']:
            patterns.append(f"90일 내 {income_result.count}회 소득 정보 변경")

        # Check answer rewrites in 7 days
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        rewrite_count = sum(
            1 for e in recent_events
            if e.get('event_type') == 'answer_rewrite'
            and e.get('created_at', '') >= seven_days_ago
        )
        if rewrite_count >= self.PATTERN_THRESHOLDS['answer_rewrites_7d']:
            patterns.append(f"7일 내 {rewrite_count}회 답변 대폭 수정")

        # Check profile edits in 24 hours
        one_day_ago = (datetime.now() - timedelta(hours=24)).isoformat()
        edit_count = sum(
            1 for e in recent_events
            if e.get('event_type') == 'profile_edit'
            and e.get('created_at', '') >= one_day_ago
        )
        if edit_count >= self.PATTERN_THRESHOLDS['profile_edits_24h']:
            patterns.append(f"24시간 내 {edit_count}회 프로필 수정 (과다)")

        return patterns

    def _generate_recommendations(
        self,
        score: float,
        patterns: List[str],
        risk_counts: Dict[str, int]
    ) -> List[str]:
        """Generate recommendations based on behavioral analysis"""
        recommendations = []

        if score < 0.5:
            recommendations.append("프로필 정보를 안정적으로 유지해주세요")

        if risk_counts.get('critical', 0) > 0:
            recommendations.append("중요 정보 변경 시 문서 재인증이 필요할 수 있습니다")

        if patterns:
            recommendations.append("잦은 정보 변경은 신뢰도에 영향을 줄 수 있습니다")

        if not recommendations:
            recommendations.append("현재 행동 패턴이 양호합니다")

        return recommendations

    def _assess_overall_risk(
        self,
        score: float,
        patterns: List[str]
    ) -> str:
        """Assess overall behavioral risk"""
        if score >= 0.9 and not patterns:
            return "excellent"
        elif score >= 0.7 and len(patterns) <= 1:
            return "good"
        elif score >= 0.5:
            return "moderate"
        elif score >= 0.3:
            return "concerning"
        else:
            return "high_risk"

    async def get_behavioral_score(self, user_id: str) -> float:
        """Get current behavioral score for a user"""
        try:
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()

            result = self.supabase.table('user_behavior_logs').select(
                'risk_level'
            ).eq('user_id', user_id).gte('created_at', thirty_days_ago).execute()

            if not result.data:
                return 1.0

            return self._calculate_behavioral_score(result.data)

        except Exception as e:
            logger.error(f"Failed to get behavioral score: {e}")
            return 1.0


# Singleton instance
behavioral_tracking_service = BehavioralTrackingService()
