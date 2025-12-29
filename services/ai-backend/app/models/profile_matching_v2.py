"""
Profile Matching Model V2
Uses Korean Fine-tuned BGE-M3 for hybrid search (Dense + Sparse + ColBERT)

Model: upskyy/bge-m3-korean
- Fine-tuned on KorSTS + KorNLI datasets
- Pearson: 0.874, Spearman: 0.872 on Korean STS
- 1024D embeddings, 8192 max tokens
- Hybrid search (dense + sparse + colbert)

Why upskyy/bge-m3-korean over BAAI/bge-m3:
1. Korean-specific fine-tuning (+5% accuracy on Korean STS)
2. Better semantic understanding of Korean expressions
3. Same architecture, better Korean performance
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)

# Korean fine-tuned BGE-M3 model
# Source: https://huggingface.co/upskyy/bge-m3-korean
KOREAN_BGE_M3_MODEL = "upskyy/bge-m3-korean"


class ProfileMatchingModelV2:
    """
    Korean Fine-tuned BGE-M3 based profile matching
    
    Features:
    - Dense embeddings for semantic similarity
    - Sparse embeddings (lexical) for keyword matching
    - ColBERT for fine-grained matching
    - Hybrid scoring combines all three
    - Korean language optimized (KorSTS: 87.4)
    """
    
    def __init__(self, use_fp16: bool = True, model_name: str = KOREAN_BGE_M3_MODEL):
        try:
            from FlagEmbedding import BGEM3FlagModel
            
            logger.info(f"Loading Korean fine-tuned BGE-M3: {model_name}")
            self.model = BGEM3FlagModel(
                model_name,
                use_fp16=use_fp16,
            )
            self.embedding_dim = 1024
            self.model_name = model_name
            logger.info(f"Korean BGE-M3 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Korean BGE-M3: {e}")
            self.model = None
    
    def create_profile_text(self, profile: Dict[str, Any]) -> str:
        """
        Convert profile dictionary to searchable text
        
        Priority order:
        1. Core values (marriage, children, religion)
        2. Lifestyle (hobbies, work-life balance)
        3. Preferences (partner requirements)
        4. Other information
        """
        sections = []
        
        # High priority fields (most important for matching)
        high_priority = {
            '결혼_계획': '결혼 계획',
            'marriage_plan': '결혼 계획',
            '자녀_계획': '자녀 계획',
            'children_plan': '자녀 계획',
            '종교': '종교',
            'religion': '종교',
            '가치관': '가치관',
            'values': '가치관',
        }
        
        # Medium priority fields
        medium_priority = {
            '재정_관리': '재정 관리 방식',
            'finance_style': '재정 관리 방식',
            '부모_동거': '부모님 동거 계획',
            'parent_living': '부모님 동거 계획',
            '라이프스타일': '라이프스타일',
            'lifestyle': '라이프스타일',
            '취미': '취미',
            'hobbies': '취미',
        }
        
        # Process high priority
        for key, label in high_priority.items():
            if key in profile and profile[key]:
                sections.append(f"[중요] {label}: {profile[key]}")
        
        # Process medium priority
        for key, label in medium_priority.items():
            if key in profile and profile[key]:
                sections.append(f"{label}: {profile[key]}")
        
        # Process remaining fields
        processed_keys = set(high_priority.keys()) | set(medium_priority.keys())
        for key, value in profile.items():
            if key not in processed_keys and value and not key.startswith('_'):
                # Clean up key for display
                display_key = key.replace('_', ' ')
                sections.append(f"{display_key}: {value}")
        
        return " | ".join(sections)
    
    def generate_embedding(
        self,
        profile: Dict[str, Any],
        return_all: bool = False
    ) -> Dict[str, Any]:
        """
        Generate embeddings for a profile
        
        Args:
            profile: User profile dictionary
            return_all: If True, return dense, sparse, and colbert embeddings
                       If False, return only dense embedding
        
        Returns:
            {
                "dense": [float] * 1024,
                "sparse": {token: weight} (optional),
                "colbert": [[float]] (optional)
            }
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        text = self.create_profile_text(profile)
        
        embeddings = self.model.encode(
            [text],
            return_dense=True,
            return_sparse=return_all,
            return_colbert_vecs=return_all
        )
        
        result = {
            "dense": embeddings['dense_vecs'][0].tolist()
        }
        
        if return_all:
            # Convert sparse weights to serializable format
            sparse_weights = embeddings['lexical_weights'][0]
            result["sparse"] = {
                str(k): float(v) for k, v in sparse_weights.items()
            }
            result["colbert"] = embeddings['colbert_vecs'][0].tolist()
        
        return result
    
    def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two dense embeddings
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Normalize
        vec1 = vec1 / np.linalg.norm(vec1)
        vec2 = vec2 / np.linalg.norm(vec2)
        
        # Cosine similarity
        similarity = np.dot(vec1, vec2)
        
        # Convert to 0-100 scale
        return float((similarity + 1) / 2 * 100)
    
    def find_matches(
        self,
        query_profile: Dict[str, Any],
        candidate_profiles: List[Dict[str, Any]],
        top_k: int = 20,
        weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find most compatible profiles using hybrid search
        
        Args:
            query_profile: The user's profile
            candidate_profiles: List of potential matches
            top_k: Number of results to return
            weights: Custom weights for {dense, sparse, colbert}
                    Default: {dense: 0.4, sparse: 0.2, colbert: 0.4}
        
        Returns:
            List of {index, score, breakdown} sorted by score descending
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        if weights is None:
            weights = {
                'dense': 0.4,
                'sparse': 0.2,
                'colbert': 0.4
            }
        
        # Create texts
        query_text = self.create_profile_text(query_profile)
        candidate_texts = [self.create_profile_text(p) for p in candidate_profiles]
        
        # Encode all at once for efficiency
        query_emb = self.model.encode(
            [query_text],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=True
        )
        
        candidate_embs = self.model.encode(
            candidate_texts,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=True
        )
        
        # Calculate hybrid scores
        scores_dense = self._compute_dense_scores(
            query_emb['dense_vecs'][0],
            candidate_embs['dense_vecs']
        )
        
        scores_sparse = self._compute_sparse_scores(
            query_emb['lexical_weights'][0],
            candidate_embs['lexical_weights']
        )
        
        scores_colbert = self._compute_colbert_scores(
            query_emb['colbert_vecs'][0],
            candidate_embs['colbert_vecs']
        )
        
        # Combine scores
        final_scores = (
            weights['dense'] * scores_dense +
            weights['sparse'] * scores_sparse +
            weights['colbert'] * scores_colbert
        )
        
        # Get top K
        top_indices = np.argsort(final_scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                "index": int(idx),
                "score": float(final_scores[idx] * 100),  # Convert to percentage
                "breakdown": {
                    "dense": float(scores_dense[idx] * 100),
                    "sparse": float(scores_sparse[idx] * 100),
                    "colbert": float(scores_colbert[idx] * 100)
                }
            })
        
        return results
    
    def _compute_dense_scores(
        self,
        query_vec: np.ndarray,
        candidate_vecs: np.ndarray
    ) -> np.ndarray:
        """Compute dense similarity scores"""
        # Normalize
        query_norm = query_vec / np.linalg.norm(query_vec)
        cand_norms = candidate_vecs / np.linalg.norm(
            candidate_vecs, axis=1, keepdims=True
        )
        
        # Dot product (cosine similarity for normalized vectors)
        scores = np.dot(cand_norms, query_norm)
        
        # Normalize to 0-1
        return (scores + 1) / 2
    
    def _compute_sparse_scores(
        self,
        query_weights: Dict,
        candidate_weights: List[Dict]
    ) -> np.ndarray:
        """Compute sparse (lexical) similarity scores"""
        scores = []
        
        query_tokens = set(query_weights.keys())
        
        for cand_weights in candidate_weights:
            # Compute overlap
            cand_tokens = set(cand_weights.keys())
            common_tokens = query_tokens & cand_tokens
            
            if not common_tokens:
                scores.append(0.0)
                continue
            
            # Weighted Jaccard-like score
            score = sum(
                min(query_weights[t], cand_weights[t])
                for t in common_tokens
            )
            
            total = sum(query_weights.values()) + sum(cand_weights.values())
            scores.append(score / total * 2 if total > 0 else 0)
        
        return np.array(scores)
    
    def _compute_colbert_scores(
        self,
        query_vecs: np.ndarray,
        candidate_vecs: List[np.ndarray]
    ) -> np.ndarray:
        """Compute ColBERT MaxSim scores"""
        scores = []
        
        for cand_vecs in candidate_vecs:
            # MaxSim: for each query token, find max similarity with any doc token
            sim_matrix = np.dot(query_vecs, cand_vecs.T)
            
            # Max over document tokens, then average over query tokens
            max_sims = np.max(sim_matrix, axis=1)
            score = np.mean(max_sims)
            
            # Normalize to 0-1
            scores.append((score + 1) / 2)
        
        return np.array(scores)
    
    def get_embedding_for_storage(self, profile: Dict[str, Any]) -> List[float]:
        """
        Get dense embedding suitable for pgvector storage
        
        This is used when storing profiles in Supabase
        """
        embedding = self.generate_embedding(profile, return_all=False)
        return embedding['dense']
