# SearchIt Architecture

## Overview

SearchIt is a production-style hybrid search and RAG system that combines traditional BM25 search with modern vector embeddings for superior retrieval performance. The system is designed with scalability, observability, and maintainability in mind.

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Indexer       │    │   Storage       │
│                 │    │   Pipelines     │    │                 │
│ • Web pages     │───►│                 │───►│ • OpenSearch    │
│ • PDFs          │    │ • Ingest        │    │ • Qdrant        │
│ • Documents     │    │ • Chunk         │    │ • PostgreSQL    │
│                 │    │ • Embed         │    │ • MinIO         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │◄───│   Gateway       │───►│   Analytics     │
│                 │    │   (FastAPI)     │    │                 │
│ • Search        │    │                 │    │ • Kafka         │
│ • Ask           │    │ • Retrieve      │    │ • Events        │
│ • Feedback      │    │ • Rerank        │    │ • Metrics       │
└─────────────────┘    │ • Generate      │    └─────────────────┘
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Observability │
                       │                 │
                       │ • Prometheus    │
                       │ • Grafana       │
                       │ • OpenTelemetry │
                       └─────────────────┘
```

## Components

### 1. Indexer Service

**Purpose**: Processes and indexes documents for search

**Key Features**:

- Multi-format ingestion (web, PDF, documents)
- Semantic chunking with heading awareness
- Batch embedding generation
- Parallel indexing to multiple stores

**Pipelines**:

- `ingest_web.py`: Web scraping and HTML processing
- `ingest_pdf.py`: PDF text extraction and OCR
- `clean_normalize.py`: Text cleaning and language detection
- `embed.py`: Batch embedding generation
- `push_to_stores.py`: Bulk indexing to search stores

### 2. Gateway Service (FastAPI)

**Purpose**: Core search and RAG API

**Key Features**:

- Hybrid retrieval (BM25 + Vector + RRF)
- Cross-encoder reranking
- Grounded answer generation
- Feedback collection

**Endpoints**:

- `GET /search`: Hybrid search with facets
- `POST /ask`: Grounded question answering
- `POST /feedback`: User interaction tracking
- `POST /ingest`: Document ingestion trigger

### 3. Web UI (Next.js)

**Purpose**: User interface for search and interaction

**Key Features**:

- Real-time search with instant results
- Citation display and navigation
- Feedback collection (thumbs up/down)
- Responsive design with dark/light themes

### 4. Storage Layer

#### OpenSearch

- **Purpose**: BM25 search and metadata
- **Features**: Full-text search, aggregations, highlighting
- **Schema**: Text fields + knn_vector for embeddings

#### Qdrant

- **Purpose**: Vector similarity search
- **Features**: Cosine similarity, filtering, payload storage
- **Schema**: 768-dimensional vectors with metadata

#### PostgreSQL

- **Purpose**: Metadata and feedback storage
- **Tables**: documents, chunks, feedback, eval_runs

#### MinIO

- **Purpose**: Object storage for raw documents
- **Features**: S3-compatible API, versioning

### 5. Analytics & Observability

#### Kafka (Redpanda)

- **Purpose**: Event streaming for analytics
- **Topics**: search.events, ask.events
- **Events**: queries, clicks, feedback, answers

#### Prometheus

- **Purpose**: Metrics collection
- **Metrics**: latency, throughput, error rates, custom business metrics

#### Grafana

- **Purpose**: Metrics visualization
- **Dashboards**: System health, search performance, user behavior

## Data Flow

### 1. Indexing Flow

```
Document → Ingest → Clean → Chunk → Embed → Index
    │         │        │       │       │       │
    ▼         ▼        ▼       ▼       ▼       ▼
  Raw     Normalized  Text   Tokens  Vectors  Search
  Data    Content    Chunks  Count   (768d)   Stores
```

### 2. Search Flow

```
Query → Embed → Retrieve → Rerank → Generate → Response
  │       │        │         │         │          │
  ▼       ▼        ▼         ▼         ▼          ▼
Text   Vector   BM25+Vec   Cross-Enc  LLM      Answer+
Query  (768d)   Results    Top-8     Gen      Citations
```

### 3. RAG Flow

```
Question → Retrieve → Rerank → Context → Generate → Validate → Answer
    │         │         │        │         │         │         │
    ▼         ▼         ▼        ▼         ▼         ▼         ▼
   Text    BM25+Vec   Cross-Enc  Assemble  LLM      Citations  Final
  Query    Top-100    Top-8     Context   Gen      Check      Result
```

## Key Algorithms

### Reciprocal Rank Fusion (RRF)

Combines BM25 and vector search results:

```
RRF_score(doc) = Σ(1 / (k + rank_i(doc)))
```

Where:

- `k = 60` (tunable parameter)
- `rank_i` is the rank in source `i` (BM25 or Vector)

### Semantic Chunking

- **Min tokens**: 250
- **Max tokens**: 500
- **Overlap**: 15%
- **Strategy**: Heading-aware, sentence boundary preservation

### Cross-Encoder Reranking

- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Input**: Query-candidate pairs
- **Output**: Relevance scores
- **Usage**: Rerank top 50 → top 8

## Performance Characteristics

### Latency Targets

- **Search**: < 100ms (P95)
- **Ask**: < 2s (P95)
- **Indexing**: 1000 docs/min

### Scalability

- **Concurrent users**: 1000+
- **Documents**: 1M+ indexed
- **Queries/sec**: 100+ sustained

### Resource Requirements

- **Gateway**: 2 CPU, 4GB RAM
- **Indexer**: 4 CPU, 8GB RAM
- **OpenSearch**: 4 CPU, 8GB RAM
- **Qdrant**: 2 CPU, 4GB RAM

## Security & Reliability

### Security

- **Authentication**: Optional API keys
- **Rate limiting**: Per-user quotas
- **Data privacy**: No PII in logs
- **Network**: TLS in production

### Reliability

- **Health checks**: All services monitored
- **Circuit breakers**: Fail-fast on dependencies
- **Retries**: Exponential backoff
- **Monitoring**: Comprehensive alerting

## Deployment

### Local Development

```bash
make dev-up     # Start all services
make index-toy  # Index sample data
make demo       # Run demo queries
```

### Production

- **Container orchestration**: Kubernetes
- **Load balancing**: NGINX/HAProxy
- **Database**: Managed services (AWS RDS, etc.)
- **Monitoring**: Prometheus + Grafana
- **Logging**: Centralized logging (ELK stack)

## Configuration

### Environment Variables

See [env.example](../env.example) for all configuration options.

### Key Settings

- **Models**: Embedding and reranker model names
- **Search**: Top-K limits, RRF parameters
- **Storage**: Connection strings and credentials
- **Observability**: Metrics and tracing endpoints
