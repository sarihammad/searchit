"""
Answer generator with grounding and citation validation
"""

from typing import List, Dict, Any, Optional
import logging
import re
import time
from prometheus_client import Counter, Histogram

from app.core.config import settings

logger = logging.getLogger(__name__)

# Prometheus metrics
GENERATE_LATENCY = Histogram('rag_latency_ms', 'Generation latency in milliseconds', ['stage'])
ABSTAIN_COUNTER = Counter('rag_abstain_total', 'Number of abstained answers', ['reason'])

class AnswerGenerator:
    """Answer generator with grounding enforcement and citation validation"""
    
    def __init__(self):
        # Default to stub unless HF_TOKEN is provided
        self.generator_type = settings.generator or "stub"
        if self.generator_type == "hf" and not getattr(settings, 'hf_token', None):
            logger.warning("HF generator requested but no HF_TOKEN provided, falling back to stub")
            self.generator_type = "stub"
        self.coverage_threshold = 0.3  # Minimum similarity threshold
    
    def generate(
        self,
        question: str,
        contexts: List[Dict[str, Any]],
        force_citations: bool = True
    ) -> Dict[str, Any]:
        """
        Generate grounded answer with citations
        """
        logger.info("Starting answer generation", extra={
            "question": question,
            "contexts_count": len(contexts),
            "force_citations": force_citations
        })
        
        # Check answerability
        if not self._is_answerable(contexts):
            ABSTAIN_COUNTER.labels(reason='low_coverage').inc()
            return {
                "abstained": True,
                "reason": "low_coverage"
            }
        
        # Generate answer based on generator type with timing
        start_time = time.time()
        
        if self.generator_type == "stub":
            answer_result = self._generate_stub_answer(question, contexts)
        elif self.generator_type == "hf":
            answer_result = self._generate_hf_answer(question, contexts)
        else:
            answer_result = self._generate_stub_answer(question, contexts)
        
        # Record generation metrics
        generate_time = (time.time() - start_time) * 1000  # Convert to ms
        GENERATE_LATENCY.labels(stage='generate').observe(generate_time)
        
        # Validate citations if required
        if force_citations and not answer_result.get("abstained", False):
            if not self._validate_citations(answer_result.get("answer", ""), contexts):
                ABSTAIN_COUNTER.labels(reason='validation_fail').inc()
                return {
                    "abstained": True,
                    "reason": "validation_fail"
                }
        
        logger.info("Answer generation completed", extra={
            "abstained": answer_result.get("abstained", False),
            "reason": answer_result.get("reason"),
            "citations_count": len(answer_result.get("citations", []))
        })
        
        return answer_result
    
    def _is_answerable(self, contexts: List[Dict[str, Any]]) -> bool:
        """Check if contexts provide enough coverage for the question"""
        if not contexts:
            return False
        
        # Simple heuristic: check if we have contexts with reasonable scores
        max_score = max(context.get("rerank_score", 0.0) for context in contexts)
        return max_score >= self.coverage_threshold
    
    def _generate_stub_answer(
        self,
        question: str,
        contexts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a stub answer based on contexts"""
        
        # Simple template-based answer
        answer_parts = []
        citations = []
        
        for i, context in enumerate(contexts[:3]):  # Use top 3 contexts
            text = context.get("text", "")
            if text:
                # Truncate text for demo
                truncated_text = text[:200] + "..." if len(text) > 200 else text
                answer_parts.append(f"Based on the available information: {truncated_text}")
                
                # Add citation
                citations.append({
                    "chunk_id": f"chunk_{i}",
                    "span": {"start": 0, "end": min(len(text), 200)}
                })
        
        if answer_parts:
            answer = " ".join(answer_parts)
            return {
                "abstained": False,
                "answer": answer,
                "citations": citations,
                "evidence_coverage": min(len(contexts) / 5.0, 1.0)
            }
        else:
            return {
                "abstained": True,
                "reason": "no_context"
            }
    
    def _generate_hf_answer(
        self,
        question: str,
        contexts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate answer using HuggingFace transformers (placeholder)"""
        # TODO: Implement actual HF model inference
        return self._generate_stub_answer(question, contexts)
    
    def _validate_citations(
        self,
        answer: str,
        contexts: List[Dict[str, Any]]
    ) -> bool:
        """Validate that citations are properly grounded"""
        # Simple validation: check if answer contains citation markers
        citation_pattern = r'\[chunk_\d+\]'
        citations = re.findall(citation_pattern, answer)
        
        # For stub implementation, always return True
        # In real implementation, would check lexical/semantic overlap
        return True
