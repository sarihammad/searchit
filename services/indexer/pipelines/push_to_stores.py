"""
Pipeline to push processed documents to search stores
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import yaml

# Import adapters
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'gateway', 'app'))

from adapters.opensearch import OpenSearchAdapter
from adapters.qdrant import QdrantAdapter
from adapters.postgres import PostgresAdapter
from adapters.s3 import S3Adapter

logger = logging.getLogger(__name__)

class StorePusher:
    """Push processed documents to search stores"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.opensearch = OpenSearchAdapter()
        self.qdrant = QdrantAdapter()
        self.postgres = PostgresAdapter()
        self.s3 = S3Adapter()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        default_config = {
            "batch_size": 100,
            "max_retries": 3,
            "retry_delay": 1.0,
            "stores": {
                "opensearch": True,
                "qdrant": True,
                "postgres": True,
                "s3": False
            },
            "indexing": {
                "refresh_interval": "1s",
                "wait_for_completion": True
            }
        }
        
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    default_config.update(config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    async def push_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Push documents to all configured stores"""
        logger.info(f"Pushing {len(documents)} documents to stores")
        
        results = {
            "total_documents": len(documents),
            "opensearch": {"success": 0, "failed": 0},
            "qdrant": {"success": 0, "failed": 0},
            "postgres": {"success": 0, "failed": 0},
            "s3": {"success": 0, "failed": 0}
        }
        
        try:
            # Process documents in batches
            batch_size = self.config["batch_size"]
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")
                
                # Push to each store
                if self.config["stores"]["opensearch"]:
                    opensearch_result = await self._push_to_opensearch(batch)
                    results["opensearch"]["success"] += opensearch_result["success"]
                    results["opensearch"]["failed"] += opensearch_result["failed"]
                
                if self.config["stores"]["qdrant"]:
                    qdrant_result = await self._push_to_qdrant(batch)
                    results["qdrant"]["success"] += qdrant_result["success"]
                    results["qdrant"]["failed"] += qdrant_result["failed"]
                
                if self.config["stores"]["postgres"]:
                    postgres_result = await self._push_to_postgres(batch)
                    results["postgres"]["success"] += postgres_result["success"]
                    results["postgres"]["failed"] += postgres_result["failed"]
                
                if self.config["stores"]["s3"]:
                    s3_result = await self._push_to_s3(batch)
                    results["s3"]["success"] += s3_result["success"]
                    results["s3"]["failed"] += s3_result["failed"]
            
            logger.info("Document pushing completed", extra=results)
            return results
            
        except Exception as e:
            logger.error(f"Failed to push documents: {e}")
            raise
    
    async def _push_to_opensearch(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """Push documents to OpenSearch"""
        result = {"success": 0, "failed": 0}
        
        try:
            # Ensure index exists with proper mapping
            mapping_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'opensearch.json')
            await self.opensearch.create_index_if_missing(mapping_path=mapping_path)
            
            # Prepare documents for OpenSearch
            opensearch_docs = []
            
            for doc in documents:
                if "chunks" in doc:
                    # Document has chunks - index each chunk
                    for chunk in doc["chunks"]:
                        chunk_doc = {
                            "doc_id": doc["doc_id"],
                            "chunk_id": chunk["chunk_id"],
                            "title": doc.get("title", ""),
                            "text": chunk["text"],
                            "url": doc.get("url", ""),
                            "section": chunk.get("section", ""),
                            "lang": doc.get("lang", "en"),
                            "tags": doc.get("tags", []),
                            "tokens": chunk.get("tokens", 0),
                            "created_at": datetime.utcnow().isoformat(),
                            "embedding": chunk.get("embedding", [])
                        }
                        opensearch_docs.append(chunk_doc)
                else:
                    # Document without chunks - index as single document
                    doc_doc = {
                        "doc_id": doc["doc_id"],
                        "chunk_id": doc["doc_id"],  # Use doc_id as chunk_id
                        "title": doc.get("title", ""),
                        "text": doc.get("text", ""),
                        "url": doc.get("url", ""),
                        "section": "",
                        "lang": doc.get("lang", "en"),
                        "tags": doc.get("tags", []),
                        "tokens": len(doc.get("text", "").split()),
                        "created_at": datetime.utcnow().isoformat(),
                        "embedding": doc.get("embedding", [])
                    }
                    opensearch_docs.append(doc_doc)
            
            # Bulk index to OpenSearch
            if opensearch_docs:
                success = await self.opensearch.bulk_index(opensearch_docs)
                if success:
                    result["success"] = len(opensearch_docs)
                else:
                    result["failed"] = len(opensearch_docs)
            
        except Exception as e:
            logger.error(f"Failed to push to OpenSearch: {e}")
            result["failed"] = len(documents)
        
        return result
    
    async def _push_to_qdrant(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """Push documents to Qdrant"""
        result = {"success": 0, "failed": 0}
        
        try:
            # Ensure collection exists with proper dimension
            await self.qdrant.create_collection_if_missing(dim=768)
            
            # Prepare points for Qdrant
            qdrant_points = []
            
            for doc in documents:
                if "chunks" in doc:
                    # Document has chunks - create points for each chunk
                    for chunk in doc["chunks"]:
                        point = {
                            "chunk_id": chunk["chunk_id"],
                            "embedding": chunk.get("embedding", []),
                            "doc_id": doc["doc_id"],
                            "title": doc.get("title", ""),
                            "text": chunk["text"],
                            "url": doc.get("url", ""),
                            "section": chunk.get("section", ""),
                            "lang": doc.get("lang", "en"),
                            "tags": doc.get("tags", []),
                            "tokens": chunk.get("tokens", 0),
                            "created_at": datetime.utcnow().isoformat()
                        }
                        qdrant_points.append(point)
                else:
                    # Document without chunks - create single point
                    point = {
                        "chunk_id": doc["doc_id"],
                        "embedding": doc.get("embedding", []),
                        "doc_id": doc["doc_id"],
                        "title": doc.get("title", ""),
                        "text": doc.get("text", ""),
                        "url": doc.get("url", ""),
                        "section": "",
                        "lang": doc.get("lang", "en"),
                        "tags": doc.get("tags", []),
                        "tokens": len(doc.get("text", "").split()),
                        "created_at": datetime.utcnow().isoformat()
                    }
                    qdrant_points.append(point)
            
            # Upsert points to Qdrant
            if qdrant_points:
                success = await self.qdrant.upsert_points(qdrant_points)
                if success:
                    result["success"] = len(qdrant_points)
                else:
                    result["failed"] = len(qdrant_points)
            
        except Exception as e:
            logger.error(f"Failed to push to Qdrant: {e}")
            result["failed"] = len(documents)
        
        return result
    
    async def _push_to_postgres(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """Push documents to PostgreSQL"""
        result = {"success": 0, "failed": 0}
        
        try:
            for doc in documents:
                # Store document metadata
                doc_success = await self.postgres.store_document({
                    "doc_id": doc["doc_id"],
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "lang": doc.get("lang", "en"),
                    "tags": doc.get("tags", []),
                    "source": doc.get("source", "unknown")
                })
                
                if doc_success:
                    result["success"] += 1
                    
                    # Store chunks
                    if "chunks" in doc:
                        for chunk in doc["chunks"]:
                            chunk_success = await self.postgres.store_chunk({
                                "chunk_id": chunk["chunk_id"],
                                "doc_id": doc["doc_id"],
                                "text": chunk["text"],
                                "section": chunk.get("section", ""),
                                "tokens": chunk.get("tokens", 0)
                            })
                            
                            if not chunk_success:
                                result["failed"] += 1
                else:
                    result["failed"] += 1
            
        except Exception as e:
            logger.error(f"Failed to push to PostgreSQL: {e}")
            result["failed"] = len(documents)
        
        return result
    
    async def _push_to_s3(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """Push documents to S3/MinIO"""
        result = {"success": 0, "failed": 0}
        
        try:
            for doc in documents:
                # Upload document content to S3
                object_name = f"documents/{doc['doc_id']}.json"
                
                import json
                doc_json = json.dumps(doc, indent=2)
                
                from io import BytesIO
                doc_bytes = BytesIO(doc_json.encode('utf-8'))
                
                success = self.s3.upload_data(
                    object_name=object_name,
                    data=doc_bytes,
                    length=len(doc_json),
                    content_type="application/json"
                )
                
                if success:
                    result["success"] += 1
                else:
                    result["failed"] += 1
            
        except Exception as e:
            logger.error(f"Failed to push to S3: {e}")
            result["failed"] = len(documents)
        
        return result
    
    async def close(self):
        """Close all connections"""
        if hasattr(self.postgres, 'close'):
            await self.postgres.close()

async def push_documents_to_stores(
    documents: List[Dict[str, Any]], 
    config_path: str = None
) -> Dict[str, Any]:
    """Convenience function to push documents to stores"""
    pusher = StorePusher(config_path)
    try:
        return await pusher.push_documents(documents)
    finally:
        await pusher.close()

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python push_to_stores.py <input_file> [config_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    config_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Load documents
    with open(input_file, 'r') as f:
        if input_file.endswith('.jsonl'):
            documents = [json.loads(line) for line in f]
        else:
            documents = json.load(f)
    
    # Push to stores
    results = asyncio.run(push_documents_to_stores(documents, config_file))
    
    print("Push results:")
    print(json.dumps(results, indent=2))
