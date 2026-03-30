-- Migration 005: Create reorder tables for autonomous inventory orchestrator
-- Idempotent: safe to run multiple times

-- pending_supplier_orders: tracks AI-suggested reorder requests
CREATE TABLE IF NOT EXISTS pending_supplier_orders (
    id                    UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id              UUID         REFERENCES stores(id),
    product_id            UUID         REFERENCES products(id),
    quantity              DECIMAL      NOT NULL,
    suggested_by_agent    BOOLEAN      DEFAULT TRUE,
    owner_approved        BOOLEAN      DEFAULT FALSE,
    approved_at           TIMESTAMP,
    supplier_contacted    BOOLEAN      DEFAULT FALSE,
    expected_delivery_date DATE,
    status                VARCHAR(50)  DEFAULT 'pending',
    created_at            TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pending_orders_store_id    ON pending_supplier_orders (store_id);
CREATE INDEX IF NOT EXISTS idx_pending_orders_product_id  ON pending_supplier_orders (product_id);
CREATE INDEX IF NOT EXISTS idx_pending_orders_status      ON pending_supplier_orders (status);

-- reorder_approvals: tracks owner edits for the learning system
CREATE TABLE IF NOT EXISTS reorder_approvals (
    id                  UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    reorder_id          UUID         REFERENCES pending_supplier_orders(id),
    suggested_quantity  DECIMAL,
    approved_quantity   DECIMAL,
    owner_edited        BOOLEAN      DEFAULT FALSE,
    edit_percentage     DECIMAL,
    created_at          TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reorder_approvals_reorder_id ON reorder_approvals (reorder_id);
