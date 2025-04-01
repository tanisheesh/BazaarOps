"""
EventSubscriber: listens to Redis pub/sub channels and dispatches events
to registered handlers.

Each event type is subscribed to its own channel (e.g. "order.created") as
well as the wildcard channel "events.all".  The subscriber runs in a
background thread so it never blocks the main application.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import TYPE_CHECKING, Callable, Protocol, runtime_checkable

import redis

from events.event_types import Event, EventType, create_event

if TYPE_CHECKING:
    from events.dead_letter_queue import DeadLetterQueue
    from events.monitoring import EventMonitor

logger = logging.getLogger(__name__)

WILDCARD_CHANNEL = "events.all"


# ---------------------------------------------------------------------------
# EventHandler protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class EventHandler(Protocol):
    """Protocol for objects that can handle an Event."""

    def handle(self, event: Event) -> None:
        """Process the given event."""
        ...


# ---------------------------------------------------------------------------
# EventSubscriber
# ---------------------------------------------------------------------------

class EventSubscriber:
    """Subscribes to Redis pub/sub channels and dispatches events to handlers."""

    def __init__(
        self,
        redis_client: redis.Redis,
        dlq: DeadLetterQueue | None = None,
        monitor: EventMonitor | None = None,
    ) -> None:
        """
        Args:
            redis_client: A synchronous Redis client.
            dlq:          Optional DeadLetterQueue. When provided, handler
                          exceptions are pushed to the DLQ instead of only
                          being logged.
            monitor:      Optional EventMonitor. When provided, each handler
                          call is wrapped with track_event to record latency.
        """
        self._redis = redis_client
        self._dlq = dlq
        self._monitor = monitor
        self._handlers: dict[EventType, list[Callable[[Event], None]]] = {}
        self._pubsub: redis.client.PubSub | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Register a callable handler for the given event type.

        Multiple handlers can be registered for the same event type; they
        will all be called in registration order.

        Args:
            event_type: The EventType to listen for.
            handler:    A callable that accepts a single Event argument.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug("Registered handler %s for event type %s", handler, event_type)

    # ------------------------------------------------------------------
    # Listening
    # ------------------------------------------------------------------

    def subscribe_and_listen(self) -> None:
        """Subscribe to all registered channels and start a blocking listen loop.

        This method is intended to be run in a background thread (see
        ``start()``).  It subscribes to:
          - One channel per registered EventType (e.g. "order.created")
          - The wildcard channel "events.all"

        The loop deserialises each incoming JSON message back to an Event
        and dispatches it to the appropriate handler(s).  Per-message errors
        are caught and logged so the loop never crashes.
        """
        self._pubsub = self._redis.pubsub()

        channels = [et.value for et in self._handlers] + [WILDCARD_CHANNEL]
        self._pubsub.subscribe(*channels)
        logger.info("EventSubscriber subscribed to channels: %s", channels)

        for message in self._pubsub.listen():
            if self._stop_event.is_set():
                break

            if message["type"] != "message":
                continue

            try:
                self._dispatch(message)
            except Exception as exc:  # pragma: no cover
                logger.error("Unhandled error dispatching message: %s", exc)

        logger.info("EventSubscriber listen loop exited.")

    def _dispatch(self, message: dict) -> None:
        """Deserialise a raw pub/sub message and call registered handlers."""
        try:
            raw = json.loads(message["data"])
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse message data: %s | error: %s", message, exc)
            return

        try:
            event_type = EventType(raw["event_type"])
        except (KeyError, ValueError) as exc:
            logger.warning("Unknown or missing event_type in message: %s | error: %s", raw, exc)
            return

        try:
            event = Event(
                event_id=raw["event_id"],
                event_type=event_type,
                timestamp=raw["timestamp"],
                store_id=raw["store_id"],
                data=raw.get("data", {}),
                metadata=raw.get("metadata", {}),
            )
        except (KeyError, TypeError) as exc:
            logger.warning("Failed to reconstruct Event from message: %s | error: %s", raw, exc)
            return

        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                if self._monitor is not None:
                    from events.monitoring import track_event
                    with track_event(self._monitor, event):
                        handler(event)
                else:
                    handler(event)
            except Exception as exc:
                handler_name = getattr(handler, "__name__", repr(handler))
                logger.error(
                    "Handler %s raised an error for event %s: %s",
                    handler_name,
                    event.event_id,
                    exc,
                )
                if self._dlq is not None:
                    try:
                        self._dlq.push(event, str(exc), handler_name)
                    except Exception as dlq_exc:
                        logger.error(
                            "Failed to push event %s to DLQ: %s",
                            event.event_id,
                            dlq_exc,
                        )

    # ------------------------------------------------------------------
    # Thread management
    # ------------------------------------------------------------------

    def start(self) -> threading.Thread:
        """Start the subscriber in a background daemon thread.

        Returns:
            The started Thread instance.
        """
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self.subscribe_and_listen,
            name="EventSubscriber",
            daemon=True,
        )
        self._thread.start()
        logger.info("EventSubscriber background thread started.")
        return self._thread

    def stop(self) -> None:
        """Gracefully stop the subscriber listen loop.

        Signals the loop to exit and unsubscribes from all channels.
        """
        self._stop_event.set()
        if self._pubsub is not None:
            try:
                self._pubsub.unsubscribe()
                self._pubsub.close()
            except Exception as exc:  # pragma: no cover
                logger.warning("Error while closing pubsub: %s", exc)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("EventSubscriber stopped.")


# ---------------------------------------------------------------------------
# Default stub handlers
# ---------------------------------------------------------------------------

def handle_order_created(event: Event) -> None:
    logger.info("[order.created] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


def handle_order_updated(event: Event) -> None:
    logger.info("[order.updated] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


def handle_order_completed(event: Event) -> None:
    logger.info("[order.completed] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


def handle_payment_received(event: Event) -> None:
    """Recalculate credit score when a payment is received (4.9)."""
    logger.info("[payment.received] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)
    customer_id = (event.data or {}).get("customer_id")
    if not customer_id:
        return
    try:
        import os
        from supabase import create_client
        from agents.intelligent_credit_agent import (
            calculate_credit_score,
            calculate_credit_limit,
            auto_restore_credit,
        )
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        new_score = calculate_credit_score(customer_id, db_conn=supabase)
        new_limit = calculate_credit_limit(new_score)
        supabase.table("customers").update(
            {"credit_score": int(new_score), "credit_limit": new_limit}
        ).eq("id", customer_id).execute()
        # Auto-restore credit if it was suspended
        customer_result = (
            supabase.table("customers")
            .select("credit_suspended")
            .eq("id", customer_id)
            .single()
            .execute()
        )
        if customer_result.data and customer_result.data.get("credit_suspended"):
            auto_restore_credit(customer_id, db_conn=supabase)
        logger.info(
            "Credit score updated for customer %s: score=%.1f limit=%.0f",
            customer_id, new_score, new_limit,
        )
    except Exception as exc:
        logger.error("handle_payment_received credit update error: %s", exc)


def handle_payment_overdue(event: Event) -> None:
    logger.info("[payment.overdue] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


def handle_inventory_low(event: Event) -> None:
    logger.info("[inventory.low] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


def handle_inventory_critical(event: Event) -> None:
    logger.info("[inventory.critical] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


def handle_customer_inactive(event: Event) -> None:
    logger.info("[customer.inactive] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


def handle_customer_churn_risk(event: Event) -> None:
    logger.info("[customer.churn_risk] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


def handle_product_trending(event: Event) -> None:
    logger.info("[product.trending] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


def handle_fraud_detected(event: Event) -> None:
    logger.info("[fraud.detected] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


def handle_credit_suspended(event: Event) -> None:
    logger.info("[credit.suspended] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


def handle_credit_restored(event: Event) -> None:
    logger.info("[credit.restored] event_id=%s store_id=%s data=%s", event.event_id, event.store_id, event.data)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_default_subscriber(redis_client: redis.Redis) -> EventSubscriber:
    """Create an EventSubscriber with all default stub handlers registered.

    Args:
        redis_client: A synchronous Redis client.

    Returns:
        A fully configured EventSubscriber ready to call ``start()``.
    """
    subscriber = EventSubscriber(redis_client)

    subscriber.register(EventType.ORDER_CREATED, handle_order_created)
    subscriber.register(EventType.ORDER_UPDATED, handle_order_updated)
    subscriber.register(EventType.ORDER_COMPLETED, handle_order_completed)
    subscriber.register(EventType.PAYMENT_RECEIVED, handle_payment_received)
    subscriber.register(EventType.PAYMENT_OVERDUE, handle_payment_overdue)
    subscriber.register(EventType.INVENTORY_LOW, handle_inventory_low)
    subscriber.register(EventType.INVENTORY_CRITICAL, handle_inventory_critical)
    subscriber.register(EventType.CUSTOMER_INACTIVE, handle_customer_inactive)
    subscriber.register(EventType.CUSTOMER_CHURN_RISK, handle_customer_churn_risk)
    subscriber.register(EventType.PRODUCT_TRENDING, handle_product_trending)
    subscriber.register(EventType.FRAUD_DETECTED, handle_fraud_detected)
    subscriber.register(EventType.CREDIT_SUSPENDED, handle_credit_suspended)
    subscriber.register(EventType.CREDIT_RESTORED, handle_credit_restored)

    return subscriber
