"""
Feedback routes for collecting user interactions
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from app.adapters.postgres import PostgresAdapter
from app.adapters.kafka import KafkaProducer

router = APIRouter()
logger = logging.getLogger(__name__)

class FeedbackRequest(BaseModel):
    query: str
    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    label: str  # click, relevant, not_relevant, thumbs_up, thumbs_down
    user_id: Optional[str] = None

@router.post("/")
async def submit_feedback(request: FeedbackRequest) -> dict:
    """
    Submit user feedback for search results or answers
    """
    try:
        logger.info("Feedback submission", extra={
            "query": request.query,
            "doc_id": request.doc_id,
            "chunk_id": request.chunk_id,
            "label": request.label,
            "user_id": request.user_id
        })
        
        # Validate label
        valid_labels = {"click", "relevant", "not_relevant", "thumbs_up", "thumbs_down"}
        if request.label not in valid_labels:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid label. Must be one of: {', '.join(valid_labels)}"
            )
        
        # Store in PostgreSQL
        postgres = PostgresAdapter()
        feedback_id = await postgres.store_feedback(
            query=request.query,
            doc_id=request.doc_id,
            chunk_id=request.chunk_id,
            label=request.label,
            user_id=request.user_id
        )
        
        # Send analytics event to Kafka
        kafka_producer = KafkaProducer()
        await kafka_producer.send_feedback_event({
            "feedback_id": feedback_id,
            "query": request.query,
            "doc_id": request.doc_id,
            "chunk_id": request.chunk_id,
            "label": request.label,
            "user_id": request.user_id,
            "timestamp": "now()"
        })
        
        logger.info("Feedback stored", extra={
            "feedback_id": feedback_id,
            "label": request.label
        })
        
        return {
            "status": "success",
            "feedback_id": feedback_id,
            "message": "Feedback submitted successfully"
        }
        
    except Exception as e:
        logger.error("Feedback submission failed", extra={
            "query": request.query,
            "label": request.label,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")
