-- Migration 007: Credit and collection system tables
-- Idempotent: safe to run multiple times

-- Add credit columns to customers table
ALTER TABLE customers ADD COLUMN IF NOT EXISTS credit_score INTEGER DEFAULT 50;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS credit_limit DECIMAL DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS credit_suspended BOOLEAN DEFAULT FALSE;

-- payment_history: tracks individual payment records per order
CREATE TABLE IF NOT EXISTS payment_history (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID         REFERENCES customers(id),
    order_id        UUID         REFERENCES orders(id),
    amount          DECIMAL      NOT NULL,
    due_date        DATE,
    paid_date       DATE,
    days_to_payment INTEGER,
    was_late        BOOLEAN,
    created_at      TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_history_customer_id ON payment_history (customer_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_order_id    ON payment_history (order_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_created_at  ON payment_history (created_at);

-- payment_reminders: tracks reminder messages sent to customers
CREATE TABLE IF NOT EXISTS payment_reminders (
    id                UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id       UUID         REFERENCES customers(id),
    order_id          UUID         REFERENCES orders(id),
    reminder_type     VARCHAR(50),  -- 'friendly', 'neutral', 'firm', 'strict'
    sent_at           TIMESTAMP    DEFAULT NOW(),
    responded         BOOLEAN      DEFAULT FALSE,
    payment_received  BOOLEAN      DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_payment_reminders_customer_id ON payment_reminders (customer_id);
CREATE INDEX IF NOT EXISTS idx_payment_reminders_order_id    ON payment_reminders (order_id);
CREATE INDEX IF NOT EXISTS idx_payment_reminders_sent_at     ON payment_reminders (sent_at);

-- notification_response_times: tracks when customers respond to messages (for timing optimization)
CREATE TABLE IF NOT EXISTS notification_response_times (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID         REFERENCES customers(id),
    sent_at         TIMESTAMP    NOT NULL,
    responded_at    TIMESTAMP,
    response_hour   INTEGER,     -- Hour of day (0-23) when customer responded
    notification_type VARCHAR(50),
    created_at      TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_response_customer_id ON notification_response_times (customer_id);
CREATE INDEX IF NOT EXISTS idx_notification_response_hour        ON notification_response_times (response_hour);
