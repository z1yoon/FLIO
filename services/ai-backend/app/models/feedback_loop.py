"""
User Feedback Loop & Secret Profile Verification

Features:
1. Match Outcome Tracking - Learn from successful/failed matches
2. Secret Profile Verification - Users can report if profile info was incorrect
3. Trust Score System - Track user credibility

Secret Verification Flow:
1. User A meets User B in real life
2. After meeting, User A can secretly report if B's info was accurate
3. User B NEVER knows who reported them
4. If 2+ reports say info is wrong → User B is blocked until they correct info
5. This creates accountability without confrontation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    ACCURATE = "accurate"
    INACCURATE = "inaccurate"
    NOT_SURE = "not_sure"


class ProfileField(Enum):
    HEIGHT = "height"
    WEIGHT = "weight"
    AGE = "age"
    PHOTOS = "photos"
    JOB = "job"
    EDUCATION = "education"
    OTHER = "other"


@dataclass
class SecretReport:
    """A secret report about another user's profile accuracy"""
    id: str
    reporter_id: str  # Who reported (kept secret)
    reported_user_id: str  # Who was reported
    field: ProfileField
    status: VerificationStatus
    actual_value: Optional[str] = None  # What the reporter claims is true
    notes: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UserTrustProfile:
    """Trust/credibility profile for a user"""
    user_id: str
    # Verification status
    total_reports_received: int = 0
    inaccurate_reports: int = 0  # Times reported as inaccurate
    accurate_reports: int = 0  # Times reported as accurate
    # Field-specific issues
    flagged_fields: Dict[str, int] = field(default_factory=dict)  # field -> report count
    # Status
    is_blocked: bool = False
    blocked_until: Optional[str] = None
    blocked_reason: Optional[str] = None
    # Trust score (0-100)
    trust_score: float = 100.0
    
    @property
    def accuracy_rate(self) -> float:
        total = self.accurate_reports + self.inaccurate_reports
        if total == 0:
            return 1.0
        return self.accurate_reports / total


class FeedbackLoopSystem:
    """
    Feedback Loop for learning from match outcomes
    and secret profile verification
    """
    
    def __init__(self, rl_selector=None):
        self.rl_selector = rl_selector
        self.match_outcomes: Dict[str, Dict] = {}  # match_id -> outcome
        self.secret_reports: List[SecretReport] = []
        self.user_trust: Dict[str, UserTrustProfile] = {}
        
        # Configuration
        self.reports_to_flag = 2  # Reports needed to flag a field
        self.reports_to_block = 2  # Reports needed to block user
        self.block_duration_days = 7  # How long to block
    
    # ==========================================
    # Match Outcome Tracking
    # ==========================================
    
    def record_match_outcome(
        self,
        match_id: str,
        user_a_id: str,
        user_b_id: str,
        questions_asked_a: List[str],
        questions_asked_b: List[str],
        outcome: str,  # "success" | "chatting" | "met" | "dating" | "rejected" | "no_response"
        days_active: int = 0
    ):
        """
        Record match outcome for RL learning
        
        Outcomes and rewards:
        - "success": Users are dating/together → highest reward
        - "met": Met in person → high reward
        - "chatting": Still chatting after 7 days → medium reward
        - "rejected": One user rejected → slight penalty
        - "no_response": No engagement → no reward
        """
        outcome_rewards = {
            "dating": 1.0,
            "met": 0.8,
            "chatting": 0.5,
            "rejected": -0.1,
            "no_response": 0.0
        }
        
        reward = outcome_rewards.get(outcome, 0.0)
        
        # Boost reward for longer engagement
        if days_active > 30:
            reward *= 1.2
        elif days_active > 7:
            reward *= 1.1
        
        # Store outcome
        self.match_outcomes[match_id] = {
            "user_a": user_a_id,
            "user_b": user_b_id,
            "outcome": outcome,
            "reward": reward,
            "days_active": days_active,
            "recorded_at": datetime.now().isoformat()
        }
        
        # Update RL if available
        if self.rl_selector:
            # Reward questions that led to successful match
            if reward > 0:
                all_questions = list(set(questions_asked_a + questions_asked_b))
                self.rl_selector.update_from_match_success(
                    questions_asked=all_questions,
                    match_accepted=(reward > 0.3),
                    user_context={"match_id": match_id}
                )
        
        logger.info(f"Recorded match outcome: {match_id} → {outcome} (reward: {reward})")
        
        return reward
    
    def get_match_statistics(self) -> Dict[str, Any]:
        """Get overall match statistics for analysis"""
        if not self.match_outcomes:
            return {"total": 0, "outcomes": {}}
        
        outcomes_count = {}
        total_reward = 0.0
        
        for match in self.match_outcomes.values():
            outcome = match["outcome"]
            outcomes_count[outcome] = outcomes_count.get(outcome, 0) + 1
            total_reward += match["reward"]
        
        return {
            "total_matches": len(self.match_outcomes),
            "outcomes": outcomes_count,
            "average_reward": total_reward / len(self.match_outcomes),
            "success_rate": outcomes_count.get("dating", 0) / len(self.match_outcomes)
        }
    
    # ==========================================
    # Secret Profile Verification
    # ==========================================
    
    def submit_secret_report(
        self,
        reporter_id: str,
        reported_user_id: str,
        field: str,
        is_accurate: bool,
        actual_value: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a secret report about another user's profile
        
        IMPORTANT: The reported user will NEVER know who reported them.
        
        Args:
            reporter_id: Who is reporting (kept secret)
            reported_user_id: Whose profile is being verified
            field: Which field (height, weight, photos, etc.)
            is_accurate: Was the info accurate?
            actual_value: What the reporter claims is true
            notes: Additional notes
        
        Returns:
            Status of the report and any actions taken
        """
        # Validate field
        try:
            field_enum = ProfileField(field)
        except ValueError:
            field_enum = ProfileField.OTHER
        
        # Create report
        report = SecretReport(
            id=f"report_{len(self.secret_reports)}_{datetime.now().timestamp()}",
            reporter_id=reporter_id,
            reported_user_id=reported_user_id,
            field=field_enum,
            status=VerificationStatus.ACCURATE if is_accurate else VerificationStatus.INACCURATE,
            actual_value=actual_value,
            notes=notes
        )
        
        self.secret_reports.append(report)
        
        # Update user trust profile
        result = self._update_trust_profile(reported_user_id, report)
        
        logger.info(f"Secret report submitted for user {reported_user_id[:8]}... on {field}")
        
        return result
    
    def _update_trust_profile(
        self,
        user_id: str,
        report: SecretReport
    ) -> Dict[str, Any]:
        """Update trust profile based on new report"""
        
        # Get or create trust profile
        if user_id not in self.user_trust:
            self.user_trust[user_id] = UserTrustProfile(user_id=user_id)
        
        profile = self.user_trust[user_id]
        profile.total_reports_received += 1
        
        result = {
            "action": "recorded",
            "field": report.field.value,
            "user_blocked": False,
            "field_flagged": False
        }
        
        if report.status == VerificationStatus.ACCURATE:
            profile.accurate_reports += 1
            # Increase trust score slightly
            profile.trust_score = min(100, profile.trust_score + 2)
        
        elif report.status == VerificationStatus.INACCURATE:
            profile.inaccurate_reports += 1
            
            # Track field-specific issues
            field_name = report.field.value
            profile.flagged_fields[field_name] = profile.flagged_fields.get(field_name, 0) + 1
            
            # Decrease trust score
            profile.trust_score = max(0, profile.trust_score - 10)
            
            # Check if field should be flagged
            if profile.flagged_fields[field_name] >= self.reports_to_flag:
                result["field_flagged"] = True
                result["flagged_field"] = field_name
            
            # Check if user should be blocked
            if profile.inaccurate_reports >= self.reports_to_block:
                self._block_user(profile, report.field.value)
                result["user_blocked"] = True
                result["action"] = "user_blocked"
                result["blocked_until"] = profile.blocked_until
                result["message"] = f"프로필 정보({field_name})가 정확하지 않다는 신고가 접수되었습니다."
        
        return result
    
    def _block_user(self, profile: UserTrustProfile, field: str):
        """Block user until they correct their info"""
        profile.is_blocked = True
        profile.blocked_until = (
            datetime.now() + timedelta(days=self.block_duration_days)
        ).isoformat()
        profile.blocked_reason = f"프로필 정보({field})가 부정확하다는 신고가 2회 이상 접수됨"
        
        logger.warning(f"User {profile.user_id[:8]}... blocked for inaccurate {field}")
    
    def check_user_status(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user is blocked or has flagged fields
        
        Call this before showing user in matches
        """
        if user_id not in self.user_trust:
            return {
                "user_id": user_id,
                "status": "verified",
                "trust_score": 100,
                "is_blocked": False,
                "flagged_fields": []
            }
        
        profile = self.user_trust[user_id]
        
        # Check if block has expired
        if profile.is_blocked and profile.blocked_until:
            blocked_until = datetime.fromisoformat(profile.blocked_until)
            if datetime.now() > blocked_until:
                profile.is_blocked = False
                profile.blocked_until = None
        
        flagged = [
            field for field, count in profile.flagged_fields.items()
            if count >= self.reports_to_flag
        ]
        
        status = "blocked" if profile.is_blocked else "flagged" if flagged else "verified"
        
        return {
            "user_id": user_id,
            "status": status,
            "trust_score": profile.trust_score,
            "is_blocked": profile.is_blocked,
            "blocked_until": profile.blocked_until,
            "blocked_reason": profile.blocked_reason,
            "flagged_fields": flagged,
            "accuracy_rate": profile.accuracy_rate
        }
    
    def get_user_notification(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get notification for user if they need to correct info
        
        IMPORTANT: Does NOT reveal who reported them!
        """
        status = self.check_user_status(user_id)
        
        if status["is_blocked"]:
            return {
                "type": "blocked",
                "title": "프로필 수정이 필요합니다",
                "message": f"회원님의 프로필 정보가 실제와 다르다는 피드백이 있었습니다. "
                          f"정확한 정보로 수정해주세요.",
                "fields_to_update": status["flagged_fields"],
                "blocked_until": status["blocked_until"],
                # 누가 신고했는지는 절대 공개하지 않음!
                "action_required": True
            }
        
        if status["flagged_fields"]:
            return {
                "type": "warning",
                "title": "프로필 확인 요청",
                "message": f"다음 정보가 정확한지 확인해주세요: {', '.join(status['flagged_fields'])}",
                "fields_to_update": status["flagged_fields"],
                "action_required": False
            }
        
        return None
    
    def user_updated_profile(self, user_id: str, updated_fields: List[str]):
        """
        Called when user updates their profile
        
        Clears flags for updated fields and potentially unblocks
        """
        if user_id not in self.user_trust:
            return
        
        profile = self.user_trust[user_id]
        
        # Clear flags for updated fields
        for field in updated_fields:
            if field in profile.flagged_fields:
                del profile.flagged_fields[field]
        
        # Unblock if all flagged fields are updated
        if profile.is_blocked:
            remaining_flags = [
                f for f, c in profile.flagged_fields.items()
                if c >= self.reports_to_flag
            ]
            
            if not remaining_flags:
                profile.is_blocked = False
                profile.blocked_until = None
                profile.blocked_reason = None
                # Reset inaccurate count (give them a fresh start)
                profile.inaccurate_reports = max(0, profile.inaccurate_reports - 1)
                
                logger.info(f"User {user_id[:8]}... unblocked after profile update")
    
    def get_post_meeting_prompt(self, user_id: str, met_user_id: str) -> Dict[str, Any]:
        """
        Generate the prompt shown to user after they meet someone
        
        This is the UI for secret verification
        """
        return {
            "title": "만남은 어떠셨나요?",
            "subtitle": "회원님의 피드백은 익명으로 처리됩니다",
            "met_user_id": met_user_id,
            "questions": [
                {
                    "field": "overall",
                    "question": "프로필 정보가 전체적으로 정확했나요?",
                    "options": ["정확했어요", "조금 달랐어요", "많이 달랐어요"]
                },
                {
                    "field": "photos",
                    "question": "프로필 사진과 실제 모습이 비슷했나요?",
                    "options": ["비슷했어요", "조금 달랐어요", "많이 달랐어요"]
                },
                {
                    "field": "height",
                    "question": "키 정보가 정확했나요?",
                    "options": ["정확했어요", "5cm 이내", "5cm 이상 차이"]
                },
                {
                    "field": "job",
                    "question": "직업/직장 정보가 정확했나요?",
                    "options": ["정확했어요", "조금 달랐어요", "많이 달랐어요"]
                }
            ],
            "note": "💡 회원님의 피드백은 다른 회원들이 더 정확한 정보를 볼 수 있도록 도와줍니다. "
                   "상대방에게는 절대 공개되지 않습니다."
        }
