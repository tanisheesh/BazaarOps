-- Migration: 002_inventory_triggers.sql
-- Creates PostgreSQL trigger functions and triggers that fire on products table
-- changes and publish events to the 'inventory_events' pg_notify channel.
--
-- Idempotent: safe to run multiple times.

-- ---------------------------------------------------------------------------
-- Trigger function: notify_inventory_event
-- ---------------------------------------------------------------------------
-- Fires on INSERT and UPDATE OF stock_quantity on the products table.
-- Sends a JSON payload via pg_notify to the 'inventory_events' channel.
-- The agent-service listens on this channel and bridges events into Redis.

CREATE OR REPLACE FUNCTION notify_inventory_event()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $
DECLARE
    event_type  TEXT;
    payload     JSON;
BEGIN
    -- For UPDATE: only fire when stock_quantity actually changed
    IF TG_OP = 'UPDATE' AND OLD.stock_quantity = NEW.stock_quantity THEN
        RETURN NEW;
    END IF;

    -- Determine event type based on operation and stock level
    IF TG_OP = 'INSERT' THEN
        -- Only notify on INSERT if initial stock is below threshold
        IF NEW.stock_quantity < NEW.low_stock_threshold THEN
            event_type := 'inventory.low';
        ELSE
            RETURN NEW;
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.stock_quantity <= 0 THEN
            event_type := 'inventory.critical';
        ELSIF NEW.stock_quantity < NEW.low_stock_threshold THEN
            event_type := 'inventory.low';
        ELSE
            -- Stock is healthy; no notification needed
            RETURN NEW;
        END IF;
    END IF;

    -- Build JSON payload
    payload := json_build_object(
        'event_type',          event_type,
        'product_id',          NEW.id,
        'store_id',            NEW.store_id,
        'product_name',        NEW.name,
        'current_stock',       NEW.stock_quantity,
        'low_stock_threshold', NEW.low_stock_threshold,
        'timestamp',           to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
    );

    -- Publish to pg_notify channel
    PERFORM pg_notify('inventory_events', payload::TEXT);

    RETURN NEW;
END;
$;

-- ---------------------------------------------------------------------------
-- Trigger on the products table
-- ---------------------------------------------------------------------------

DROP TRIGGER IF EXISTS products_stock_trigger ON products;
CREATE TRIGGER products_stock_trigger
    AFTER INSERT OR UPDATE OF stock_quantity ON products
    FOR EACH ROW
    EXECUTE FUNCTION notify_inventory_event();
