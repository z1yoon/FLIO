"""
Reinforcement Learning for Question Selection

Uses Multi-Armed Bandit (Thompson Sampling) to learn:
1. Which questions lead to better profile completion
2. Which questions users engage with more
3. Which questions improve match quality

Why Multi-Armed Bandit over Deep RL:
- Simpler to implement and maintain
- Works well with limited data
- Interpretable results
- No neural network training required
- Fast inference
"""

import json
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class QuestionStats:
    """Statistics for a single question"""
    question_id: str
    # Thompson Sampling parameters (Beta distribution)
    alpha: float = 1.0  # Success count + 1
    beta: float = 1.0   # Failure count + 1
    # Additional metrics
    times_asked: int = 0
    times_answered: int = 0
    avg_answer_length: float = 0.0
    avg_clarity_score: float = 50.0
    led_to_match: int = 0  # Number of successful matches after this question
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class QuestionSelector:
    """
    Multi-Armed Bandit based Question Selection
    
    Uses Thompson Sampling to balance:
    - Exploitation: Ask questions that have worked well
    - Exploration: Try questions we don't know much about
    
    Reward signals:
    1. Answer quality (clarity score from Qwen2.5)
    2. User engagement (did they answer? how detailed?)
    3. Match success (did questions lead to good matches?)
    """
    
    def __init__(self):
        self.question_stats: Dict[str, QuestionStats] = {}
        self.context_stats: Dict[str, Dict[str, QuestionStats]] = {}
        # Context keys: category, user_age_group, user_gender, time_of_day
    
    def select_question(
        self,
        candidate_questions: List[Dict[str, Any]],
        user_context: Optional[Dict[str, Any]] = None,
        exploration_rate: float = 0.1
    ) -> Dict[str, Any]:
        """
        Select the best question using Thompson Sampling
        
        Args:
            candidate_questions: List of questions from RAG retrieval
            user_context: User info for contextualized selection
            exploration_rate: Probability of pure exploration (epsilon)
        
        Returns:
            Selected question with selection metadata
        """
        if not candidate_questions:
            return None
        
        # Epsilon-greedy exploration
        if np.random.random() < exploration_rate:
            selected = np.random.choice(candidate_questions)
            return {
                **selected,
                "selection_method": "exploration",
                "selection_score": 0.5
            }
        
        # Thompson Sampling
        best_score = -1
        best_question = None
        
        for question in candidate_questions:
            q_id = question["id"]
            stats = self._get_stats(q_id, user_context)
            
            # Sample from Beta distribution
            sampled_score = np.random.beta(stats.alpha, stats.beta)
            
            # Boost by RAG relevance score
            relevance_boost = question.get("relevance_score", 0.5) * 0.3
            
            # Priority boost
            priority_boost = {"high": 0.2, "medium": 0.1, "low": 0.0}.get(
                question.get("priority", "medium"), 0.1
            )
            
            final_score = sampled_score + relevance_boost + priority_boost
            
            if final_score > best_score:
                best_score = final_score
                best_question = question
        
        return {
            **best_question,
            "selection_method": "thompson_sampling",
            "selection_score": float(best_score)
        }
    
    def select_questions(
        self,
        candidate_questions: List[Dict[str, Any]],
        num_questions: int,
        user_context: Optional[Dict[str, Any]] = None,
        diversity_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Select multiple diverse questions
        
        Uses Determinantal Point Process (DPP) approximation for diversity
        """
        if len(candidate_questions) <= num_questions:
            return candidate_questions
        
        selected = []
        remaining = candidate_questions.copy()
        selected_categories = set()
        
        while len(selected) < num_questions and remaining:
            # Calculate scores for remaining questions
            scores = []
            
            for question in remaining:
                q_id = question["id"]
                stats = self._get_stats(q_id, user_context)
                
                # Base score from Thompson Sampling
                base_score = np.random.beta(stats.alpha, stats.beta)
                
                # Diversity penalty for same category
                category = question.get("category", "unknown")
                diversity_penalty = diversity_weight if category in selected_categories else 0
                
                final_score = base_score - diversity_penalty
                scores.append(final_score)
            
            # Select best
            best_idx = np.argmax(scores)
            best_question = remaining.pop(best_idx)
            
            selected.append({
                **best_question,
                "selection_method": "diverse_thompson",
                "selection_score": float(scores[best_idx])
            })
            selected_categories.add(best_question.get("category", "unknown"))
        
        return selected
    
    def update_reward(
        self,
        question_id: str,
        reward: float,
        user_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update question statistics based on outcome
        
        Args:
            question_id: ID of the question
            reward: Reward value (0.0 to 1.0)
                - 0.0: No answer, skip, or very vague
                - 0.5: Answered but unclear
                - 1.0: Clear, detailed answer
            user_context: Context for segmented learning
            metadata: Additional info (answer_length, clarity_score, etc.)
        """
        stats = self._get_stats(question_id, user_context)
        
        # Update Beta distribution parameters
        # Reward > 0.5 is treated as success
        if reward > 0.5:
            stats.alpha += reward
        else:
            stats.beta += (1 - reward)
        
        # Update additional metrics
        stats.times_asked += 1
        if reward > 0:
            stats.times_answered += 1
        
        if metadata:
            # Exponential moving average for metrics
            decay = 0.1
            
            if "answer_length" in metadata:
                stats.avg_answer_length = (
                    (1 - decay) * stats.avg_answer_length +
                    decay * metadata["answer_length"]
                )
            
            if "clarity_score" in metadata:
                stats.avg_clarity_score = (
                    (1 - decay) * stats.avg_clarity_score +
                    decay * metadata["clarity_score"]
                )
            
            if metadata.get("led_to_match", False):
                stats.led_to_match += 1
        
        stats.last_updated = datetime.now().isoformat()
        
        # Store back
        self._set_stats(question_id, stats, user_context)
    
    def update_from_answer_analysis(
        self,
        question_id: str,
        answer_analysis: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ):
        """
        Convenience method to update from Qwen2.5 analysis output
        
        Expected analysis format from question_generator.analyze_answer():
            {
                "clarity_score": 0-100,
                "is_vague": bool,
                "needs_followup": bool,
                ...
            }
        """
        clarity = answer_analysis.get("clarity_score", 50) / 100.0
        is_vague = answer_analysis.get("is_vague", True)
        
        # Calculate reward
        reward = clarity
        if is_vague:
            reward *= 0.7  # Penalty for vague answers
        
        self.update_reward(
            question_id=question_id,
            reward=reward,
            user_context=user_context,
            metadata={
                "clarity_score": answer_analysis.get("clarity_score", 50),
                "answer_length": len(answer_analysis.get("key_info", [])) * 20
            }
        )
    
    def update_from_match_success(
        self,
        questions_asked: List[str],
        match_accepted: bool,
        user_context: Optional[Dict[str, Any]] = None
    ):
        """
        Update all questions that led to a successful match
        
        Called when:
        - User accepts a match -> reward boost
        - User rejects a match -> small penalty
        """
        reward_boost = 0.3 if match_accepted else -0.1
        
        for q_id in questions_asked:
            stats = self._get_stats(q_id, user_context)
            
            if match_accepted:
                stats.alpha += reward_boost
                stats.led_to_match += 1
            else:
                stats.beta += abs(reward_boost)
            
            stats.last_updated = datetime.now().isoformat()
            self._set_stats(q_id, stats, user_context)
    
    def get_question_performance(
        self,
        question_id: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get performance metrics for a question"""
        stats = self._get_stats(question_id, user_context)
        
        # Calculate expected success rate
        expected_success = stats.alpha / (stats.alpha + stats.beta)
        
        # Calculate confidence (variance of Beta distribution)
        variance = (stats.alpha * stats.beta) / (
            (stats.alpha + stats.beta) ** 2 * (stats.alpha + stats.beta + 1)
        )
        confidence = 1 - np.sqrt(variance) * 4  # Scale variance to 0-1
        
        return {
            "question_id": question_id,
            "expected_success_rate": float(expected_success),
            "confidence": float(max(0, confidence)),
            "times_asked": stats.times_asked,
            "times_answered": stats.times_answered,
            "answer_rate": stats.times_answered / max(stats.times_asked, 1),
            "avg_clarity_score": stats.avg_clarity_score,
            "led_to_matches": stats.led_to_match,
            "last_updated": stats.last_updated
        }
    
    def get_top_questions(
        self,
        category: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top performing questions overall or by category"""
        performances = []
        
        for q_id, stats in self.question_stats.items():
            perf = self.get_question_performance(q_id)
            performances.append(perf)
        
        # Sort by expected success rate
        performances.sort(key=lambda x: x["expected_success_rate"], reverse=True)
        
        return performances[:top_k]
    
    def export_stats(self) -> Dict[str, Any]:
        """Export all statistics for persistence"""
        return {
            "question_stats": {
                q_id: {
                    "alpha": s.alpha,
                    "beta": s.beta,
                    "times_asked": s.times_asked,
                    "times_answered": s.times_answered,
                    "avg_answer_length": s.avg_answer_length,
                    "avg_clarity_score": s.avg_clarity_score,
                    "led_to_match": s.led_to_match,
                    "last_updated": s.last_updated
                }
                for q_id, s in self.question_stats.items()
            },
            "context_stats": {
                ctx_key: {
                    q_id: {
                        "alpha": s.alpha,
                        "beta": s.beta,
                        "times_asked": s.times_asked,
                        "times_answered": s.times_answered
                    }
                    for q_id, s in ctx_stats.items()
                }
                for ctx_key, ctx_stats in self.context_stats.items()
            }
        }
    
    def import_stats(self, data: Dict[str, Any]):
        """Import statistics from persistence"""
        for q_id, stats_data in data.get("question_stats", {}).items():
            self.question_stats[q_id] = QuestionStats(
                question_id=q_id,
                **stats_data
            )
        
        for ctx_key, ctx_data in data.get("context_stats", {}).items():
            self.context_stats[ctx_key] = {}
            for q_id, stats_data in ctx_data.items():
                self.context_stats[ctx_key][q_id] = QuestionStats(
                    question_id=q_id,
                    **stats_data
                )
    
    def _get_stats(
        self,
        question_id: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> QuestionStats:
        """Get stats for question, optionally contextualized"""
        # Try context-specific stats first
        if user_context:
            ctx_key = self._make_context_key(user_context)
            if ctx_key in self.context_stats:
                if question_id in self.context_stats[ctx_key]:
                    return self.context_stats[ctx_key][question_id]
        
        # Fall back to global stats
        if question_id not in self.question_stats:
            self.question_stats[question_id] = QuestionStats(question_id=question_id)
        
        return self.question_stats[question_id]
    
    def _set_stats(
        self,
        question_id: str,
        stats: QuestionStats,
        user_context: Optional[Dict[str, Any]] = None
    ):
        """Set stats for question"""
        # Always update global stats
        self.question_stats[question_id] = stats
        
        # Also update context-specific stats
        if user_context:
            ctx_key = self._make_context_key(user_context)
            if ctx_key not in self.context_stats:
                self.context_stats[ctx_key] = {}
            self.context_stats[ctx_key][question_id] = stats
    
    def _make_context_key(self, user_context: Dict[str, Any]) -> str:
        """Create a key from user context for segmented learning"""
        # Use age group and gender for segmentation
        age = user_context.get("age", 30)
        age_group = f"{(age // 10) * 10}s"  # 20s, 30s, etc.
        gender = user_context.get("gender", "unknown")
        
        return f"{age_group}_{gender}"


class QuestionOrchestrator:
    """
    Orchestrates RAG + RL + Qwen2.5 for intelligent question selection
    
    Flow:
    1. RAG retrieves candidate questions based on context
    2. RL selects the best question(s)
    3. Qwen2.5 personalizes the selected question
    4. After answer, Qwen2.5 analyzes and RL updates
    """
    
    def __init__(
        self,
        rag_retriever,  # RAGQuestionRetriever instance
        rl_selector: Optional[QuestionSelector] = None,
        question_generator=None  # AdaptiveQuestionGenerator instance
    ):
        self.rag = rag_retriever
        self.rl = rl_selector or QuestionSelector()
        self.generator = question_generator
    
    def get_next_question(
        self,
        user_answer: str,
        current_question: str,
        answered_questions: List[str],
        user_profile: Dict[str, Any],
        num_questions: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get the next best question(s) to ask
        
        Args:
            user_answer: User's answer to current question
            current_question: The question that was asked
            answered_questions: IDs of already answered questions
            user_profile: User's profile for context
            num_questions: Number of questions to return
        
        Returns:
            List of questions with metadata
        """
        # Step 1: RAG retrieval
        candidates = self.rag.retrieve_by_context(
            user_answer=user_answer,
            current_question=current_question,
            answered_questions=answered_questions,
            top_k=10
        )
        
        # Add follow-up questions
        follow_ups = self.rag.get_follow_up_questions(
            self._find_question_id(current_question),
            answered_questions
        )
        candidates.extend(follow_ups)
        
        # Deduplicate
        seen_ids = set()
        unique_candidates = []
        for q in candidates:
            if q["id"] not in seen_ids:
                seen_ids.add(q["id"])
                unique_candidates.append(q)
        
        # Step 2: RL selection
        user_context = {
            "age": user_profile.get("age", 30),
            "gender": user_profile.get("gender", "unknown")
        }
        
        if num_questions == 1:
            selected = [self.rl.select_question(unique_candidates, user_context)]
        else:
            selected = self.rl.select_questions(
                unique_candidates, num_questions, user_context
            )
        
        # Step 3: Personalization with Qwen2.5 (optional)
        if self.generator:
            for i, question in enumerate(selected):
                personalized = self._personalize_question(
                    question, user_profile, user_answer
                )
                selected[i]["personalized_text"] = personalized
        
        return [q for q in selected if q is not None]
    
    def process_answer(
        self,
        question_id: str,
        question_text: str,
        answer: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process user's answer and update RL
        
        Returns analysis and whether follow-up is needed
        """
        # Analyze answer with Qwen2.5
        if self.generator:
            analysis = self.generator.analyze_answer(question_text, answer)
        else:
            # Basic analysis without Qwen2.5
            analysis = {
                "clarity_score": 70 if len(answer) > 20 else 30,
                "is_vague": len(answer) < 20,
                "needs_followup": len(answer) < 20
            }
        
        # Update RL
        user_context = {
            "age": user_profile.get("age", 30),
            "gender": user_profile.get("gender", "unknown")
        }
        
        self.rl.update_from_answer_analysis(
            question_id=question_id,
            answer_analysis=analysis,
            user_context=user_context
        )
        
        return analysis
    
    def _find_question_id(self, question_text: str) -> Optional[str]:
        """Find question ID by text"""
        for q_id, q in self.rag.questions.items():
            if q.text == question_text:
                return q_id
        return None
    
    def _personalize_question(
        self,
        question: Dict[str, Any],
        user_profile: Dict[str, Any],
        previous_answer: str
    ) -> str:
        """Use Qwen2.5 to personalize question based on context"""
        # For now, return original text
        # In production, call generator.personalize_question()
        return question.get("text", "")
