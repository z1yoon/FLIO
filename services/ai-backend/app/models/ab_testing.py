"""
A/B Testing Framework
Test different question strategies, matching algorithms, and UI variations

Features:
- Create experiments with multiple variants
- Automatic user assignment
- Track metrics per variant
- Statistical significance testing
- Winner determination
"""

import logging
import hashlib
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class Variant:
    """A single variant in an experiment"""
    id: str
    name: str
    config: Dict[str, Any]
    weight: float = 1.0  # Traffic allocation weight
    # Metrics
    users_assigned: int = 0
    conversions: int = 0
    total_value: float = 0.0  # Sum of metric values
    
    @property
    def conversion_rate(self) -> float:
        if self.users_assigned == 0:
            return 0.0
        return self.conversions / self.users_assigned
    
    @property
    def average_value(self) -> float:
        if self.users_assigned == 0:
            return 0.0
        return self.total_value / self.users_assigned


@dataclass
class Experiment:
    """An A/B test experiment"""
    id: str
    name: str
    description: str
    variants: List[Variant]
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    # Targeting
    user_percentage: float = 100.0  # % of users to include
    target_segments: List[str] = field(default_factory=list)  # e.g., ["age_20s", "female"]


class ABTestingFramework:
    """
    A/B Testing Framework for FLIO
    
    Example experiments:
    - Question order: 결혼관 먼저 vs 라이프스타일 먼저
    - Avatar personality: 친근한 vs 전문적인
    - Matching algorithm: BGE-M3 only vs BGE-M3 + Reranker
    """
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        self.user_assignments: Dict[str, Dict[str, str]] = {}  # user_id -> {experiment_id: variant_id}
    
    def create_experiment(
        self,
        experiment_id: str,
        name: str,
        description: str,
        variants: List[Dict[str, Any]],
        user_percentage: float = 100.0
    ) -> Experiment:
        """
        Create a new A/B test experiment
        
        Args:
            experiment_id: Unique ID
            name: Human-readable name
            description: What we're testing
            variants: List of variant configs
            user_percentage: % of users to include in test
        
        Example:
            create_experiment(
                "question_order_v1",
                "Question Order Test",
                "Test if starting with lifestyle questions improves completion",
                variants=[
                    {"id": "control", "name": "결혼관 먼저", "config": {"first_category": "결혼관"}},
                    {"id": "treatment", "name": "라이프스타일 먼저", "config": {"first_category": "라이프스타일"}}
                ]
            )
        """
        variant_objects = [
            Variant(
                id=v["id"],
                name=v["name"],
                config=v.get("config", {}),
                weight=v.get("weight", 1.0)
            )
            for v in variants
        ]
        
        experiment = Experiment(
            id=experiment_id,
            name=name,
            description=description,
            variants=variant_objects,
            user_percentage=user_percentage
        )
        
        self.experiments[experiment_id] = experiment
        logger.info(f"Created experiment: {name} with {len(variants)} variants")
        
        return experiment
    
    def start_experiment(self, experiment_id: str):
        """Start running an experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        exp = self.experiments[experiment_id]
        exp.status = ExperimentStatus.RUNNING
        exp.started_at = datetime.now().isoformat()
        logger.info(f"Started experiment: {exp.name}")
    
    def get_variant(
        self,
        experiment_id: str,
        user_id: str,
        user_segment: Optional[str] = None
    ) -> Optional[Variant]:
        """
        Get the variant for a user (deterministic assignment)
        
        Uses consistent hashing so same user always gets same variant
        """
        if experiment_id not in self.experiments:
            return None
        
        exp = self.experiments[experiment_id]
        
        if exp.status != ExperimentStatus.RUNNING:
            return None
        
        # Check if user should be in experiment
        if not self._should_include_user(user_id, exp):
            return None
        
        # Check cached assignment
        if user_id in self.user_assignments:
            if experiment_id in self.user_assignments[user_id]:
                variant_id = self.user_assignments[user_id][experiment_id]
                return next((v for v in exp.variants if v.id == variant_id), None)
        
        # Assign variant using consistent hashing
        variant = self._assign_variant(user_id, exp)
        
        # Cache assignment
        if user_id not in self.user_assignments:
            self.user_assignments[user_id] = {}
        self.user_assignments[user_id][experiment_id] = variant.id
        
        # Update stats
        variant.users_assigned += 1
        
        return variant
    
    def record_conversion(
        self,
        experiment_id: str,
        user_id: str,
        value: float = 1.0
    ):
        """
        Record a conversion/success event
        
        Args:
            experiment_id: Experiment to record for
            user_id: User who converted
            value: Metric value (e.g., completion rate, match score)
        """
        if experiment_id not in self.experiments:
            return
        
        if user_id not in self.user_assignments:
            return
        
        if experiment_id not in self.user_assignments[user_id]:
            return
        
        variant_id = self.user_assignments[user_id][experiment_id]
        exp = self.experiments[experiment_id]
        
        for variant in exp.variants:
            if variant.id == variant_id:
                variant.conversions += 1
                variant.total_value += value
                break
    
    def get_results(self, experiment_id: str) -> Dict[str, Any]:
        """
        Get experiment results with statistical analysis
        """
        if experiment_id not in self.experiments:
            return {}
        
        exp = self.experiments[experiment_id]
        
        results = {
            "experiment": {
                "id": exp.id,
                "name": exp.name,
                "status": exp.status.value,
                "started_at": exp.started_at
            },
            "variants": [],
            "winner": None,
            "confidence": 0.0
        }
        
        best_variant = None
        best_rate = -1
        
        for variant in exp.variants:
            variant_data = {
                "id": variant.id,
                "name": variant.name,
                "users": variant.users_assigned,
                "conversions": variant.conversions,
                "conversion_rate": variant.conversion_rate,
                "average_value": variant.average_value
            }
            results["variants"].append(variant_data)
            
            if variant.conversion_rate > best_rate:
                best_rate = variant.conversion_rate
                best_variant = variant
        
        # Determine winner
        if best_variant and best_variant.users_assigned >= 100:
            results["winner"] = best_variant.id
            results["confidence"] = self._calculate_confidence(exp.variants)
        
        return results
    
    def _should_include_user(self, user_id: str, exp: Experiment) -> bool:
        """Check if user should be included in experiment"""
        if exp.user_percentage >= 100:
            return True
        
        # Use hash to deterministically include/exclude
        hash_val = int(hashlib.md5(f"{user_id}:{exp.id}".encode()).hexdigest(), 16)
        return (hash_val % 100) < exp.user_percentage
    
    def _assign_variant(self, user_id: str, exp: Experiment) -> Variant:
        """Assign variant using weighted consistent hashing"""
        hash_val = int(hashlib.md5(f"{user_id}:{exp.id}:variant".encode()).hexdigest(), 16)
        
        # Calculate total weight
        total_weight = sum(v.weight for v in exp.variants)
        
        # Assign based on weight
        threshold = (hash_val % 1000) / 1000.0 * total_weight
        cumulative = 0.0
        
        for variant in exp.variants:
            cumulative += variant.weight
            if threshold < cumulative:
                return variant
        
        return exp.variants[-1]
    
    def _calculate_confidence(self, variants: List[Variant]) -> float:
        """Calculate statistical confidence (simplified)"""
        if len(variants) < 2:
            return 0.0
        
        # Simple z-test approximation
        v1, v2 = variants[0], variants[1]
        
        if v1.users_assigned < 30 or v2.users_assigned < 30:
            return 0.0
        
        p1 = v1.conversion_rate
        p2 = v2.conversion_rate
        n1 = v1.users_assigned
        n2 = v2.users_assigned
        
        if p1 == p2:
            return 0.0
        
        # Pooled proportion
        p_pool = (v1.conversions + v2.conversions) / (n1 + n2)
        
        if p_pool == 0 or p_pool == 1:
            return 0.0
        
        # Standard error
        se = (p_pool * (1 - p_pool) * (1/n1 + 1/n2)) ** 0.5
        
        if se == 0:
            return 0.0
        
        # Z-score
        z = abs(p1 - p2) / se
        
        # Convert to confidence (approximate)
        if z > 2.58:
            return 0.99
        elif z > 1.96:
            return 0.95
        elif z > 1.65:
            return 0.90
        else:
            return min(0.85, z / 2)


# Pre-configured experiments for FLIO
def create_default_experiments(framework: ABTestingFramework):
    """Create default experiments for FLIO"""
    
    # Experiment 1: Question order
    framework.create_experiment(
        "question_order_v1",
        "Question Category Order",
        "Test which category to ask first for better completion",
        variants=[
            {
                "id": "marriage_first",
                "name": "결혼관 먼저",
                "config": {"first_category": "결혼관", "categories_order": ["결혼관", "가치관", "재정", "라이프스타일", "가족"]}
            },
            {
                "id": "lifestyle_first",
                "name": "라이프스타일 먼저",
                "config": {"first_category": "라이프스타일", "categories_order": ["라이프스타일", "가치관", "결혼관", "재정", "가족"]}
            }
        ]
    )
    
    # Experiment 2: Avatar tone
    framework.create_experiment(
        "avatar_tone_v1",
        "Avatar Personality",
        "Test friendly vs professional avatar tone",
        variants=[
            {
                "id": "friendly",
                "name": "친근한 톤",
                "config": {"tone": "friendly", "emoji_usage": True, "formality": "casual"}
            },
            {
                "id": "professional",
                "name": "전문적인 톤",
                "config": {"tone": "professional", "emoji_usage": False, "formality": "formal"}
            }
        ]
    )
    
    # Experiment 3: Matching algorithm
    framework.create_experiment(
        "matching_algo_v1",
        "Matching Algorithm",
        "Test BGE-M3 only vs BGE-M3 + Reranker",
        variants=[
            {
                "id": "bge_only",
                "name": "BGE-M3 Only",
                "config": {"use_reranker": False}
            },
            {
                "id": "bge_reranker",
                "name": "BGE-M3 + Reranker",
                "config": {"use_reranker": True}
            }
        ]
    )
    
    return framework
