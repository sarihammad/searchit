"""
Configuration management for SearchIt Gateway
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Search backends
    opensearch_url: str = "http://localhost:9200"
    qdrant_url: str = "http://localhost:6333"
    
    # Datastores
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "searchit"
    postgres_user: str = "searchit"
    postgres_password: str = "searchit"
    
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "searchit"
    minio_secret_key: str = "searchitsecret"
    minio_bucket: str = "searchit-data"
    
    # Analytics
    kafka_broker: str = "localhost:9092"
    
    # Gateway
    gateway_port: int = 8000
    env: str = "dev"
    
    # Models
    embed_model: str = "intfloat/e5-base"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    generator: str = "stub"  # stub|hf|api
    hf_token: Optional[str] = None
    
    # Optional: OpenTelemetry
    otel_exporter_otlp_endpoint: Optional[str] = None
    otel_service_name: str = "searchit-gateway"
    
    # Search parameters
    default_top_k: int = 10
    max_top_k: int = 100
    rrf_k: int = 60
    rerank_top_k: int = 50
    final_top_k: int = 8
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
