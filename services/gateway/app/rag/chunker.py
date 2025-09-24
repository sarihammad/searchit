"""
Semantic chunker for text processing
"""

from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

class SemanticChunker:
    """Semantic chunker with heading awareness and overlap"""
    
    def __init__(
        self,
        min_tokens: int = 250,
        max_tokens: int = 500,
        overlap: float = 0.15,
        merge_short_below: int = 120
    ):
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap = overlap
        self.merge_short_below = merge_short_below
        
        # Regex patterns
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        self.section_pattern = re.compile(r'^##+\s+(.+)$', re.MULTILINE)
    
    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk text into semantic segments with overlap
        """
        if not text.strip():
            return []
        
        logger.info("Starting text chunking", extra={
            "text_length": len(text),
            "min_tokens": self.min_tokens,
            "max_tokens": self.max_tokens
        })
        
        # Split into sections based on headings
        sections = self._split_into_sections(text)
        
        # Process each section
        chunks = []
        for section_text, section_title in sections:
            section_chunks = self._chunk_section(section_text, section_title)
            chunks.extend(section_chunks)
        
        # Merge very short chunks
        chunks = self._merge_short_chunks(chunks)
        
        # Add overlap between chunks
        chunks = self._add_overlap(chunks)
        
        logger.info("Chunking completed", extra={
            "chunks_count": len(chunks)
        })
        
        return chunks
    
    def _split_into_sections(self, text: str) -> List[tuple]:
        """Split text into sections based on headings"""
        sections = []
        
        # Find all heading positions
        headings = list(self.heading_pattern.finditer(text))
        
        if not headings:
            # No headings found, treat entire text as one section
            return [(text, "")]
        
        # Extract sections between headings
        for i, heading in enumerate(headings):
            start = heading.start()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            
            section_text = text[start:end].strip()
            section_title = heading.group(2).strip()
            
            if section_text:
                sections.append((section_text, section_title))
        
        return sections
    
    def _chunk_section(self, section_text: str, section_title: str) -> List[Dict[str, Any]]:
        """Chunk a single section into smaller pieces"""
        chunks = []
        
        # Split by sentences for better semantic boundaries
        sentences = re.split(r'(?<=[.!?])\s+', section_text)
        
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)
            
            # If adding this sentence would exceed max_tokens, start new chunk
            if current_tokens + sentence_tokens > self.max_tokens and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "tokens": current_tokens,
                    "section": section_title
                })
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                current_tokens += sentence_tokens
        
        # Add final chunk if it has content
        if current_chunk.strip() and current_tokens >= self.min_tokens // 2:
            chunks.append({
                "text": current_chunk.strip(),
                "tokens": current_tokens,
                "section": section_title
            })
        
        return chunks
    
    def _merge_short_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge chunks that are too short"""
        if len(chunks) <= 1:
            return chunks
        
        merged_chunks = []
        i = 0
        
        while i < len(chunks):
            current_chunk = chunks[i]
            
            # If current chunk is too short, try to merge with next
            if current_chunk["tokens"] < self.merge_short_below and i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                
                # Merge if combined size is reasonable
                combined_tokens = current_chunk["tokens"] + next_chunk["tokens"]
                if combined_tokens <= self.max_tokens * 1.5:  # Allow some flexibility
                    merged_text = current_chunk["text"] + " " + next_chunk["text"]
                    merged_chunk = {
                        "text": merged_text.strip(),
                        "tokens": combined_tokens,
                        "section": current_chunk.get("section", "")
                    }
                    merged_chunks.append(merged_chunk)
                    i += 2  # Skip next chunk as it's been merged
                    continue
            
            merged_chunks.append(current_chunk)
            i += 1
        
        return merged_chunks
    
    def _add_overlap(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add overlap between consecutive chunks"""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            text = chunk["text"]
            
            # Add overlap from previous chunk
            if i > 0:
                prev_chunk = chunks[i - 1]
                prev_text = prev_chunk["text"]
                
                # Get last portion of previous chunk for overlap
                prev_words = prev_text.split()
                overlap_size = int(len(prev_words) * self.overlap)
                
                if overlap_size > 0:
                    overlap_text = " ".join(prev_words[-overlap_size:])
                    text = overlap_text + " " + text
            
            # Add overlap to next chunk
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                next_text = next_chunk["text"]
                
                # Get first portion of current chunk for next chunk's overlap
                current_words = text.split()
                overlap_size = int(len(current_words) * self.overlap)
                
                if overlap_size > 0:
                    # Store overlap info for next iteration
                    pass
            
            overlapped_chunks.append({
                "text": text.strip(),
                "tokens": self._count_tokens(text),
                "section": chunk.get("section", "")
            })
        
        return overlapped_chunks
    
    def _count_tokens(self, text: str) -> int:
        """
        Simple token counting (word-based)
        In production, would use proper tokenizer
        """
        # Remove extra whitespace and split by words
        words = text.strip().split()
        return len(words)
