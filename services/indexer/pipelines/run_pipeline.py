"""
Main pipeline runner for SearchIt indexer
"""

import asyncio
import logging
import json
import argparse
import sys
from typing import List, Dict, Any
from datetime import datetime

from ingest_web import WebIngester
from ingest_pdf import PDFIngester
from clean_normalize import TextCleaner
from embed import EmbeddingGenerator
from push_to_stores import StorePusher

# Import chunker from gateway
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'gateway', 'app'))
from rag.chunker import SemanticChunker

logger = logging.getLogger(__name__)

class IndexerPipeline:
    """Main indexing pipeline orchestrator"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        # Initialize components
        self.web_ingester = None
        self.pdf_ingester = PDFIngester()
        self.cleaner = TextCleaner()
        self.chunker = SemanticChunker()
        self.embedder = EmbeddingGenerator()
        self.store_pusher = None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load pipeline configuration"""
        default_config = {
            "chunking": {
                "min_tokens": 250,
                "max_tokens": 500,
                "overlap": 0.15
            },
            "embedding": {
                "model_name": "intfloat/e5-base",
                "batch_size": 32
            },
            "stores": {
                "opensearch": True,
                "qdrant": True,
                "postgres": True,
                "s3": False
            },
            "logging": {
                "level": "INFO",
                "format": "json"
            }
        }
        
        if config_path:
            try:
                import yaml
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    default_config.update(config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def setup_logging(self):
        """Setup logging configuration"""
        level = getattr(logging, self.config["logging"]["level"].upper())
        
        if self.config["logging"]["format"] == "json":
            from gateway.app.core.logging import setup_logging
            setup_logging(self.config["logging"]["level"])
        else:
            logging.basicConfig(
                level=level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    async def ingest_from_source(self, source: str, source_type: str) -> List[Dict[str, Any]]:
        """Ingest documents from various sources"""
        logger.info(f"Ingesting from {source_type}: {source}")
        
        documents = []
        
        if source_type == "web":
            async with WebIngester() as ingester:
                if source.startswith("http"):
                    # Single URL
                    doc = await ingester.fetch_url(source)
                    if doc:
                        documents.append(doc)
                else:
                    # File with URLs
                    with open(source, 'r') as f:
                        urls = [line.strip() for line in f if line.strip()]
                    
                    for url in urls:
                        doc = await ingester.fetch_url(url)
                        if doc:
                            documents.append(doc)
        
        elif source_type == "pdf":
            if os.path.isfile(source):
                # Single PDF file
                doc = self.pdf_ingester.ingest_pdf(source)
                if doc:
                    documents.append(doc)
            else:
                # Directory of PDF files
                import glob
                pdf_files = glob.glob(os.path.join(source, "**/*.pdf"), recursive=True)
                
                for pdf_file in pdf_files:
                    doc = self.pdf_ingester.ingest_pdf(pdf_file)
                    if doc:
                        documents.append(doc)
        
        elif source_type == "jsonl":
            # JSONL file
            with open(source, 'r') as f:
                for line in f:
                    if line.strip():
                        doc = json.loads(line)
                        documents.append(doc)
        
        elif source_type == "json":
            # JSON file
            with open(source, 'r') as f:
                documents = json.load(f)
        
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        logger.info(f"Ingested {len(documents)} documents from {source_type}")
        return documents
    
    def clean_and_normalize(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean and normalize document text"""
        logger.info(f"Cleaning and normalizing {len(documents)} documents")
        
        for doc in documents:
            if "text" in doc:
                # Clean the text
                cleaned_result = self.cleaner.clean_text(doc["text"])
                doc["text"] = cleaned_result
                
                # Detect language if not specified
                if "lang" not in doc or not doc["lang"]:
                    doc["lang"] = self.cleaner.detect_language(doc["text"])
                
                # Extract sections
                sections = self.cleaner.extract_sections(doc["text"])
                doc["sections"] = sections
        
        return documents
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Chunk documents into smaller pieces"""
        logger.info(f"Chunking {len(documents)} documents")
        
        chunked_documents = []
        
        for doc in documents:
            if "chunks" in doc:
                # Document already has chunks
                chunked_documents.append(doc)
                continue
            
            text = doc.get("text", "")
            if not text.strip():
                logger.warning(f"Document {doc.get('doc_id', 'unknown')} has no text to chunk")
                continue
            
            # Chunk the text
            chunks = self.chunker.chunk(text)
            
            # Add chunk metadata
            doc_chunks = []
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc['doc_id']}_chunk_{i+1}"
                
                doc_chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk["text"],
                    "section": chunk.get("section", ""),
                    "tokens": chunk["tokens"]
                })
            
            doc["chunks"] = doc_chunks
            chunked_documents.append(doc)
        
        return chunked_documents
    
    def generate_embeddings(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings for documents and chunks"""
        logger.info(f"Generating embeddings for {len(documents)} documents")
        
        # Process documents with embeddings
        documents_with_embeddings = self.embedder.process_documents(documents)
        
        return documents_with_embeddings
    
    async def push_to_stores(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Push documents to search stores"""
        logger.info(f"Pushing {len(documents)} documents to stores")
        
        if not self.store_pusher:
            self.store_pusher = StorePusher()
        
        results = await self.store_pusher.push_documents(documents)
        return results
    
    async def run_full_pipeline(
        self, 
        source: str, 
        source_type: str
    ) -> Dict[str, Any]:
        """Run the complete indexing pipeline"""
        logger.info(f"Starting full pipeline for {source_type}: {source}")
        
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Ingest documents
            documents = await self.ingest_from_source(source, source_type)
            
            if not documents:
                logger.warning("No documents ingested")
                return {"status": "warning", "message": "No documents ingested"}
            
            # Step 2: Clean and normalize
            documents = self.clean_and_normalize(documents)
            
            # Step 3: Chunk documents
            documents = self.chunk_documents(documents)
            
            # Step 4: Generate embeddings
            documents = self.generate_embeddings(documents)
            
            # Step 5: Push to stores
            push_results = await self.push_to_stores(documents)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Pipeline completed successfully in {duration:.2f} seconds")
            
            return {
                "status": "success",
                "duration_seconds": duration,
                "documents_processed": len(documents),
                "push_results": push_results,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        finally:
            # Cleanup
            if self.store_pusher:
                await self.store_pusher.close()

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="SearchIt Indexing Pipeline")
    parser.add_argument("--source", required=True, help="Source file, URL, or directory")
    parser.add_argument("--type", required=True, choices=["web", "pdf", "jsonl", "json"], 
                       help="Source type")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--output", help="Output file for results")
    
    args = parser.parse_args()
    
    # Create pipeline
    pipeline = IndexerPipeline(args.config)
    
    # Run pipeline
    results = await pipeline.run_full_pipeline(args.source, args.type)
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    else:
        print(json.dumps(results, indent=2))
    
    # Exit with appropriate code
    if results["status"] == "success":
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
