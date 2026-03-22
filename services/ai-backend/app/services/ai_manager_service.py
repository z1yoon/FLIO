"""
FLIO AI Manager Service
Core logic for conversational AI marriage manager:
  - Ambiguity detection + follow-up question generation
  - Profile quality diagnostics
  - Structured feedback processing + weight learning
  - Proactive coaching messages
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from ..models.database import get_supabase_client
from .azure_openai_service import azure_openai_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes (plain dicts used for flexibility, typed here for clarity)
# ---------------------------------------------------------------------------

class AmbiguityResult:
    def __init__(self, score: float, is_ambiguous: bool, reason: str, followup: Optional[str]):
        self.score = score            # 0.0 (clear) – 1.0 (totally vague)
        self.is_ambiguous = is_ambiguous
        self.reason = reason
        self.followup = followup      # The follow-up question text


class DiagnosticIssue:
    def __init__(self, severity: str, issue: str, impact: str, solution: str):
        self.severity = severity      # 'high' | 'medium' | 'low'
        self.issue = issue
        self.impact = impact
        self.solution = solution

    def to_dict(self) -> Dict:
        return {
            "severity": self.severity,
            "issue": self.issue,
            "impact": self.impact,
            "solution": self.solution,
        }


class ProfileDiagnosisResult:
    def __init__(self, overall_score: int, issues: List[DiagnosticIssue],
                 recommendations: List[str], estimated_improvement_pct: int,
                 market_percentile: int):
        self.overall_score = overall_score
        self.issues = issues
        self.recommendations = recommendations
        self.estimated_improvement_pct = estimated_improvement_pct
        self.market_percentile = market_percentile


# ---------------------------------------------------------------------------
# AIManagerService
# ---------------------------------------------------------------------------

class AIManagerService:
    """
    Two-layer ambiguity detection architecture:

    Layer 1 — Heuristics (this class, _quick_vague_check):
        Cheap, zero-latency pattern matching. Runs before ANY LLM call.
        If the answer is clearly specific, skip the LLM entirely (cost savings).
        If borderline or clearly vague, escalate to Layer 2.

    Layer 2 — LLM (azure_openai_service.generate_followup_question):
        Deep contextual analysis — considers previous answers, cultural nuance,
        semantic vagueness, and generates a targeted follow-up question.
        VAGUE_PATTERNS below are echoed in the LLM system prompt purely as
        *examples for the model*, not as duplicate logic.

    All LLM calls use the shared _MANAGER_PERSONA defined in AzureOpenAIService
    so persona/tone is consistent across every AI manager endpoint.
    """

    AMBIGUITY_THRESHOLD = 0.55  # score above this → trigger follow-up

    # Heuristic pre-filter patterns (Layer 1). These are ALSO referenced in the
    # LLM system prompt as examples — that's intentional, not duplication.
    # Purpose here: avoid LLM call when answer is trivially clear or trivially vague.
    VAGUE_PATTERNS = [
        "상관없어요", "상관없음", "괜찮아요", "모르겠어요", "글쎄요",
        "그냥", "다 좋아요", "뭐든지", "아무거나", "적당히",
        "보통", "평범", "그냥 그래요", "잘 모르겠어요",
    ]

    def __init__(self):
        self.supabase = get_supabase_client()

    # ------------------------------------------------------------------
    # 1. AMBIGUITY DETECTION & FOLLOW-UP GENERATION
    # ------------------------------------------------------------------

    def _quick_vague_check(self, answer: str) -> float:
        """Fast heuristic check before calling LLM. Returns 0-1 vagueness."""
        answer_lower = answer.strip().lower()

        # Very short answer
        if len(answer_lower) <= 5:
            return 0.85

        # Exact vague phrase match
        for pattern in self.VAGUE_PATTERNS:
            if pattern in answer_lower:
                return 0.80

        # Single word answers for open-ended questions
        if len(answer_lower.split()) <= 2:
            return 0.65

        return 0.0  # Not obviously vague

    async def detect_ambiguity_and_followup(
        self,
        question_text: str,
        answer: str,
        question_category: str,
        previous_answers: Optional[List[Dict]] = None,
    ) -> AmbiguityResult:
        """
        Detect if the answer is ambiguous and generate a context-aware follow-up.
        Uses heuristics first; calls LLM only when score is borderline.
        """
        quick_score = self._quick_vague_check(answer)

        # If clearly vague via heuristics, still call LLM for smart follow-up
        if quick_score < self.AMBIGUITY_THRESHOLD:
            return AmbiguityResult(
                score=quick_score,
                is_ambiguous=False,
                reason="Answer is specific enough",
                followup=None,
            )

        # Call LLM for analysis + follow-up generation
        try:
            result = await azure_openai_service.generate_followup_question(
                question_text=question_text,
                answer=answer,
                question_category=question_category,
                previous_answers=previous_answers or [],
            )
            return AmbiguityResult(
                score=result["ambiguity_score"],
                is_ambiguous=result["ambiguity_score"] >= self.AMBIGUITY_THRESHOLD,
                reason=result["reason"],
                followup=result.get("followup_question"),
            )
        except Exception as e:
            logger.error(f"Ambiguity detection failed: {e}")
            # Fallback: return heuristic score without follow-up
            return AmbiguityResult(
                score=quick_score,
                is_ambiguous=quick_score >= self.AMBIGUITY_THRESHOLD,
                reason="Heuristic detection",
                followup=None,
            )

    async def log_followup(
        self,
        user_id: str,
        question_id: str,
        original_answer: str,
        ambiguity_score: float,
        followup_question: str,
    ) -> Optional[str]:
        """Persist follow-up log; returns the log record id."""
        try:
            result = self.supabase.table("followup_question_log").insert({
                "user_id": user_id,
                "question_id": question_id,
                "original_answer": original_answer,
                "ambiguity_score": ambiguity_score,
                "followup_question": followup_question,
            }).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            logger.warning(f"Failed to log follow-up: {e}")
            return None

    async def save_followup_answer(self, log_id: str, answer: str) -> None:
        """Update the follow-up log with user's answer."""
        try:
            self.supabase.table("followup_question_log").update({
                "followup_answer": answer,
                "followup_answered_at": "now()",
            }).eq("id", log_id).execute()
        except Exception as e:
            logger.warning(f"Failed to save follow-up answer: {e}")

    # ------------------------------------------------------------------
    # 2. PROFILE QUALITY DIAGNOSTICS
    # ------------------------------------------------------------------

    async def diagnose_profile(self, user_id: str) -> ProfileDiagnosisResult:
        """
        Full profile quality analysis. Returns structured issues and recommendations.
        """
        try:
            # Fetch user data
            profile_data = await self._fetch_profile_data(user_id)
            answer_data = await self._fetch_answer_data(user_id)
            feedback_summary = await self._get_feedback_summary(user_id)

            # Rule-based checks
            issues: List[DiagnosticIssue] = []
            dimension_scores: Dict[str, int] = {}

            # --- Photo check ---
            photos = profile_data.get("photos", [])
            photo_score = min(100, len(photos) * 25)
            dimension_scores["photo_score"] = photo_score
            if len(photos) == 0:
                issues.append(DiagnosticIssue(
                    "high", "사진이 없습니다", "매칭 확률 -80%",
                    "프로필 사진을 최소 1장 이상 추가하세요. 자연스러운 일상 사진을 추천합니다."
                ))
            elif len(photos) < 3:
                issues.append(DiagnosticIssue(
                    "high", f"사진이 {len(photos)}장밖에 없습니다",
                    "매칭 확률 -50%",
                    "얼굴, 전신, 취미 활동 사진을 포함해 3장 이상 추가하세요."
                ))

            # --- Answer completeness ---
            total_questions = answer_data.get("total_questions", 40)
            answered = answer_data.get("answered_count", 0)
            completion_pct = (answered / total_questions * 100) if total_questions > 0 else 0
            completeness_score = int(completion_pct)
            dimension_scores["answer_completeness_score"] = completeness_score
            if completion_pct < 50:
                issues.append(DiagnosticIssue(
                    "high", f"프로필 완성도가 낮습니다 ({int(completion_pct)}%)",
                    "AI 매칭 정확도 -60%",
                    f"나머지 {total_questions - answered}개 질문에 답변하세요. 완성도가 높을수록 정확한 매칭이 이루어집니다."
                ))
            elif completion_pct < 80:
                issues.append(DiagnosticIssue(
                    "medium", f"프로필 완성도 {int(completion_pct)}%",
                    "AI 매칭 정확도 -25%",
                    f"나머지 {total_questions - answered}개 질문에 추가 답변하면 매칭 품질이 향상됩니다."
                ))

            # --- Open-ended answer quality ---
            open_answers = answer_data.get("open_answers", [])
            short_open = [a for a in open_answers if len(a) < 30]
            quality_score = max(0, 100 - len(short_open) * 25)
            dimension_scores["answer_quality_score"] = quality_score
            if len(short_open) > 0:
                issues.append(DiagnosticIssue(
                    "medium",
                    f"서술형 답변 {len(short_open)}개가 너무 짧습니다",
                    "AI 임베딩 매칭 정확도 -40%",
                    "서술형 답변을 2-3문장으로 구체적으로 작성하면 AI가 더 정확하게 매칭합니다."
                ))

            # --- Preference range too narrow ---
            dealbreaker_count = answer_data.get("dealbreaker_count", 0)
            consistency_score = max(0, 100 - max(0, dealbreaker_count - 5) * 10)
            dimension_scores["preference_consistency_score"] = consistency_score
            if dealbreaker_count > 8:
                issues.append(DiagnosticIssue(
                    "medium",
                    f"딜브레이커가 {dealbreaker_count}개로 너무 많습니다",
                    "매칭 풀 -70%",
                    "딜브레이커를 5개 이내로 줄이면 더 많은 적합한 상대를 만날 수 있습니다."
                ))

            # --- Feedback-based insight ---
            if feedback_summary.get("avg_rating", 0) < 3.0 and feedback_summary.get("total_feedback", 0) >= 3:
                common_issues = feedback_summary.get("common_dealbreakers", [])
                if common_issues:
                    issues.append(DiagnosticIssue(
                        "medium",
                        f"반복되는 불만족 패턴: {', '.join(common_issues[:2])}",
                        "매칭 만족도 지속 낮음",
                        "AI 매니저와 대화를 통해 선호 조건을 재정립해보세요."
                    ))

            # --- AI-powered deeper analysis ---
            if open_answers:
                try:
                    ai_diagnosis = await azure_openai_service.diagnose_profile_quality(
                        profile_data=profile_data,
                        answers_summary=answer_data,
                        existing_issues=[i.to_dict() for i in issues],
                    )
                    for ai_issue in ai_diagnosis.get("additional_issues", []):
                        issues.append(DiagnosticIssue(
                            ai_issue.get("severity", "low"),
                            ai_issue.get("issue", ""),
                            ai_issue.get("impact", ""),
                            ai_issue.get("solution", ""),
                        ))
                    recommendations = ai_diagnosis.get("recommendations", [])
                    market_percentile = ai_diagnosis.get("market_percentile", 50)
                except Exception as e:
                    logger.warning(f"AI diagnosis call failed, using rule-based only: {e}")
                    recommendations = self._build_default_recommendations(issues)
                    market_percentile = 50
            else:
                recommendations = self._build_default_recommendations(issues)
                market_percentile = 50

            # Compute overall score
            weights = {
                "photo_score": 0.30,
                "answer_completeness_score": 0.30,
                "answer_quality_score": 0.25,
                "preference_consistency_score": 0.15,
            }
            overall = int(sum(
                dimension_scores.get(k, 50) * w
                for k, w in weights.items()
            ))

            # Estimated improvement if all high-severity issues fixed
            high_issues = [i for i in issues if i.severity == "high"]
            estimated_improvement = min(60, len(high_issues) * 20)

            result = ProfileDiagnosisResult(
                overall_score=overall,
                issues=issues,
                recommendations=recommendations,
                estimated_improvement_pct=estimated_improvement,
                market_percentile=market_percentile,
            )

            # Cache in DB
            await self._cache_diagnostics(user_id, overall, dimension_scores, issues, recommendations, estimated_improvement, market_percentile)

            return result

        except Exception as e:
            logger.error(f"Profile diagnosis failed for {user_id}: {e}")
            raise

    def _build_default_recommendations(self, issues: List[DiagnosticIssue]) -> List[str]:
        recs = []
        if any(i.severity == "high" for i in issues):
            recs.append("심각도 높은 문제를 먼저 해결하세요. 사진 추가와 프로필 완성이 가장 중요합니다.")
        recs.append("서술형 답변을 구체적으로 작성할수록 AI 매칭 정확도가 올라갑니다.")
        recs.append("딜브레이커는 진짜 중요한 것만 5개 이내로 유지하세요.")
        return recs

    async def _cache_diagnostics(self, user_id: str, overall: int, dimensions: Dict,
                                  issues: List[DiagnosticIssue], recommendations: List[str],
                                  improvement_pct: int, market_percentile: int) -> None:
        try:
            self.supabase.table("profile_diagnostics").upsert({
                "user_id": user_id,
                "overall_score": overall,
                "photo_score": dimensions.get("photo_score"),
                "answer_completeness_score": dimensions.get("answer_completeness_score"),
                "answer_quality_score": dimensions.get("answer_quality_score"),
                "preference_consistency_score": dimensions.get("preference_consistency_score"),
                "issues": json.dumps([i.to_dict() for i in issues]),
                "recommendations": json.dumps(recommendations),
                "estimated_match_improvement_pct": improvement_pct,
                "market_percentile": market_percentile,
                "is_stale": False,
            }, on_conflict="user_id").execute()
        except Exception as e:
            logger.warning(f"Failed to cache diagnostics: {e}")

    # ------------------------------------------------------------------
    # 3. STRUCTURED FEEDBACK PROCESSING
    # ------------------------------------------------------------------

    async def process_match_feedback(
        self,
        user_id: str,
        match_user_id: str,
        overall_rating: int,
        dimension_ratings: Dict[str, int],
        positive_aspects: List[str],
        dealbreaker_aspects: List[str],
        free_text: Optional[str] = None,
        implicit_signals: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Store structured match feedback and update learned question weights.
        Returns updated matching context.
        """
        try:
            # 1. Upsert feedback record
            feedback_record = {
                "user_id": user_id,
                "match_user_id": match_user_id,
                "overall_rating": overall_rating,
                "values_alignment_rating": dimension_ratings.get("values_alignment"),
                "lifestyle_match_rating": dimension_ratings.get("lifestyle_match"),
                "conversation_comfort_rating": dimension_ratings.get("conversation_comfort"),
                "marriage_seriousness_rating": dimension_ratings.get("marriage_seriousness"),
                "positive_aspects": positive_aspects,
                "dealbreaker_aspects": dealbreaker_aspects,
                "free_text_feedback": free_text,
                "feedback_type": "explicit",
            }
            if implicit_signals:
                feedback_record.update({
                    "profile_view_duration_seconds": implicit_signals.get("view_duration"),
                    "conversation_initiated": implicit_signals.get("conversation_started", False),
                    "photos_viewed": implicit_signals.get("photos_viewed", 0),
                })

            self.supabase.table("match_feedback").upsert(
                feedback_record, on_conflict="user_id,match_user_id"
            ).execute()

            # 2. Update learned weights after sufficient feedback
            await self._update_learned_weights(user_id)

            # 3. Invalidate diagnostics cache if low rating
            if overall_rating <= 2:
                self.supabase.table("profile_diagnostics").update(
                    {"is_stale": True}
                ).eq("user_id", user_id).execute()

            return {
                "success": True,
                "message": "피드백이 저장되었습니다. 다음 매칭 추천에 반영됩니다.",
                "needs_diagnosis": overall_rating <= 2,
            }

        except Exception as e:
            logger.error(f"Failed to process feedback for {user_id}: {e}")
            raise

    async def _update_learned_weights(self, user_id: str) -> None:
        """
        Derive per-question importance weights from accumulated feedback.
        Requires ≥5 feedbacks to have statistical confidence.
        """
        try:
            # Get all feedback for this user
            feedback_result = self.supabase.table("match_feedback").select(
                "overall_rating, values_alignment_rating, lifestyle_match_rating, "
                "conversation_comfort_rating, marriage_seriousness_rating, "
                "positive_aspects, dealbreaker_aspects"
            ).eq("user_id", user_id).execute()

            feedbacks = feedback_result.data or []
            if len(feedbacks) < 5:
                return  # Not enough data yet

            # Simple weight derivation: dimension ratings vs overall satisfaction
            dimension_to_question_groups = {
                "values_alignment_rating": [
                    "family_values", "conflict_resolution", "trust_building",
                    "marriage_timeline", "personal_values_lifestyle"
                ],
                "lifestyle_match_rating": [
                    "lifestyle_preferences", "social_energy", "daily_routine",
                    "hobbies_activities"
                ],
                "conversation_comfort_rating": [
                    "communication_style", "ideal_relationship_dynamic",
                    "conflict_growth_philosophy"
                ],
                "marriage_seriousness_rating": [
                    "marriage_plan", "children_plan", "career_family_balance"
                ],
            }

            # Compute correlation: if dimension_rating correlates with overall → high weight
            weight_map: Dict[str, float] = {}
            for dim_field, question_ids in dimension_to_question_groups.items():
                dim_ratings = [f.get(dim_field) for f in feedbacks if f.get(dim_field)]
                overall_ratings = [f.get("overall_rating") for f in feedbacks if f.get(dim_field) and f.get("overall_rating")]

                if len(dim_ratings) >= 3:
                    correlation = self._pearson_correlation(dim_ratings, overall_ratings)
                    # Map correlation (−1 to 1) → weight multiplier (0.5 to 2.0)
                    weight_mult = max(0.5, min(2.0, 1.0 + correlation))
                    for qid in question_ids:
                        weight_map[qid] = round(weight_mult, 3)

            if not weight_map:
                return

            confidence = min(1.0, len(feedbacks) / 20)

            self.supabase.rpc("upsert_matching_weights", {
                "p_user_id": user_id,
                "p_question_weights": json.dumps(weight_map),
                "p_feedback_count": len(feedbacks),
                "p_confidence": confidence,
            }).execute()

            logger.info(f"Updated matching weights for {user_id} (n={len(feedbacks)}, weights={len(weight_map)})")

        except Exception as e:
            logger.warning(f"Weight update failed for {user_id}: {e}")

    def _pearson_correlation(self, x: List, y: List) -> float:
        """Simple Pearson correlation coefficient."""
        n = len(x)
        if n < 2:
            return 0.0
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        std_x = (sum((xi - mean_x) ** 2 for xi in x) / n) ** 0.5
        std_y = (sum((yi - mean_y) ** 2 for yi in y) / n) ** 0.5
        if std_x == 0 or std_y == 0:
            return 0.0
        return cov / (n * std_x * std_y)

    # ------------------------------------------------------------------
    # 4. AI MANAGER CONVERSATIONAL CHAT
    # ------------------------------------------------------------------

    async def chat(
        self,
        user_id: str,
        user_message: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main conversational entry point for the AI manager.
        Loads session history, calls LLM, saves response.
        """
        try:
            # Load or create session
            session = await self._get_or_create_session(user_id, session_id)
            messages = session.get("messages", [])

            # Build context enrichment for the LLM
            user_context = await self._build_user_context(user_id)

            # Get AI response
            ai_reply = await azure_openai_service.ai_manager_chat(
                user_message=user_message,
                conversation_history=messages,
                user_context=user_context,
            )

            # Append both turns
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            messages.append({"role": "user", "content": user_message, "timestamp": now})
            messages.append({"role": "assistant", "content": ai_reply["message"], "timestamp": now})

            # Persist updated session
            await self._save_session(session["id"], messages, ai_reply.get("extracted_insights", {}))

            return {
                "session_id": session["id"],
                "message": ai_reply["message"],
                "suggested_actions": ai_reply.get("suggested_actions", []),
                "intent_detected": ai_reply.get("intent", "general"),
            }

        except Exception as e:
            logger.error(f"AI manager chat failed for {user_id}: {e}")
            raise

    async def _get_or_create_session(self, user_id: str, session_id: Optional[str]) -> Dict:
        """Load existing session or create a new one."""
        if session_id:
            result = self.supabase.table("ai_manager_sessions").select("*").eq("id", session_id).execute()
            if result.data:
                return result.data[0]

        # Try to find an existing active session
        result = self.supabase.table("ai_manager_sessions").select("*").eq(
            "user_id", user_id
        ).eq("is_active", True).order("last_message_at", desc=True).limit(1).execute()

        if result.data:
            return result.data[0]

        # Create new session
        new_session = self.supabase.table("ai_manager_sessions").insert({
            "user_id": user_id,
            "session_type": "general",
            "messages": [],
        }).execute()
        return new_session.data[0]

    async def _save_session(self, session_id: str, messages: List[Dict], insights: Dict) -> None:
        try:
            self.supabase.table("ai_manager_sessions").update({
                "messages": json.dumps(messages),
                "extracted_insights": json.dumps(insights),
                "last_message_at": "now()",
            }).eq("id", session_id).execute()
        except Exception as e:
            logger.warning(f"Failed to save session {session_id}: {e}")

    async def _build_user_context(self, user_id: str) -> Dict[str, Any]:
        """Assemble user context for AI manager personalisation."""
        context: Dict[str, Any] = {"user_id": user_id}
        try:
            profile = self.supabase.table("profiles").select(
                "nickname, trust_tier, subscription_status"
            ).eq("user_id", user_id).single().execute()
            if profile.data:
                context.update(profile.data)
        except Exception:
            pass

        try:
            diagnostics = self.supabase.table("profile_diagnostics").select(
                "overall_score, issues"
            ).eq("user_id", user_id).single().execute()
            if diagnostics.data:
                context["profile_score"] = diagnostics.data["overall_score"]
                issues = diagnostics.data.get("issues") or []
                if isinstance(issues, str):
                    issues = json.loads(issues)
                context["top_issues"] = [i.get("issue") for i in issues[:3] if isinstance(i, dict)]
        except Exception:
            pass

        try:
            summary = self.supabase.rpc("get_user_feedback_summary", {"p_user_id": user_id}).execute()
            if summary.data:
                context["feedback_summary"] = summary.data
        except Exception:
            pass

        return context

    # ------------------------------------------------------------------
    # 5. HELPER: fetch profile / answer data
    # ------------------------------------------------------------------

    async def _fetch_profile_data(self, user_id: str) -> Dict:
        try:
            result = self.supabase.table("profiles").select(
                "nickname, photos, trust_tier, paid_tier"
            ).eq("user_id", user_id).single().execute()
            return result.data or {}
        except Exception as e:
            logger.warning(f"Failed to fetch profile for {user_id}: {e}")
            return {}

    async def _fetch_answer_data(self, user_id: str) -> Dict:
        try:
            # Count total and answered questions
            answers_result = self.supabase.table("user_answers").select(
                "question_id, answer_value, is_dealbreaker"
            ).eq("user_id", user_id).execute()

            answers = answers_result.data or []
            open_answer_question_ids = {
                "personal_values_lifestyle",
                "ideal_relationship_dynamic",
                "conflict_growth_philosophy",
            }
            open_answers = [
                a["answer_value"] for a in answers
                if a.get("question_id") in open_answer_question_ids
                and a.get("answer_value")
            ]
            dealbreaker_count = sum(1 for a in answers if a.get("is_dealbreaker"))

            return {
                "answered_count": len(answers),
                "total_questions": 40,
                "open_answers": open_answers,
                "dealbreaker_count": dealbreaker_count,
            }
        except Exception as e:
            logger.warning(f"Failed to fetch answers for {user_id}: {e}")
            return {"answered_count": 0, "total_questions": 40, "open_answers": [], "dealbreaker_count": 0}

    async def _get_feedback_summary(self, user_id: str) -> Dict:
        try:
            result = self.supabase.rpc("get_user_feedback_summary", {"p_user_id": user_id}).execute()
            return result.data or {}
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # 6. PROACTIVE COACHING
    # ------------------------------------------------------------------

    async def generate_proactive_coaching(self, user_id: str) -> Dict[str, Any]:
        """
        Generate proactive coaching messages based on user state.

        Trigger conditions (checked periodically or on app open):
        - Weekly tip if no coaching sent in 7 days
        - Inactivity nudge if no login in 3+ days
        - Milestone celebration (first match, first feedback, profile complete)
        - Low satisfaction alert if avg rating ≤ 2.5 over last 5 feedbacks
        """
        from datetime import datetime, timezone, timedelta

        triggers: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        profile_data = await self._fetch_profile_data(user_id)
        answer_data = await self._fetch_answer_data(user_id)
        feedback_summary = await self._get_feedback_summary(user_id)
        nickname = profile_data.get("nickname", "회원님")

        # --- Trigger: Inactivity nudge (3+ days since last session message) ---
        try:
            session_result = self.supabase.table("ai_manager_sessions").select(
                "last_message_at"
            ).eq("user_id", user_id).eq("is_active", True).order(
                "last_message_at", desc=True
            ).limit(1).execute()

            if session_result.data:
                last_msg_str = session_result.data[0].get("last_message_at", "")
                if last_msg_str:
                    last_msg_at = datetime.fromisoformat(last_msg_str.replace("Z", "+00:00"))
                    days_inactive = (now - last_msg_at).days
                    if days_inactive >= 3:
                        triggers.append({
                            "type": "inactivity_nudge",
                            "days_inactive": days_inactive,
                            "priority": "medium",
                        })
            else:
                # Never chatted with AI manager
                triggers.append({
                    "type": "first_time_welcome",
                    "priority": "high",
                })
        except Exception as e:
            logger.warning(f"Inactivity check failed: {e}")

        # --- Trigger: Profile incomplete ---
        completion_pct = 0
        total_q = answer_data.get("total_questions", 40)
        answered = answer_data.get("answered_count", 0)
        if total_q > 0:
            completion_pct = int(answered / total_q * 100)

        if completion_pct < 80:
            triggers.append({
                "type": "profile_incomplete",
                "completion_pct": completion_pct,
                "remaining": total_q - answered,
                "priority": "high",
            })

        # --- Trigger: Low satisfaction pattern ---
        avg_rating = feedback_summary.get("avg_rating", 0) if isinstance(feedback_summary, dict) else 0
        total_fb = feedback_summary.get("total_feedback", 0) if isinstance(feedback_summary, dict) else 0
        if total_fb >= 3 and avg_rating <= 2.5:
            triggers.append({
                "type": "low_satisfaction",
                "avg_rating": avg_rating,
                "total_feedback": total_fb,
                "common_dealbreakers": (
                    feedback_summary.get("common_dealbreakers", [])
                    if isinstance(feedback_summary, dict) else []
                ),
                "priority": "high",
            })

        # --- Trigger: Milestone celebration ---
        if total_fb == 1:
            triggers.append({"type": "milestone_first_feedback", "priority": "low"})
        if completion_pct == 100:
            triggers.append({"type": "milestone_profile_complete", "priority": "low"})

        if not triggers:
            return {
                "has_coaching": False,
                "message": None,
                "coaching_type": None,
            }

        # Pick highest priority trigger
        priority_order = {"high": 0, "medium": 1, "low": 2}
        triggers.sort(key=lambda t: priority_order.get(t.get("priority", "low"), 2))
        top_trigger = triggers[0]

        # Generate coaching message via LLM
        try:
            coaching_msg = await azure_openai_service.generate_coaching_message(
                nickname=nickname,
                trigger=top_trigger,
                profile_completion_pct=completion_pct,
                avg_rating=avg_rating,
            )
        except Exception as e:
            logger.warning(f"Coaching LLM call failed: {e}")
            coaching_msg = self._fallback_coaching_message(top_trigger, nickname, completion_pct)

        # Log coaching event
        try:
            self.supabase.table("coaching_log").insert({
                "user_id": user_id,
                "coaching_type": top_trigger["type"],
                "message": coaching_msg["message"],
                "trigger_data": top_trigger,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log coaching: {e}")

        return {
            "has_coaching": True,
            "message": coaching_msg["message"],
            "coaching_type": top_trigger["type"],
            "suggested_actions": coaching_msg.get("suggested_actions", []),
        }

    def _fallback_coaching_message(
        self, trigger: Dict, nickname: str, completion_pct: int
    ) -> Dict[str, Any]:
        """Offline fallback coaching messages when LLM is unavailable."""
        t = trigger.get("type", "")
        if t == "first_time_welcome":
            return {
                "message": f"{nickname}님, 안녕하세요! FLIO AI 매니저입니다. 좋은 만남을 위해 함께 준비해볼까요?",
                "suggested_actions": ["프로필 완성하기", "AI 매니저와 대화하기"],
            }
        if t == "inactivity_nudge":
            return {
                "message": f"{nickname}님, 요즘 어떻게 지내세요? 새로운 매칭 추천이 준비되어 있어요.",
                "suggested_actions": ["매칭 확인하기"],
            }
        if t == "profile_incomplete":
            return {
                "message": f"{nickname}님, 프로필 완성도가 {completion_pct}%입니다. 나머지 질문에 답하면 매칭 정확도가 크게 올라가요!",
                "suggested_actions": ["질문 답변하기"],
            }
        if t == "low_satisfaction":
            return {
                "message": f"{nickname}님, 최근 매칭이 만족스럽지 않으셨나요? AI 매니저와 대화하면 선호 조건을 재정립할 수 있어요.",
                "suggested_actions": ["AI 매니저와 상담하기", "프로필 진단받기"],
            }
        return {
            "message": f"{nickname}님, FLIO가 더 나은 매칭을 위해 준비하고 있어요!",
            "suggested_actions": [],
        }



# Singleton
ai_manager_service = AIManagerService()
