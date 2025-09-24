"""
PostgreSQL adapter for metadata and feedback storage
"""

from typing import List, Dict, Any, Optional
import logging
import asyncio
import asyncpg
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

class PostgresAdapter:
    """Adapter for PostgreSQL operations"""
    
    def __init__(self):
        self.pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            # Connection parameters
            conn_params = {
                "host": settings.postgres_host,
                "port": settings.postgres_port,
                "database": settings.postgres_db,
                "user": settings.postgres_user,
                "password": settings.postgres_password,
                "min_size": 5,
                "max_size": 20
            }
            
            # Create pool (will be initialized on first use)
            self.pool = None  # Will be created lazily
            
            logger.info("PostgreSQL adapter initialized", extra={
                "host": settings.postgres_host,
                "database": settings.postgres_db
            })
            
        except Exception as e:
            logger.error("Failed to initialize PostgreSQL adapter", extra={
                "error": str(e)
            })
    
    async def _get_pool(self):
        """Get or create connection pool"""
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(
                    host=settings.postgres_host,
                    port=settings.postgres_port,
                    database=settings.postgres_db,
                    user=settings.postgres_user,
                    password=settings.postgres_password,
                    min_size=5,
                    max_size=20
                )
                logger.info("PostgreSQL connection pool created")
            except Exception as e:
                logger.error("Failed to create PostgreSQL pool", extra={
                    "error": str(e)
                })
                raise
        
        return self.pool
    
    async def store_document(self, document: Dict[str, Any]) -> bool:
        """Store document metadata"""
        try:
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO documents (doc_id, title, url, lang, tags, source, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        url = EXCLUDED.url,
                        lang = EXCLUDED.lang,
                        tags = EXCLUDED.tags,
                        source = EXCLUDED.source,
                        updated_at = EXCLUDED.updated_at
                """, 
                document.get("doc_id"),
                document.get("title"),
                document.get("url"),
                document.get("lang"),
                document.get("tags", []),
                document.get("source"),
                datetime.utcnow()
                )
            
            logger.info("Document stored", extra={
                "doc_id": document.get("doc_id")
            })
            return True
            
        except Exception as e:
            logger.error("Failed to store document", extra={
                "doc_id": document.get("doc_id"),
                "error": str(e)
            })
            return False
    
    async def store_chunk(self, chunk: Dict[str, Any]) -> bool:
        """Store chunk metadata"""
        try:
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO chunks (chunk_id, doc_id, text, section, tokens, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        doc_id = EXCLUDED.doc_id,
                        text = EXCLUDED.text,
                        section = EXCLUDED.section,
                        tokens = EXCLUDED.tokens
                """,
                chunk.get("chunk_id"),
                chunk.get("doc_id"),
                chunk.get("text"),
                chunk.get("section"),
                chunk.get("tokens"),
                datetime.utcnow()
                )
            
            logger.info("Chunk stored", extra={
                "chunk_id": chunk.get("chunk_id")
            })
            return True
            
        except Exception as e:
            logger.error("Failed to store chunk", extra={
                "chunk_id": chunk.get("chunk_id"),
                "error": str(e)
            })
            return False
    
    async def store_feedback(
        self,
        query: str,
        doc_id: Optional[str],
        chunk_id: Optional[str],
        label: str,
        user_id: Optional[str]
    ) -> int:
        """Store user feedback and return feedback ID"""
        try:
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                feedback_id = await conn.fetchval("""
                    INSERT INTO feedback (query, doc_id, chunk_id, label, user_id, ts)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                """,
                query,
                doc_id,
                chunk_id,
                label,
                user_id,
                datetime.utcnow()
                )
            
            logger.info("Feedback stored", extra={
                "feedback_id": feedback_id,
                "label": label
            })
            return feedback_id
            
        except Exception as e:
            logger.error("Failed to store feedback", extra={
                "error": str(e)
            })
            raise
    
    async def get_feedback_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get feedback statistics"""
        try:
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                stats = await conn.fetch("""
                    SELECT 
                        label,
                        COUNT(*) as count
                    FROM feedback
                    WHERE ts >= NOW() - INTERVAL '%s days'
                    GROUP BY label
                """, days)
                
                return {row["label"]: row["count"] for row in stats}
                
        except Exception as e:
            logger.error("Failed to get feedback stats", extra={
                "error": str(e)
            })
            return {}
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")
