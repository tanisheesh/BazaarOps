-- Migration: 001_order_triggers.sql
-- Creates PostgreSQL trigger functions and triggers that fire on orders table
-- changes and publish events to the 'order_events' pg_notify channel.
--
-- Idempotent: safe to run multiple times.

-- ---------------------------------------------------------------------------
-- Trigger function: notify_order_event
-- ---------------------------------------------------------------------------
-- Fires on INSERT and UPDATE of the orders table.
-- Sends a JSON payload via pg_notify to the 'order_events' channel.
-- The agent-service listens on this channel and bridges events into Redis.

CREATE OR REPLACE FUNCTION notify_order_event()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    event_type  TEXT;
    payload     JSON;
BEGIN
    -- Determine event type based on operation and status change
    IF TG_OP = 'INSERT' THEN
        event_type := 'order.created';
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.status = 'completed' AND OLD.status IS DISTINCT FROM 'completed' THEN
            event_type := 'order.completed';
        ELSE
            event_type := 'order.updated';
        END IF;
    END IF;

    -- Build JSON payload
    payload := json_build_object(
        'event_type',    event_type,
        'order_id',      NEW.id,
        'customer_id',   NEW.customer_id,
        'store_id',      NEW.store_id,
        'total_amount',  NEW.total_amount,
        'status',        NEW.status,
        'timestamp',     to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
    );

    -- Publish to pg_notify channel
    PERFORM pg_notify('order_events', payload::TEXT);

    RETURN NEW;
END;
$$;

-- ---------------------------------------------------------------------------
-- Triggers on the orders table
-- ---------------------------------------------------------------------------

-- INSERT trigger
DROP TRIGGER IF EXISTS orders_insert_trigger ON orders;
CREATE TRIGGER orders_insert_trigger
    AFTER INSERT ON orders
    FOR EACH ROW
    EXECUTE FUNCTION notify_order_event();

-- UPDATE trigger
DROP TRIGGER IF EXISTS orders_update_trigger ON orders;
CREATE TRIGGER orders_update_trigger
    AFTER UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION notify_order_event();
