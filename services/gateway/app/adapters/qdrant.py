"""
Qdrant adapter for vector search operations
"""

from typing import List, Dict, Any, Optional
import logging
import asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

class QdrantAdapter:
    """Adapter for Qdrant vector operations"""
    
    def __init__(self):
        self.client = None
        self.collection_name = "searchit_chunks"
        self.vector_size = 768
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Qdrant client"""
        try:
            self.client = AsyncQdrantClient(url=settings.qdrant_url)
            logger.info("Qdrant client initialized", extra={
                "url": settings.qdrant_url
            })
        except Exception as e:
            logger.error("Failed to initialize Qdrant client", extra={
                "error": str(e)
            })
    
    async def create_collection_if_missing(self, dim: int = None, collection_name: str = None):
        """Create collection if it doesn't exist"""
        if not self.client:
            return
        
        # Use provided parameters or defaults
        target_collection = collection_name or self.collection_name
        target_dim = dim or self.vector_size
        
        # Validate embedding dimension matches model
        expected_dim = getattr(settings, 'embed_dim', 768)
        if target_dim != expected_dim:
            logger.error(f"Embedding dimension mismatch: got {target_dim}, expected {expected_dim}")
            return
        
        try:
            # Check if collection exists
            collections = await self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if target_collection not in collection_names:
                await self.client.create_collection(
                    collection_name=target_collection,
                    vectors_config=VectorParams(
                        size=target_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info("Qdrant collection created", extra={
                    "collection_name": target_collection,
                    "vector_size": target_dim
                })
            
        except Exception as e:
            logger.error("Failed to create Qdrant collection", extra={
                "collection_name": target_collection,
                "error": str(e)
            })
    
    async def search_dense(
        self,
        query_vector: List[float],
        size: int = 100,
        filters: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Perform dense vector search"""
        if not self.client:
            return []
        
        try:
            await self.create_collection_if_missing()
            
            # Build filter conditions
            query_filter = None
            if filters:
                conditions = []
                for field, value in filters.items():
                    if field == "lang":
                        conditions.append(
                            FieldCondition(
                                key="lang",
                                match=MatchValue(value=value)
                            )
                        )
                    elif field == "tags":
                        conditions.append(
                            FieldCondition(
                                key="tags",
                                match=MatchValue(value=value)
                            )
                        )
                
                if conditions:
                    query_filter = Filter(must=conditions)
            
            # Perform search
            search_result = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=size,
                query_filter=query_filter,
                with_payload=True
            )
            
            results = []
            for hit in search_result:
                payload = hit.payload
                payload["score"] = hit.score
                results.append(payload)
            
            logger.info("Dense search completed", extra={
                "results_count": len(results)
            })
            
            return results
            
        except Exception as e:
            logger.error("Dense search failed", extra={
                "error": str(e)
            })
            return []
    
    async def upsert_points(self, points: List[Dict[str, Any]]) -> bool:
        """Upsert vector points to collection"""
        if not self.client or not points:
            return False
        
        try:
            await self.create_collection_if_missing()
            
            # Convert to Qdrant points
            qdrant_points = []
            for point in points:
                chunk_id = point.get("chunk_id")
                embedding = point.get("embedding", [])
                payload = {k: v for k, v in point.items() if k != "embedding"}
                
                qdrant_points.append(
                    PointStruct(
                        id=chunk_id,
                        vector=embedding,
                        payload=payload
                    )
                )
            
            # Upsert points
            await self.client.upsert(
                collection_name=self.collection_name,
                points=qdrant_points
            )
            
            logger.info("Points upserted successfully", extra={
                "points_count": len(qdrant_points)
            })
            
            return True
            
        except Exception as e:
            logger.error("Failed to upsert points", extra={
                "error": str(e)
            })
            return False
    
    async def delete_collection(self) -> bool:
        """Delete the collection (for testing)"""
        if not self.client:
            return False
        
        try:
            await self.client.delete_collection(collection_name=self.collection_name)
            logger.info("Collection deleted", extra={
                "collection_name": self.collection_name
            })
            return True
        except Exception as e:
            logger.error("Failed to delete collection", extra={
                "error": str(e)
            })
            return False
