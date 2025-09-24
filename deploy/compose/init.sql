-- Initialize SearchIt database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    title TEXT,
    url TEXT,
    lang TEXT,
    tags TEXT[],
    source TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Chunks table
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT REFERENCES documents(doc_id),
    text TEXT,
    section TEXT,
    tokens INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Feedback table
CREATE TABLE IF NOT EXISTS feedback (
    id BIGSERIAL PRIMARY KEY,
    query TEXT,
    doc_id TEXT,
    chunk_id TEXT,
    label TEXT CHECK (label IN ('click','relevant','not_relevant','thumbs_up','thumbs_down')),
    ts TIMESTAMPTZ DEFAULT now(),
    user_id TEXT
);

-- Evaluation runs table
CREATE TABLE IF NOT EXISTS eval_runs (
    id BIGSERIAL PRIMARY KEY,
    run_name TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    metrics JSONB,
    params JSONB
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_feedback_ts ON feedback(ts);
CREATE INDEX IF NOT EXISTS idx_feedback_label ON feedback(label);
