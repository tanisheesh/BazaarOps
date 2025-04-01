-- Migration 006: Customer lifecycle tables and column additions
-- Idempotent: safe to run multiple times

-- Add lifecycle columns to customers table
ALTER TABLE customers ADD COLUMN IF NOT EXISTS birthday VARCHAR(5);          -- MM-DD format
ALTER TABLE customers ADD COLUMN IF NOT EXISTS is_vip BOOLEAN DEFAULT FALSE;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS last_order_date TIMESTAMP;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS avg_order_interval INTEGER;   -- Days
ALTER TABLE customers ADD COLUMN IF NOT EXISTS churn_risk_level VARCHAR(20);

-- customer_segments: tracks segment assignments per customer
CREATE TABLE IF NOT EXISTS customer_segments (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID         REFERENCES customers(id),
    segment_type    VARCHAR(50),  -- 'vip', 'at_risk', 'dormant', 'new'
    assigned_at     TIMESTAMP    DEFAULT NOW(),
    expires_at      TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customer_segments_customer_id  ON customer_segments (customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_segments_segment_type ON customer_segments (segment_type);

-- birthday_wishes_sent: tracks birthday messages sent to customers
CREATE TABLE IF NOT EXISTS birthday_wishes_sent (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID         REFERENCES customers(id),
    sent_at         TIMESTAMP    DEFAULT NOW(),
    message_text    TEXT,
    responded       BOOLEAN      DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_birthday_wishes_customer_id ON birthday_wishes_sent (customer_id);
CREATE INDEX IF NOT EXISTS idx_birthday_wishes_sent_at     ON birthday_wishes_sent (sent_at);

-- re_engagement_messages: tracks churn re-engagement messages
CREATE TABLE IF NOT EXISTS re_engagement_messages (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID         REFERENCES customers(id),
    store_id        UUID         REFERENCES stores(id),
    message_number  INTEGER      DEFAULT 1,   -- 1 = first, 2 = follow-up
    sent_at         TIMESTAMP    DEFAULT NOW(),
    message_text    TEXT,
    responded       BOOLEAN      DEFAULT FALSE,
    responded_at    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_re_engagement_customer_id ON re_engagement_messages (customer_id);
CREATE INDEX IF NOT EXISTS idx_re_engagement_store_id    ON re_engagement_messages (store_id);
CREATE INDEX IF NOT EXISTS idx_re_engagement_sent_at     ON re_engagement_messages (sent_at);
