-- Migration 004: Create event_log table for persisting domain events
-- Idempotent: safe to run multiple times

CREATE TABLE IF NOT EXISTS event_log (
    id               UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id         VARCHAR(36)  UNIQUE NOT NULL,
    event_type       VARCHAR(50)  NOT NULL,
    store_id         UUID         NOT NULL,
    data             JSONB,
    metadata         JSONB,
    processed_at     TIMESTAMP    DEFAULT NOW(),
    processing_status VARCHAR(20) DEFAULT 'received',  -- 'received', 'processed', 'failed'
    error_message    TEXT
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_event_log_event_type   ON event_log (event_type);
CREATE INDEX IF NOT EXISTS idx_event_log_store_id     ON event_log (store_id);
CREATE INDEX IF NOT EXISTS idx_event_log_processed_at ON event_log (processed_at);
