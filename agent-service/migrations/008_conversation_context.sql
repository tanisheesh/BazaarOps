-- Migration 008: Conversation context table for conversational AI shopping assistant
-- Task 5.7: Create database table (conversation_context)
-- Idempotent: safe to run multiple times

-- Enable uuid extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- conversation_context: persists conversation state for the NLP shopping assistant
CREATE TABLE IF NOT EXISTS conversation_context (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID         REFERENCES customers(id) ON DELETE CASCADE,
    session_id      VARCHAR(100),
    messages        JSONB        DEFAULT '[]'::jsonb,   -- Array of {role, content, timestamp}
    current_cart    JSONB        DEFAULT '[]'::jsonb,   -- Items being ordered
    state           VARCHAR(50)  DEFAULT 'browsing',    -- browsing | ordering | confirming | confirmed
    created_at      TIMESTAMP    DEFAULT NOW(),
    updated_at      TIMESTAMP    DEFAULT NOW(),
    expires_at      TIMESTAMP    DEFAULT (NOW() + INTERVAL '1 hour')
);

CREATE INDEX IF NOT EXISTS idx_conversation_context_customer_id ON conversation_context (customer_id);
CREATE INDEX IF NOT EXISTS idx_conversation_context_session_id  ON conversation_context (session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_context_expires_at  ON conversation_context (expires_at);

-- Auto-update updated_at on row change
CREATE OR REPLACE FUNCTION update_conversation_context_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_conversation_context_updated_at ON conversation_context;
CREATE TRIGGER trg_conversation_context_updated_at
    BEFORE UPDATE ON conversation_context
    FOR EACH ROW EXECUTE FUNCTION update_conversation_context_updated_at();

-- nlp_performance_log: tracks NLP accuracy and latency for monitoring (5.10)
CREATE TABLE IF NOT EXISTS nlp_performance_log (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID         REFERENCES customers(id),
    store_id        UUID         REFERENCES stores(id),
    user_message    TEXT,
    detected_intent VARCHAR(50),
    items_extracted INTEGER      DEFAULT 0,
    items_matched   INTEGER      DEFAULT 0,
    used_fallback   BOOLEAN      DEFAULT FALSE,
    latency_ms      INTEGER,
    success         BOOLEAN      DEFAULT TRUE,
    created_at      TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nlp_perf_customer_id ON nlp_performance_log (customer_id);
CREATE INDEX IF NOT EXISTS idx_nlp_perf_created_at  ON nlp_performance_log (created_at);
CREATE INDEX IF NOT EXISTS idx_nlp_perf_success     ON nlp_performance_log (success);
