# SearchIt Observability Guide

## Overview

SearchIt provides comprehensive observability through Prometheus metrics, Grafana dashboards, and OpenTelemetry tracing. This guide covers monitoring, alerting, and troubleshooting.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SearchIt      │    │   Prometheus    │    │    Grafana      │
│   Gateway       │───►│   Metrics       │───►│   Dashboards    │
│   (Metrics)     │    │   Collection    │    │   & Alerts      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│ OpenTelemetry   │
│   Tracing       │
└─────────────────┘
```

## Metrics

### Core Metrics

#### Request Metrics

- `rag_request_total{route, method}` - Total requests by route and method
- `rag_latency_seconds{route}` - Request latency histogram
- `rag_request_duration_seconds` - Request duration histogram

#### Search Metrics

- `search_retrieved_sources_total{source}` - Documents retrieved by source (BM25/Dense)
- `search_results_count` - Number of results returned
- `search_filters_applied_total` - Number of filters applied

#### RAG Metrics

- `rag_abstain_total{reason}` - Number of abstained answers by reason
- `rag_answer_tokens_total{model}` - Total tokens in generated answers
- `rag_evidence_coverage` - Evidence coverage scores
- `rag_citations_count` - Number of citations per answer

#### System Metrics

- `rag_memory_usage_bytes` - Memory usage
- `rag_cpu_usage_percent` - CPU usage
- `rag_active_connections` - Active database connections

### Custom Metrics

#### Business Metrics

- `user_sessions_total` - Total user sessions
- `feedback_submitted_total{type}` - Feedback by type
- `popular_queries_total` - Most common queries
- `answer_quality_score` - Quality scores from feedback

## Prometheus Configuration

### Scrape Configuration

```yaml
scrape_configs:
  - job_name: "gateway"
    static_configs:
      - targets: ["gateway:8000"]
    metrics_path: "/metrics"
    scrape_interval: 5s

  - job_name: "opensearch"
    static_configs:
      - targets: ["opensearch:9200"]
    metrics_path: "/_prometheus/metrics"
    scrape_interval: 30s
```

### Recording Rules

```yaml
groups:
  - name: searchit.rules
    rules:
      - record: searchit:request_rate
        expr: sum(rate(rag_request_total[5m])) by (route)

      - record: searchit:error_rate
        expr: sum(rate(rag_request_total{status="error"}[5m])) / sum(rate(rag_request_total[5m]))

      - record: searchit:abstain_rate
        expr: sum(rate(rag_abstain_total[5m])) / sum(rate(rag_request_total[5m]))
```

## Grafana Dashboards

### Main Dashboard

The main SearchIt dashboard provides:

- **Request Rate**: Requests per second by route
- **Response Time**: P50, P95, P99 latencies
- **Abstain Rate**: Proportion of abstained answers
- **Error Rate**: Request error rate
- **Search Sources**: Distribution of BM25 vs Dense results
- **Feedback**: User feedback distribution

### Access

- URL: http://localhost:3001
- Username: `admin`
- Password: `admin`

### Custom Dashboards

Create custom dashboards for:

- **Performance Monitoring**: Latency trends, throughput
- **Quality Metrics**: Abstain rates, coverage scores
- **User Behavior**: Popular queries, feedback patterns
- **System Health**: Resource usage, connection pools

## OpenTelemetry Tracing

### Configuration

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:14268/api/traces")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
```

### Trace Structure

```
SearchIt Request
├── Gateway Handler
├── Authentication
├── Search Flow
│   ├── Query Processing
│   ├── BM25 Search
│   ├── Dense Search
│   ├── RRF Fusion
│   └── Result Formatting
├── Ask Flow
│   ├── Retrieval
│   ├── Reranking
│   ├── Generation
│   └── Citation Extraction
└── Response
```

### Span Attributes

- `query_id`: Unique query identifier
- `user_id`: User identifier
- `query_length`: Query text length
- `results_count`: Number of results
- `abstained`: Whether answer was abstained
- `response_time_ms`: Response time in milliseconds

## Alerting

### Critical Alerts

```yaml
groups:
  - name: searchit.critical
    rules:
      - alert: HighErrorRate
        expr: searchit:error_rate > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} for {{ $labels.instance }}"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(rag_latency_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}s for {{ $labels.instance }}"
```

### Warning Alerts

```yaml
- alert: HighAbstainRate
  expr: searchit:abstain_rate > 0.3
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High abstain rate"
    description: "Abstain rate is {{ $value }} for {{ $labels.instance }}"

- alert: LowThroughput
  expr: searchit:request_rate < 1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Low throughput detected"
    description: "Request rate is {{ $value }} for {{ $labels.instance }}"
```

## Logging

### Structured Logging

```python
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Structured log entry
logger.info("Search completed", extra={
    "query": "machine learning",
    "results_count": 10,
    "response_time_ms": 150,
    "user_id": "user123",
    "timestamp": datetime.utcnow().isoformat()
})
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General information about system operation
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failed operations
- **CRITICAL**: Critical error messages

### Log Aggregation

For production deployments, integrate with:

- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Fluentd**: Log collection and forwarding
- **Loki**: Grafana's log aggregation system

## Health Checks

### Application Health

```python
@app.get("/health")
async def health_check():
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": await check_database(),
            "opensearch": await check_opensearch(),
            "qdrant": await check_qdrant(),
            "memory": check_memory_usage()
        }
    }

    # Determine overall health
    all_healthy = all(check["healthy"] for check in checks["checks"].values())
    checks["status"] = "healthy" if all_healthy else "unhealthy"

    return checks
```

### Infrastructure Health

Monitor:

- **Database connections**: Connection pool health
- **Search indices**: Index status and health
- **Memory usage**: Heap and off-heap memory
- **CPU usage**: System and application CPU
- **Disk space**: Available disk space
- **Network**: Latency to dependencies

## Performance Monitoring

### Key Performance Indicators (KPIs)

- **Response Time**: P50, P95, P99 latencies
- **Throughput**: Requests per second
- **Error Rate**: Percentage of failed requests
- **Availability**: Uptime percentage
- **Abstain Rate**: Percentage of abstained answers

### Performance Targets

- **Search Latency**: P95 < 100ms
- **Ask Latency**: P95 < 2s
- **Error Rate**: < 1%
- **Availability**: > 99.9%

### Performance Testing

```bash
# Load testing with wrk
wrk -t12 -c400 -d30s --script=search.lua http://localhost:8000/search

# Custom performance test
python scripts/performance_test.py --queries 1000 --concurrent 50
```

## Troubleshooting

### Common Issues

1. **High Latency**

   - Check database connection pool
   - Monitor embedding model performance
   - Verify search index health

2. **High Error Rate**

   - Check application logs
   - Verify dependency health
   - Monitor resource usage

3. **High Abstain Rate**
   - Check retrieval quality
   - Verify embedding model
   - Review coverage thresholds

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export OTEL_LOG_LEVEL=DEBUG

# Start with debug mode
python -m app.main --debug
```

### Profiling

```python
import cProfile
import pstats

# Profile search function
profiler = cProfile.Profile()
profiler.enable()
# ... search code ...
profiler.disable()

# Save profile results
profiler.dump_stats("search_profile.prof")

# Analyze results
stats = pstats.Stats(profiler)
stats.sort_stats("cumulative")
stats.print_stats(20)
```

## Best Practices

### Monitoring

1. **Monitor Key Metrics**: Focus on business-critical metrics
2. **Set Appropriate Thresholds**: Avoid alert fatigue
3. **Use Multiple Time Windows**: Short-term and long-term trends
4. **Monitor Dependencies**: Track external service health

### Alerting

1. **Clear Alert Messages**: Include context and remediation steps
2. **Appropriate Severity**: Critical vs warning classification
3. **Escalation Policies**: Define escalation procedures
4. **Regular Review**: Review and tune alert thresholds

### Logging

1. **Structured Logs**: Use consistent log format
2. **Include Context**: Add relevant metadata
3. **Avoid Sensitive Data**: Never log passwords or PII
4. **Log Levels**: Use appropriate log levels

### Performance

1. **Baseline Establishment**: Establish performance baselines
2. **Regular Testing**: Perform regular performance tests
3. **Capacity Planning**: Plan for growth
4. **Optimization**: Continuously optimize performance

## Integration Examples

### Slack Integration

```yaml
# Alertmanager configuration
route:
  group_by: ["alertname"]
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: "slack"

receivers:
  - name: "slack"
    slack_configs:
      - api_url: "https://hooks.slack.com/services/..."
        channel: "#alerts"
        title: "SearchIt Alert"
        text: "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}"
```

### Email Integration

```yaml
receivers:
  - name: "email"
    email_configs:
      - to: "admin@company.com"
        subject: "SearchIt Alert: {{ .GroupLabels.alertname }}"
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
```

### PagerDuty Integration

```yaml
receivers:
  - name: "pagerduty"
    pagerduty_configs:
      - service_key: "your-service-key"
        description: "{{ .GroupLabels.alertname }}"
        details:
          summary: "{{ .Annotations.summary }}"
          description: "{{ .Annotations.description }}"
```
