"""
Kafka producer for analytics events
"""

from typing import Dict, Any
import logging
import json
from confluent_kafka import Producer

from app.core.config import settings

logger = logging.getLogger(__name__)

class KafkaProducer:
    """Kafka producer for analytics events"""
    
    def __init__(self):
        self.producer = None
        self._initialize_producer()
    
    def _initialize_producer(self):
        """Initialize Kafka producer"""
        try:
            config = {
                "bootstrap.servers": settings.kafka_broker,
                "client.id": "searchit-gateway",
                "acks": "all",
                "retries": 3,
                "batch.size": 16384,
                "linger.ms": 10,
                "buffer.memory": 33554432
            }
            
            self.producer = Producer(config)
            logger.info("Kafka producer initialized", extra={
                "broker": settings.kafka_broker
            })
            
        except Exception as e:
            logger.error("Failed to initialize Kafka producer", extra={
                "error": str(e)
            })
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation"""
        if err:
            logger.error("Message delivery failed", extra={
                "error": str(err)
            })
        else:
            logger.debug("Message delivered successfully", extra={
                "topic": msg.topic(),
                "partition": msg.partition(),
                "offset": msg.offset()
            })
    
    def send_search_event(self, event_data: Dict[str, Any]) -> bool:
        """Send search analytics event"""
        if not self.producer:
            return False
        
        try:
            event_data["event_type"] = "search.query"
            event_data["timestamp"] = event_data.get("timestamp", "now()")
            
            message = json.dumps(event_data)
            
            self.producer.produce(
                topic="search.events",
                value=message,
                callback=self._delivery_callback
            )
            
            # Flush to ensure message is sent
            self.producer.flush()
            
            logger.info("Search event sent", extra={
                "query": event_data.get("query", ""),
                "event_type": "search.query"
            })
            return True
            
        except Exception as e:
            logger.error("Failed to send search event", extra={
                "error": str(e)
            })
            return False
    
    def send_click_event(self, event_data: Dict[str, Any]) -> bool:
        """Send click analytics event"""
        if not self.producer:
            return False
        
        try:
            event_data["event_type"] = "search.click"
            event_data["timestamp"] = event_data.get("timestamp", "now()")
            
            message = json.dumps(event_data)
            
            self.producer.produce(
                topic="search.events",
                value=message,
                callback=self._delivery_callback
            )
            
            self.producer.flush()
            
            logger.info("Click event sent", extra={
                "doc_id": event_data.get("doc_id", ""),
                "event_type": "search.click"
            })
            return True
            
        except Exception as e:
            logger.error("Failed to send click event", extra={
                "error": str(e)
            })
            return False
    
    def send_feedback_event(self, event_data: Dict[str, Any]) -> bool:
        """Send feedback analytics event"""
        if not self.producer:
            return False
        
        try:
            event_data["event_type"] = "search.feedback"
            event_data["timestamp"] = event_data.get("timestamp", "now()")
            
            message = json.dumps(event_data)
            
            self.producer.produce(
                topic="search.events",
                value=message,
                callback=self._delivery_callback
            )
            
            self.producer.flush()
            
            logger.info("Feedback event sent", extra={
                "label": event_data.get("label", ""),
                "event_type": "search.feedback"
            })
            return True
            
        except Exception as e:
            logger.error("Failed to send feedback event", extra={
                "error": str(e)
            })
            return False
    
    def send_ask_event(self, event_data: Dict[str, Any]) -> bool:
        """Send ask/answer analytics event"""
        if not self.producer:
            return False
        
        try:
            event_data["event_type"] = "ask.answer"
            event_data["timestamp"] = event_data.get("timestamp", "now()")
            
            message = json.dumps(event_data)
            
            self.producer.produce(
                topic="ask.events",
                value=message,
                callback=self._delivery_callback
            )
            
            self.producer.flush()
            
            logger.info("Ask event sent", extra={
                "question": event_data.get("question", ""),
                "abstained": event_data.get("abstained", False),
                "event_type": "ask.answer"
            })
            return True
            
        except Exception as e:
            logger.error("Failed to send ask event", extra={
                "error": str(e)
            })
            return False
    
    def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.flush()
            logger.info("Kafka producer closed")
