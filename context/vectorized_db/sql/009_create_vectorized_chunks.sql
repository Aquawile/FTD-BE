-- Migration 009: Create sec_vectorized_chunks table for GCS vector data
-- Non-destructive: does not modify any existing tables
-- Populated by scripts/sync_vectorized_to_postgres.py

CREATE TABLE IF NOT EXISTS sec_vectorized_chunks (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT,
    cik TEXT,
    accession_number TEXT,
    form_type TEXT,
    filing_date DATE,
    chunk_index INTEGER NOT NULL,
    text_preview TEXT,
    vector JSONB,
    source_bucket TEXT,
    source_object TEXT,
    vectorized_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Idempotency: prevent duplicate inserts from re-runs
    UNIQUE(source_object, chunk_index)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_sec_vectorized_chunks_source_object
    ON sec_vectorized_chunks(source_object);
CREATE INDEX IF NOT EXISTS idx_sec_vectorized_chunks_ticker
    ON sec_vectorized_chunks(ticker);
CREATE INDEX IF NOT EXISTS idx_sec_vectorized_chunks_accession
    ON sec_vectorized_chunks(accession_number);
CREATE INDEX IF NOT EXISTS idx_sec_vectorized_chunks_cik
    ON sec_vectorized_chunks(cik);
