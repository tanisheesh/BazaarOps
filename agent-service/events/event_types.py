"""
Event types and event structure for BazaarOps agent-service.

Defines:
- EventType enum with all supported domain events
- Event dataclass representing the canonical event structure
- create_event() helper for constructing new events
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# EventType enum
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_COMPLETED = "order.completed"
    PAYMENT_RECEIVED = "payment.received"
    PAYMENT_OVERDUE = "payment.overdue"
    INVENTORY_LOW = "inventory.low"
    INVENTORY_CRITICAL = "inventory.critical"
    CUSTOMER_INACTIVE = "customer.inactive"
    CUSTOMER_CHURN_RISK = "customer.churn_risk"
    PRODUCT_TRENDING = "product.trending"
    FRAUD_DETECTED = "fraud.detected"
    # Credit & collection events
    CREDIT_SUSPENDED = "credit.suspended"
    CREDIT_RESTORED = "credit.restored"


# ---------------------------------------------------------------------------
# Event dataclass
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """Canonical event structure used across the agent-service."""

    event_id: str
    event_type: EventType
    timestamp: str          # ISO 8601 format
    store_id: str
    data: dict[str, Any]
    metadata: dict[str, Any]  # e.g. {"source": "agent-service", "version": "1.0"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def create_event(
    event_type: EventType,
    store_id: str,
    data: dict[str, Any],
    source: str = "agent-service",
    version: str = "1.0",
) -> Event:
    """
    Create a new Event with an auto-generated UUID and current UTC timestamp.

    Args:
        event_type: One of the EventType enum values.
        store_id:   Identifier of the store that originated the event.
        data:       Domain-specific payload for the event.
        source:     Service that produced the event (default: "agent-service").
        version:    Schema version string (default: "1.0").

    Returns:
        A fully populated Event instance.
    """
    return Event(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        store_id=store_id,
        data=data,
        metadata={"source": source, "version": version},
    )
