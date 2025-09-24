"""
Hybrid retriever combining BM25 and dense vector search with RRF fusion
"""

from typing import List, Dict, Any, Optional
import logging
import asyncio
import time
from prometheus_client import Counter, Histogram

from app.adapters.opensearch import OpenSearchAdapter
from app.adapters.qdrant import QdrantAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)

# Prometheus metrics
RETRIEVAL_LATENCY = Histogram('rag_latency_ms', 'Retrieval latency in milliseconds', ['stage'])
RETRIEVED_SOURCES = Counter('search_retrieved_sources_total', 'Documents retrieved by source', ['source'])

class HybridRetriever:
    """Hybrid retriever using RRF fusion of BM25 and dense search"""
    
    def __init__(self):
        self.opensearch = OpenSearchAdapter()
        self.qdrant = QdrantAdapter()
        self.rrf_k = settings.rrf_k
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, str]] = None,
        with_highlights: bool = True
    ) -> Dict[str, Any]:
        """
        Perform hybrid search with RRF fusion
        """
        logger.info("Starting hybrid search", extra={
            "query": query,
            "top_k": top_k,
            "filters": filters,
            "with_highlights": with_highlights
        })
        
        # Run BM25 and dense search in parallel with timing
        start_time = time.time()
        
        bm25_task = self.opensearch.search_bm25(query, top_k * 2, filters)
        dense_task = self.qdrant.search_dense(query, top_k * 2, filters)
        
        bm25_results, dense_results = await asyncio.gather(bm25_task, dense_task)
        
        # Record metrics
        retrieval_time = (time.time() - start_time) * 1000  # Convert to ms
        RETRIEVAL_LATENCY.labels(stage='retrieve').observe(retrieval_time)
        RETRIEVED_SOURCES.labels(source='bm25').inc(len(bm25_results))
        RETRIEVED_SOURCES.labels(source='dense').inc(len(dense_results))
        
        # Fuse results using RRF
        fused_results = self._rrf_fuse(bm25_results, dense_results, top_k)
        
        # Get facets from OpenSearch
        facets = await self.opensearch.get_facets(filters)
        
        return {
            "query": query,
            "results": fused_results,
            "facets": facets,
            "total": len(fused_results)
        }
    
    def _rrf_fuse(
        self,
        bm25_results: List[Dict[str, Any]],
        dense_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Fuse BM25 and dense results using Reciprocal Rank Fusion
        """
        scores = {}
        
        # Add BM25 scores
        for rank, result in enumerate(bm25_results, 1):
            doc_id = result["doc_id"]
            chunk_id = result["chunk_id"]
            key = f"{doc_id}:{chunk_id}"
            
            scores[key] = scores.get(key, {
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "title": result.get("title", ""),
                "text": result.get("text", ""),
                "url": result.get("url", ""),
                "section": result.get("section", ""),
                "lang": result.get("lang", ""),
                "tags": result.get("tags", []),
                "score": 0.0,
                "bm25_rank": rank,
                "dense_rank": None,
                "bm25_score": result.get("score", 0.0),
                "dense_score": 0.0
            })
            
            scores[key]["score"] += 1.0 / (self.rrf_k + rank)
        
        # Add dense scores
        for rank, result in enumerate(dense_results, 1):
            doc_id = result["doc_id"]
            chunk_id = result["chunk_id"]
            key = f"{doc_id}:{chunk_id}"
            
            if key in scores:
                scores[key]["score"] += 1.0 / (self.rrf_k + rank)
                scores[key]["dense_rank"] = rank
                scores[key]["dense_score"] = result.get("score", 0.0)
            else:
                scores[key] = {
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "title": result.get("title", ""),
                    "text": result.get("text", ""),
                    "url": result.get("url", ""),
                    "section": result.get("section", ""),
                    "lang": result.get("lang", ""),
                    "tags": result.get("tags", []),
                    "score": 1.0 / (self.rrf_k + rank),
                    "bm25_rank": None,
                    "dense_rank": rank,
                    "bm25_score": 0.0,
                    "dense_score": result.get("score", 0.0)
                }
        
        # Sort by fused score and return top_k
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )[:top_k]
        
        logger.info("RRF fusion completed", extra={
            "bm25_results": len(bm25_results),
            "dense_results": len(dense_results),
            "fused_results": len(sorted_results)
        })
        
        return sorted_results
