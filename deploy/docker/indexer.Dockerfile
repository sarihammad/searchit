FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY pipelines/ ./pipelines/
COPY configs/ ./configs/

# Create non-root user
RUN useradd -m -u 1000 indexer && chown -R indexer:indexer /app
USER indexer

# Keep container running for manual pipeline execution
CMD ["sleep", "infinity"]
