"""
Cross-encoder reranker for improving search result relevance
"""

from typing import List, Dict, Any
import logging
import time
from sentence_transformers import CrossEncoder
from prometheus_client import Histogram

from app.core.config import settings

logger = logging.getLogger(__name__)

# Prometheus metrics
RERANK_LATENCY = Histogram('rag_latency_ms', 'Reranking latency in milliseconds', ['stage'])

class CEReranker:
    """Cross-encoder reranker using sentence-transformers"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.reranker_model
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the cross-encoder model"""
        try:
            logger.info("Loading cross-encoder model", extra={
                "model_name": self.model_name
            })
            self.model = CrossEncoder(self.model_name)
            logger.info("Cross-encoder model loaded successfully")
        except Exception as e:
            logger.error("Failed to load cross-encoder model", extra={
                "model_name": self.model_name,
                "error": str(e)
            })
            # Fallback to a simpler model or disable reranking
            self.model = None
    
    def rerank(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates using cross-encoder
        """
        if not self.model or not candidates:
            # Return original candidates if model not available
            return [{"text": text, "rerank_score": 0.0} for text in candidates[:top_k]]
        
        try:
            logger.info("Starting reranking", extra={
                "query": query,
                "candidates_count": len(candidates),
                "top_k": top_k
            })
            
            # Time the reranking
            start_time = time.time()
            
            # Prepare query-candidate pairs
            pairs = [(query, candidate) for candidate in candidates]
            
            # Get relevance scores
            scores = self.model.predict(pairs).tolist()
            
            # Record metrics
            rerank_time = (time.time() - start_time) * 1000  # Convert to ms
            RERANK_LATENCY.labels(stage='rerank').observe(rerank_time)
            
            # Combine candidates with scores and sort
            scored_candidates = [
                {"text": candidate, "rerank_score": score}
                for candidate, score in zip(candidates, scores)
            ]
            
            # Sort by rerank score (descending)
            reranked = sorted(
                scored_candidates,
                key=lambda x: x["rerank_score"],
                reverse=True
            )[:top_k]
            
            logger.info("Reranking completed", extra={
                "input_count": len(candidates),
                "output_count": len(reranked)
            })
            
            return reranked
            
        except Exception as e:
            logger.error("Reranking failed", extra={
                "error": str(e)
            })
            # Return original candidates as fallback
            return [{"text": text, "rerank_score": 0.0} for text in candidates[:top_k]]
