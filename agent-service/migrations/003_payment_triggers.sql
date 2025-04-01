-- Migration: 003_payment_triggers.sql
-- Creates PostgreSQL trigger functions and triggers that fire on orders table
-- payment-related changes and publish events to the 'payment_events' pg_notify channel.
--
-- Idempotent: safe to run multiple times.

-- ---------------------------------------------------------------------------
-- Trigger function: notify_payment_event
-- ---------------------------------------------------------------------------
-- Fires on INSERT and UPDATE OF payment_status on the orders table.
-- Sends a JSON payload via pg_notify to the 'payment_events' channel.
-- The agent-service listens on this channel and bridges events into Redis.

CREATE OR REPLACE FUNCTION notify_payment_event()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    event_type  TEXT;
    payload     JSON;
BEGIN
    -- Only proceed when payment_status actually changes (or on INSERT)
    IF TG_OP = 'UPDATE' AND OLD.payment_status IS NOT DISTINCT FROM NEW.payment_status THEN
        RETURN NEW;
    END IF;

    -- Determine event type based on operation and payment_status
    IF TG_OP = 'INSERT' AND NEW.payment_status = 'paid' THEN
        event_type := 'payment.received';
    ELSIF TG_OP = 'UPDATE' AND NEW.payment_status = 'paid' THEN
        event_type := 'payment.received';
    ELSIF TG_OP = 'UPDATE'
          AND NEW.payment_status = 'pending'
          AND NEW.due_date IS NOT NULL
          AND NEW.due_date < now() THEN
        event_type := 'payment.overdue';
    ELSE
        -- No relevant payment event to publish
        RETURN NEW;
    END IF;

    -- Build JSON payload
    payload := json_build_object(
        'event_type',       event_type,
        'order_id',         NEW.id,
        'customer_id',      NEW.customer_id,
        'store_id',         NEW.store_id,
        'amount',           NEW.total_amount,
        'payment_status',   NEW.payment_status,
        'due_date',         NEW.due_date,
        'paid_date',        NEW.paid_at,
        'timestamp',        to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
    );

    -- Publish to pg_notify channel
    PERFORM pg_notify('payment_events', payload::TEXT);

    RETURN NEW;
END;
$$;

-- ---------------------------------------------------------------------------
-- Trigger on the orders table
-- ---------------------------------------------------------------------------

DROP TRIGGER IF EXISTS orders_payment_trigger ON orders;
CREATE TRIGGER orders_payment_trigger
    AFTER INSERT OR UPDATE OF payment_status ON orders
    FOR EACH ROW
    EXECUTE FUNCTION notify_payment_event();
