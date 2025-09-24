"""
SearchIt Gateway - FastAPI application for hybrid search and RAG
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from app.core.config import settings
from app.core.logging import setup_logging
from app.routes import search, ask, feedback, ingest

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('rag_request_total', 'Total requests', ['route', 'method'])
REQUEST_LATENCY = Histogram('rag_latency_seconds', 'Request latency', ['route'])

app = FastAPI(
    title="SearchIt Gateway",
    description="Hybrid search and RAG API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://web:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record metrics
    route = request.url.path
    method = request.method
    REQUEST_COUNT.labels(route=route, method=method).inc()
    
    process_time = time.time() - start_time
    REQUEST_LATENCY.labels(route=route).observe(process_time)
    
    return response

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "searchit-gateway"}

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Include routers
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(ask.router, prefix="/ask", tags=["ask"])
app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "SearchIt Gateway",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENV == "dev" else False
    )
