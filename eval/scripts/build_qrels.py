#!/usr/bin/env python3
"""
Build relevance judgments (qrels) for evaluation
"""

import argparse
import json
import logging
from typing import Dict, List, Tuple
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QrelsBuilder:
    """Build relevance judgments for evaluation"""
    
    def __init__(self):
        self.qrels = {}
    
    def add_judgment(self, query_id: str, doc_id: str, relevance: int):
        """Add a relevance judgment"""
        if query_id not in self.qrels:
            self.qrels[query_id] = []
        
        self.qrels[query_id].append((doc_id, relevance))
    
    def build_from_corpus(self, corpus_path: str, queries_path: str) -> Dict[str, List[Tuple[str, int]]]:
        """Build qrels from corpus and queries using heuristics"""
        logger.info("Building qrels from corpus using heuristics...")
        
        # Load corpus
        corpus = {}
        with open(corpus_path, 'r') as f:
            for line in f:
                if line.strip():
                    doc = json.loads(line)
                    corpus[doc['doc_id']] = doc
        
        # Load queries
        queries = {}
        with open(queries_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('query_id'):
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        query_id = parts[0]
                        query_text = parts[1]
                        queries[query_id] = query_text
        
        # Build qrels using simple heuristics
        qrels = {}
        
        for query_id, query_text in queries.items():
            qrels[query_id] = []
            
            # Simple keyword matching
            query_words = set(query_text.lower().split())
            
            for doc_id, doc in corpus.items():
                relevance = 0
                
                # Check title match
                title_words = set(doc.get('title', '').lower().split())
                title_overlap = len(query_words.intersection(title_words))
                
                # Check text match
                text_words = set(doc.get('text', '').lower().split())
                text_overlap = len(query_words.intersection(text_words))
                
                # Check tags match
                tags = doc.get('tags', [])
                tag_overlap = sum(1 for tag in tags if tag.lower() in query_text.lower())
                
                # Calculate relevance score
                if title_overlap >= 2:
                    relevance = 2  # Highly relevant
                elif title_overlap >= 1 or text_overlap >= 3:
                    relevance = 1  # Relevant
                elif text_overlap >= 1 or tag_overlap >= 1:
                    relevance = 1  # Somewhat relevant
                
                if relevance > 0:
                    qrels[query_id].append((doc_id, relevance))
        
        logger.info(f"Built qrels for {len(qrels)} queries")
        return qrels
    
    def save_qrels(self, qrels: Dict[str, List[Tuple[str, int]]], output_path: str):
        """Save qrels to TSV file"""
        with open(output_path, 'w') as f:
            f.write("query_id\tdoc_id\trelevance\n")
            
            for query_id, judgments in qrels.items():
                for doc_id, relevance in judgments:
                    f.write(f"{query_id}\t{doc_id}\t{relevance}\n")
        
        logger.info(f"Qrels saved to {output_path}")
    
    def load_qrels(self, qrels_path: str) -> Dict[str, List[Tuple[str, int]]]:
        """Load qrels from TSV file"""
        qrels = {}
        
        with open(qrels_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('query_id'):
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        query_id = parts[0]
                        doc_id = parts[1]
                        relevance = int(parts[2])
                        
                        if query_id not in qrels:
                            qrels[query_id] = []
                        qrels[query_id].append((doc_id, relevance))
        
        logger.info(f"Loaded qrels for {len(qrels)} queries")
        return qrels
    
    def validate_qrels(self, qrels: Dict[str, List[Tuple[str, int]]], corpus_path: str) -> Dict[str, int]:
        """Validate qrels against corpus"""
        # Load corpus
        corpus = {}
        with open(corpus_path, 'r') as f:
            for line in f:
                if line.strip():
                    doc = json.loads(line)
                    corpus[doc['doc_id']] = doc
        
        stats = {
            'total_queries': len(qrels),
            'total_judgments': 0,
            'relevant_judgments': 0,
            'highly_relevant_judgments': 0,
            'invalid_doc_ids': 0
        }
        
        for query_id, judgments in qrels.items():
            stats['total_judgments'] += len(judgments)
            
            for doc_id, relevance in judgments:
                if doc_id not in corpus:
                    stats['invalid_doc_ids'] += 1
                    logger.warning(f"Invalid doc_id in qrels: {doc_id}")
                
                if relevance > 0:
                    stats['relevant_judgments'] += 1
                
                if relevance >= 2:
                    stats['highly_relevant_judgments'] += 1
        
        return stats
    
    def print_stats(self, qrels: Dict[str, List[Tuple[str, int]]]):
        """Print qrels statistics"""
        total_queries = len(qrels)
        total_judgments = sum(len(judgments) for judgments in qrels.values())
        relevant_judgments = sum(
            sum(1 for _, rel in judgments if rel > 0)
            for judgments in qrels.values()
        )
        highly_relevant_judgments = sum(
            sum(1 for _, rel in judgments if rel >= 2)
            for judgments in qrels.values()
        )
        
        print(f"Qrels Statistics:")
        print(f"  Total queries: {total_queries}")
        print(f"  Total judgments: {total_judgments}")
        print(f"  Relevant judgments: {relevant_judgments}")
        print(f"  Highly relevant judgments: {highly_relevant_judgments}")
        print(f"  Avg judgments per query: {total_judgments / total_queries:.2f}")
        print(f"  Avg relevant per query: {relevant_judgments / total_queries:.2f}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Build relevance judgments")
    parser.add_argument("--corpus", required=True, help="Corpus JSONL file")
    parser.add_argument("--queries", required=True, help="Queries TSV file")
    parser.add_argument("--output", required=True, help="Output qrels TSV file")
    parser.add_argument("--validate", action="store_true", help="Validate qrels")
    
    args = parser.parse_args()
    
    # Build qrels
    builder = QrelsBuilder()
    qrels = builder.build_from_corpus(args.corpus, args.queries)
    
    # Print statistics
    builder.print_stats(qrels)
    
    # Save qrels
    builder.save_qrels(qrels, args.output)
    
    # Validate if requested
    if args.validate:
        stats = builder.validate_qrels(qrels, args.corpus)
        print(f"Validation results:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    main()
