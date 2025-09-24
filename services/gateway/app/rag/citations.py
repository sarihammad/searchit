"""
Citation handling and validation utilities
"""

from typing import List, Dict, Any, Tuple
import re
import logging

logger = logging.getLogger(__name__)

class CitationManager:
    """Manages citations and span mapping"""
    
    def __init__(self):
        self.citation_pattern = r'\[chunk_(\d+):(\d+)\.\.(\d+)\]'
    
    def extract_citations(self, text: str) -> List[Dict[str, Any]]:
        """Extract citations from text with span information"""
        citations = []
        
        for match in re.finditer(self.citation_pattern, text):
            chunk_id = match.group(1)
            start = int(match.group(2))
            end = int(match.group(3))
            
            citations.append({
                "chunk_id": chunk_id,
                "span": {"start": start, "end": end}
            })
        
        return citations
    
    def format_citations(self, citations: List[Dict[str, Any]]) -> str:
        """Format citations for display"""
        if not citations:
            return ""
        
        formatted = []
        for i, citation in enumerate(citations, 1):
            chunk_id = citation.get("chunk_id", f"chunk_{i}")
            span = citation.get("span", {})
            start = span.get("start", 0)
            end = span.get("end", 0)
            
            formatted.append(f"[{i}] {chunk_id}:{start}-{end}")
        
        return "; ".join(formatted)
    
    def deduplicate_citations(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate citations"""
        seen = set()
        unique_citations = []
        
        for citation in citations:
            chunk_id = citation.get("chunk_id")
            span = citation.get("span", {})
            key = (chunk_id, span.get("start"), span.get("end"))
            
            if key not in seen:
                seen.add(key)
                unique_citations.append(citation)
        
        return unique_citations
    
    def validate_citation_spans(
        self,
        citation: Dict[str, Any],
        context_text: str
    ) -> bool:
        """Validate that citation spans are within context bounds"""
        span = citation.get("span", {})
        start = span.get("start", 0)
        end = span.get("end", 0)
        
        if start < 0 or end > len(context_text) or start >= end:
            return False
        
        return True
