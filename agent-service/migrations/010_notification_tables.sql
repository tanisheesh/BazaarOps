-- Migration 010: Notification Tables
-- Creates tables for smart notification orchestrator (Task 8)

-- 8.5 notification_preferences: stores per-customer notification preferences
CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    tone_preference VARCHAR(20) DEFAULT 'casual',       -- 'formal' | 'casual'
    use_emojis BOOLEAN DEFAULT TRUE,
    language_preference VARCHAR(20) DEFAULT 'english',  -- 'english' | 'hindi'
    message_length_preference VARCHAR(20) DEFAULT 'brief', -- 'brief' | 'detailed'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(customer_id)
);

-- 8.5 notification_history: tracks all notifications sent/queued/batched
CREATE TABLE IF NOT EXISTS notification_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    store_id UUID REFERENCES stores(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) DEFAULT 'general',
    priority VARCHAR(20) DEFAULT 'medium',  -- 'critical' | 'high' | 'medium' | 'low'
    status VARCHAR(20) DEFAULT 'queued',    -- 'queued' | 'sent' | 'batched'
    sent_at TIMESTAMP,
    responded BOOLEAN DEFAULT FALSE,
    responded_at TIMESTAMP,
    response_hour INTEGER,                  -- Hour of day (0-23) when customer responded
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_notification_history_customer
    ON notification_history(customer_id);

CREATE INDEX IF NOT EXISTS idx_notification_history_store
    ON notification_history(store_id);

CREATE INDEX IF NOT EXISTS idx_notification_history_status
    ON notification_history(status);

CREATE INDEX IF NOT EXISTS idx_notification_history_sent_at
    ON notification_history(sent_at);

CREATE INDEX IF NOT EXISTS idx_notification_preferences_customer
    ON notification_preferences(customer_id);
