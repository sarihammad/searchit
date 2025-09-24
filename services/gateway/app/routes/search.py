"""
Search routes for hybrid BM25 + vector search
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional, Dict, Any
import logging

from app.rag.retriever import HybridRetriever

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
async def search(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(10, ge=1, le=100, description="Number of results to return"),
    filters: Optional[str] = Query(None, description="Filters in format lang:en,tags:python"),
    with_highlights: bool = Query(True, description="Include text highlights")
) -> Dict[str, Any]:
    """
    Hybrid search endpoint combining BM25 and vector search with RRF fusion
    """
    try:
        logger.info("Search request", extra={
            "query": q,
            "top_k": top_k,
            "filters": filters,
            "with_highlights": with_highlights
        })
        
        # Initialize retriever
        retriever = HybridRetriever()
        
        # Parse filters
        filter_dict = {}
        if filters:
            for filter_item in filters.split(","):
                if ":" in filter_item:
                    key, value = filter_item.split(":", 1)
                    filter_dict[key.strip()] = value.strip()
        
        # Perform search
        results = await retriever.search(
            query=q,
            top_k=top_k,
            filters=filter_dict,
            with_highlights=with_highlights
        )
        
        logger.info("Search completed", extra={
            "query": q,
            "result_count": len(results.get("results", [])),
            "facets": results.get("facets", {})
        })
        
        return results
        
    except Exception as e:
        logger.error("Search failed", extra={
            "query": q,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
