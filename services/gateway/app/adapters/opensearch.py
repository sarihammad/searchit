"""
OpenSearch adapter for BM25 search and metadata
"""

from typing import List, Dict, Any, Optional
import logging
import asyncio
from opensearchpy import OpenSearch, AsyncOpenSearch
from opensearchpy.helpers import bulk

from app.core.config import settings

logger = logging.getLogger(__name__)

class OpenSearchAdapter:
    """Adapter for OpenSearch operations"""
    
    def __init__(self):
        self.client = None
        self.index_name = "searchit_chunks"
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenSearch client"""
        try:
            self.client = AsyncOpenSearch(
                hosts=[settings.opensearch_url],
                http_auth=None,  # No auth for local dev
                use_ssl=False,
                verify_certs=False,
                ssl_assert_hostname=False,
                ssl_show_warn=False,
            )
            logger.info("OpenSearch client initialized", extra={
                "url": settings.opensearch_url
            })
        except Exception as e:
            logger.error("Failed to initialize OpenSearch client", extra={
                "error": str(e)
            })
    
    async def create_index_if_missing(self, mapping_path: str = None, index_name: str = None):
        """Create index with proper mapping if it doesn't exist"""
        if not self.client:
            return
        
        # Use provided index name or default
        target_index = index_name or self.index_name
        
        try:
            # Check if index exists
            exists = await self.client.indices.exists(index=target_index)
            
            if not exists:
                # Use provided mapping or default
                if mapping_path:
                    import json
                    with open(mapping_path, 'r') as f:
                        mapping = json.load(f)
                else:
                    mapping = {
                        "settings": {
                            "index": {
                                "knn": True,
                                "analysis": {
                                    "analyzer": {
                                        "default": {"type": "standard"}
                                    }
                                }
                            }
                        },
                        "mappings": {
                            "properties": {
                                "doc_id": {"type": "keyword"},
                                "chunk_id": {"type": "keyword"},
                                "title": {"type": "text"},
                                "text": {"type": "text"},
                                "url": {"type": "keyword"},
                                "section": {"type": "keyword"},
                                "lang": {"type": "keyword"},
                                "tags": {"type": "keyword"},
                                "embedding": {
                                    "type": "knn_vector",
                                    "dimension": 768,
                                    "method": {
                                        "name": "hnsw",
                                        "space_type": "cosinesimil",
                                        "engine": "nmslib"
                                    }
                                }
                            }
                        }
                    }
                
                await self.client.indices.create(index=target_index, body=mapping)
                logger.info("OpenSearch index created", extra={
                    "index_name": target_index
                })
            
        except Exception as e:
            logger.error("Failed to create OpenSearch index", extra={
                "index_name": target_index,
                "error": str(e)
            })
    
    async def search_bm25(
        self,
        query: str,
        size: int = 100,
        filters: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Perform BM25 search"""
        if not self.client:
            return []
        
        try:
            await self.create_index_if_missing()
            
            # Build query
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^2", "text"],
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                },
                "size": size,
                "_source": ["doc_id", "chunk_id", "title", "text", "url", "section", "lang", "tags"]
            }
            
            # Add filters
            if filters:
                filter_clauses = []
                for field, value in filters.items():
                    if field == "lang":
                        filter_clauses.append({"term": {"lang": value}})
                    elif field == "tags":
                        filter_clauses.append({"term": {"tags": value}})
                
                if filter_clauses:
                    search_body["query"]["bool"]["filter"] = filter_clauses
            
            # Execute search
            response = await self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                source["score"] = hit["_score"]
                results.append(source)
            
            logger.info("BM25 search completed", extra={
                "query": query,
                "results_count": len(results)
            })
            
            return results
            
        except Exception as e:
            logger.error("BM25 search failed", extra={
                "query": query,
                "error": str(e)
            })
            return []
    
    async def get_facets(self, filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Get facet aggregations"""
        if not self.client:
            return {}
        
        try:
            await self.create_index_if_missing()
            
            search_body = {
                "size": 0,
                "aggs": {
                    "lang": {
                        "terms": {"field": "lang", "size": 10}
                    },
                    "tags": {
                        "terms": {"field": "tags", "size": 20}
                    }
                }
            }
            
            # Add filters if provided
            if filters:
                search_body["query"] = {"bool": {"filter": []}}
                for field, value in filters.items():
                    if field == "lang":
                        search_body["query"]["bool"]["filter"].append({"term": {"lang": value}})
                    elif field == "tags":
                        search_body["query"]["bool"]["filter"].append({"term": {"tags": value}})
            
            response = await self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            facets = {}
            aggs = response.get("aggregations", {})
            
            for facet_name, agg_data in aggs.items():
                facets[facet_name] = {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in agg_data["buckets"]
                }
            
            return facets
            
        except Exception as e:
            logger.error("Failed to get facets", extra={
                "error": str(e)
            })
            return {}
    
    async def bulk_index(self, documents: List[Dict[str, Any]]) -> bool:
        """Bulk index documents"""
        if not self.client or not documents:
            return False
        
        try:
            await self.create_index_if_missing()
            
            actions = []
            for doc in documents:
                action = {
                    "_index": self.index_name,
                    "_id": doc.get("chunk_id"),
                    "_source": doc
                }
                actions.append(action)
            
            success, failed = await bulk(self.client, actions)
            
            logger.info("Bulk indexing completed", extra={
                "success_count": len(success),
                "failed_count": len(failed)
            })
            
            return len(failed) == 0
            
        except Exception as e:
            logger.error("Bulk indexing failed", extra={
                "error": str(e)
            })
            return False
