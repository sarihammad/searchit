"""
OpenTelemetry configuration for SearchIt Gateway
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

def setup_telemetry() -> None:
    """Setup OpenTelemetry tracing"""
    
    if not settings.otel_exporter_otlp_endpoint:
        logger.info("OpenTelemetry endpoint not configured, skipping telemetry setup")
        return
    
    try:
        # Configure tracer provider
        trace.set_tracer_provider(TracerProvider())
        tracer = trace.get_tracer(__name__)
        
        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
        )
        
        # Configure span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app()
        
        # Instrument requests
        RequestsInstrumentor().instrument()
        
        logger.info("OpenTelemetry configured", extra={
            "endpoint": settings.otel_exporter_otlp_endpoint,
            "service_name": settings.otel_service_name
        })
        
    except Exception as e:
        logger.error("Failed to setup OpenTelemetry", extra={
            "error": str(e)
        })

def get_tracer(name: str):
    """Get a tracer instance"""
    return trace.get_tracer(name)
