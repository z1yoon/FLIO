"""
RAG (Retrieval Augmented Generation) for Question Database

Purpose:
- Store curated questions for profile matching
- Retrieve relevant questions based on user context
- Use vector similarity for semantic search
- Categories: 결혼관/가치관/재정/라이프스타일/가족

Flow:
1. User answers a question
2. RAG retrieves related follow-up questions
3. Qwen2.5 personalizes the retrieved questions
4. RL ranks which question to ask next
"""

import json
import logging
import numpy as np
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Question:
    """Question data structure"""
    id: str
    text: str
    category: str
    priority: str  # high/medium/low
    tags: List[str]
    follow_up_ids: List[str]  # Related question IDs
    embedding: Optional[List[float]] = None


# Question Database - Load from questions_database.py
def _load_question_database():
    """Load questions from the main database"""
    try:
        from app.data.questions_database import ALL_QUESTIONS, QuestionCategory
        
        # Convert to RAG format
        category_map = {
            QuestionCategory.MARRIAGE: "결혼관",
            QuestionCategory.FAMILY: "가족",
            QuestionCategory.FINANCE: "재정",
            QuestionCategory.CAREER: "직장",
            QuestionCategory.RELIGION: "종교",
            QuestionCategory.LIFESTYLE: "라이프스타일",
            QuestionCategory.PERSONALITY: "성격",
            QuestionCategory.SOCIAL: "사회규범"
        }
        
        priority_map = lambda w: "high" if w >= 0.8 else "medium" if w >= 0.6 else "low"
        
        return [
            {
                "id": q.id,
                "text": q.text_ko,
                "category": category_map.get(q.category, "기타"),
                "priority": priority_map(q.importance_weight),
                "tags": q.tags or [],
                "follow_up_ids": q.follow_up_ids or [],
                "options": q.options or []
            }
            for q in ALL_QUESTIONS
        ]
    except ImportError:
        # Fallback to minimal set if database not available
        return _get_fallback_questions()


def _get_fallback_questions():
    """Fallback questions if main database unavailable"""
    return [
        {
            "id": "marriage_timeline",
            "text": "결혼을 언제쯤 생각하고 계세요?",
            "category": "결혼관",
            "priority": "high",
            "tags": ["결혼", "시기"],
            "follow_up_ids": ["marriage_reason"]
        },
        {
            "id": "children_plan",
            "text": "자녀 계획이 있으신가요?",
            "category": "가족",
            "priority": "high",
            "tags": ["자녀", "출산"],
            "follow_up_ids": ["children_count"]
        },
        {
            "id": "parents_living",
            "text": "부모님과 동거할 계획이 있으신가요?",
            "category": "가족",
            "priority": "high",
            "tags": ["부모", "동거"],
            "follow_up_ids": []
        },
        {
            "id": "finance_management",
            "text": "결혼 후 가계 재정은 어떻게 관리하고 싶으세요?",
            "category": "재정",
            "priority": "high",
            "tags": ["재정", "돈"],
            "follow_up_ids": []
        },
        {
            "id": "religion",
            "text": "종교가 있으신가요?",
            "category": "종교",
            "priority": "high",
            "tags": ["종교"],
            "follow_up_ids": ["religion_importance"]
        }
    ]


QUESTION_DATABASE = _load_question_database()


class RAGQuestionRetriever:
    """
    RAG-based Question Retrieval System
    
    Uses BGE-M3 embeddings to find semantically similar questions
    based on user's answers and context.
    """
    
    def __init__(self, embedding_model=None):
        """
        Args:
            embedding_model: Pre-loaded BGE-M3 model or None to load new
        """
        self.questions: Dict[str, Question] = {}
        self.question_embeddings: Optional[np.ndarray] = None
        self.question_ids: List[str] = []
        
        # Use provided model or load new
        if embedding_model:
            self.model = embedding_model
        else:
            self._load_embedding_model()
        
        # Initialize question database
        self._load_questions()
    
    def _load_embedding_model(self):
        """Load BGE-M3 for question embeddings"""
        try:
            from FlagEmbedding import BGEM3FlagModel
            
            logger.info("Loading BGE-M3 for RAG...")
            self.model = BGEM3FlagModel(
                'upskyy/bge-m3-korean',
                use_fp16=True
            )
            logger.info("BGE-M3 loaded for RAG")
        except Exception as e:
            logger.error(f"Failed to load BGE-M3: {e}")
            self.model = None
    
    def _load_questions(self):
        """Load and embed questions from database"""
        logger.info(f"Loading {len(QUESTION_DATABASE)} questions...")
        
        question_texts = []
        
        for q_data in QUESTION_DATABASE:
            question = Question(
                id=q_data["id"],
                text=q_data["text"],
                category=q_data["category"],
                priority=q_data["priority"],
                tags=q_data["tags"],
                follow_up_ids=q_data["follow_up_ids"]
            )
            self.questions[question.id] = question
            self.question_ids.append(question.id)
            question_texts.append(question.text)
        
        # Generate embeddings for all questions
        if self.model and question_texts:
            embeddings = self.model.encode(
                question_texts,
                return_dense=True
            )['dense_vecs']
            
            self.question_embeddings = np.array(embeddings)
            
            # Store embeddings in questions
            for i, q_id in enumerate(self.question_ids):
                self.questions[q_id].embedding = embeddings[i].tolist()
        
        logger.info("Questions loaded and embedded")
    
    def retrieve_by_context(
        self,
        user_answer: str,
        current_question: str,
        answered_questions: List[str],
        top_k: int = 5,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant questions based on context
        
        Args:
            user_answer: User's last answer
            current_question: The question that was asked
            answered_questions: List of question IDs already answered
            top_k: Number of questions to retrieve
            category_filter: Optional category to filter by
        
        Returns:
            List of questions with relevance scores
        """
        if self.model is None or self.question_embeddings is None:
            # Fallback: return follow-up questions
            return self._fallback_retrieval(current_question, answered_questions, top_k)
        
        # Create context query
        context_query = f"{current_question} {user_answer}"
        
        # Get query embedding
        query_embedding = self.model.encode(
            [context_query],
            return_dense=True
        )['dense_vecs'][0]
        
        # Calculate similarities
        similarities = np.dot(self.question_embeddings, query_embedding)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1]
        
        results = []
        for idx in top_indices:
            q_id = self.question_ids[idx]
            question = self.questions[q_id]
            
            # Skip already answered questions
            if q_id in answered_questions:
                continue
            
            # Apply category filter
            if category_filter and question.category != category_filter:
                continue
            
            results.append({
                "id": question.id,
                "text": question.text,
                "category": question.category,
                "priority": question.priority,
                "tags": question.tags,
                "relevance_score": float(similarities[idx])
            })
            
            if len(results) >= top_k:
                break
        
        return results
    
    def retrieve_by_category(
        self,
        category: str,
        answered_questions: List[str],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get top questions from a specific category
        
        Priority order: high > medium > low
        """
        priority_order = {"high": 0, "medium": 1, "low": 2}
        
        category_questions = [
            q for q in self.questions.values()
            if q.category == category and q.id not in answered_questions
        ]
        
        # Sort by priority
        category_questions.sort(
            key=lambda q: priority_order.get(q.priority, 3)
        )
        
        return [
            {
                "id": q.id,
                "text": q.text,
                "category": q.category,
                "priority": q.priority,
                "tags": q.tags,
                "relevance_score": 1.0 - (priority_order[q.priority] * 0.1)
            }
            for q in category_questions[:top_k]
        ]
    
    def get_follow_up_questions(
        self,
        question_id: str,
        answered_questions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get pre-defined follow-up questions for a given question
        """
        if question_id not in self.questions:
            return []
        
        question = self.questions[question_id]
        
        results = []
        for follow_up_id in question.follow_up_ids:
            if follow_up_id in answered_questions:
                continue
            if follow_up_id not in self.questions:
                continue
            
            follow_up = self.questions[follow_up_id]
            results.append({
                "id": follow_up.id,
                "text": follow_up.text,
                "category": follow_up.category,
                "priority": follow_up.priority,
                "tags": follow_up.tags,
                "relevance_score": 0.9  # High score for direct follow-ups
            })
        
        return results
    
    def get_coverage_analysis(
        self,
        answered_questions: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze which categories have been covered
        
        Returns:
            {
                "total_questions": 15,
                "answered": 5,
                "coverage_percent": 33.3,
                "by_category": {
                    "결혼관": {"total": 3, "answered": 1, "percent": 33.3},
                    ...
                },
                "missing_high_priority": ["question_id1", ...],
                "recommendation": "가치관 카테고리의 질문을 더 해보세요"
            }
        """
        category_stats: Dict[str, Dict[str, int]] = {}
        missing_high_priority = []
        
        for q in self.questions.values():
            if q.category not in category_stats:
                category_stats[q.category] = {"total": 0, "answered": 0}
            
            category_stats[q.category]["total"] += 1
            
            if q.id in answered_questions:
                category_stats[q.category]["answered"] += 1
            elif q.priority == "high":
                missing_high_priority.append(q.id)
        
        # Calculate percentages
        by_category = {}
        for category, stats in category_stats.items():
            by_category[category] = {
                "total": stats["total"],
                "answered": stats["answered"],
                "percent": (stats["answered"] / stats["total"] * 100) if stats["total"] > 0 else 0
            }
        
        # Find least covered category
        least_covered = min(
            by_category.items(),
            key=lambda x: x[1]["percent"]
        )
        
        return {
            "total_questions": len(self.questions),
            "answered": len(answered_questions),
            "coverage_percent": len(answered_questions) / len(self.questions) * 100,
            "by_category": by_category,
            "missing_high_priority": missing_high_priority,
            "recommendation": f"{least_covered[0]} 카테고리의 질문을 더 해보세요"
        }
    
    def _fallback_retrieval(
        self,
        current_question: str,
        answered_questions: List[str],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Fallback when embedding model not available"""
        # Find current question and return follow-ups
        current_id = None
        for q_id, q in self.questions.items():
            if q.text == current_question:
                current_id = q_id
                break
        
        if current_id:
            return self.get_follow_up_questions(current_id, answered_questions)
        
        # Return high priority questions not yet answered
        return self.retrieve_by_category("결혼관", answered_questions, top_k)
    
    def add_custom_question(
        self,
        question_id: str,
        text: str,
        category: str,
        priority: str = "medium",
        tags: List[str] = None,
        follow_up_ids: List[str] = None
    ):
        """Add a new question to the database (for dynamic questions)"""
        question = Question(
            id=question_id,
            text=text,
            category=category,
            priority=priority,
            tags=tags or [],
            follow_up_ids=follow_up_ids or []
        )
        
        # Generate embedding
        if self.model:
            embedding = self.model.encode(
                [text],
                return_dense=True
            )['dense_vecs'][0]
            question.embedding = embedding.tolist()
            
            # Update embeddings array
            self.question_embeddings = np.vstack([
                self.question_embeddings,
                embedding.reshape(1, -1)
            ])
        
        self.questions[question_id] = question
        self.question_ids.append(question_id)
