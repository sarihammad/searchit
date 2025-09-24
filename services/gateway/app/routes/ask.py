"""
Ask routes for grounded question answering
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import time
from collections import defaultdict, deque

from app.rag.retriever import HybridRetriever
from app.rag.reranker import CEReranker
from app.rag.generator import AnswerGenerator

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple in-memory rate limiter (token bucket)
class RateLimiter:
    def __init__(self, rate: int = 10, window: int = 60):
        self.rate = rate  # requests per window
        self.window = window  # seconds
        self.requests = defaultdict(lambda: deque())
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        client_requests = self.requests[client_ip]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] <= now - self.window:
            client_requests.popleft()
        
        # Check if under rate limit
        if len(client_requests) < self.rate:
            client_requests.append(now)
            return True
        return False

# Global rate limiter (10 requests per minute per IP)
rate_limiter = RateLimiter(rate=10, window=60)

class AskRequest(BaseModel):
    question: str
    top_k: int = 8
    ground: bool = True

class AskResponse(BaseModel):
    answer: Optional[str] = None
    citations: List[Dict[str, Any]] = []
    evidence_coverage: float = 0.0
    abstained: bool = False
    reason: Optional[str] = None

@router.post("/", response_model=AskResponse)
async def ask_question(request: AskRequest, http_request: Request) -> AskResponse:
    """
    Grounded question answering endpoint with retrieval, reranking, and generation
    """
    try:
        # Rate limiting
        client_ip = http_request.client.host
        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
        
        logger.info("Ask request", extra={
            "question": request.question,
            "top_k": request.top_k,
            "ground": request.ground
        })
        
        # Initialize components
        retriever = HybridRetriever()
        reranker = CEReranker()
        generator = AnswerGenerator()
        
        # Retrieve relevant chunks
        search_results = await retriever.search(
            query=request.question,
            top_k=100,  # Get more for reranking
            with_highlights=False
        )
        
        if not search_results.get("results"):
            logger.info("No results found for question", extra={
                "question": request.question
            })
            return AskResponse(
                abstained=True,
                reason="no_results"
            )
        
        # Rerank results
        candidates = [r["text"] for r in search_results["results"]]
        reranked = reranker.rerank(
            query=request.question,
            candidates=candidates,
            top_k=request.top_k
        )
        
        # Generate answer
        answer_result = generator.generate(
            question=request.question,
            contexts=reranked,
            force_citations=request.ground
        )
        
        logger.info("Ask completed", extra={
            "question": request.question,
            "abstained": answer_result.get("abstained", False),
            "reason": answer_result.get("reason"),
            "citations_count": len(answer_result.get("citations", []))
        })
        
        return AskResponse(**answer_result)
        
    except Exception as e:
        logger.error("Ask failed", extra={
            "question": request.question,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Ask failed: {str(e)}")
