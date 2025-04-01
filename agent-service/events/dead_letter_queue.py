"""
DeadLetterQueue: stores failed events in Redis for later inspection or retry.

Failed events are stored as JSON objects in a Redis list under the key
"dlq:failed_events".  Each entry captures the original event, the error
message, which handler failed, retry count, and timestamps.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from datetime import datetime, timezone
from typing import Any

import redis

from events.event_types import Event, EventType

logger = logging.getLogger(__name__)

DLQ_KEY = "dlq:failed_events"
MAX_RETRIES = 3


class DeadLetterQueue:
    """Dead letter queue backed by a Redis list."""

    def __init__(self, redis_client: redis.Redis) -> None:
        """
        Args:
            redis_client: A synchronous Redis client.
        """
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _serialize_entry(self, entry: dict[str, Any]) -> str:
        return json.dumps(entry)

    def _deserialize_entry(self, raw: str) -> dict[str, Any]:
        return json.loads(raw)

    def _event_to_dict(self, event: Event) -> dict[str, Any]:
        raw = dataclasses.asdict(event)
        raw["event_type"] = event.event_type.value
        return raw

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push(self, event: Event, error: str, handler_name: str) -> None:
        """Store a failed event in the DLQ.

        If an entry for this event_id already exists (e.g. a retry failed),
        its retry_count and last_failed_at are updated in place.  Otherwise
        a new entry is appended.

        Args:
            event:        The Event that failed to be processed.
            error:        The error message from the exception.
            handler_name: Name of the handler that raised the error.
        """
        now = self._now_iso()

        # Check if this event is already in the DLQ (previous retry attempt)
        existing_entries = self._redis.lrange(DLQ_KEY, 0, -1)
        for raw in existing_entries:
            entry = self._deserialize_entry(raw)
            if entry.get("event", {}).get("event_id") == event.event_id:
                # Update existing entry
                entry["retry_count"] += 1
                entry["last_failed_at"] = now
                entry["error"] = error

                if entry["retry_count"] >= MAX_RETRIES:
                    logger.critical(
                        "Event %s has reached max retries (%d). "
                        "Leaving in DLQ for manual review. Last error: %s",
                        event.event_id,
                        MAX_RETRIES,
                        error,
                    )

                # Replace old entry with updated one
                self._redis.lrem(DLQ_KEY, 1, raw)
                self._redis.rpush(DLQ_KEY, self._serialize_entry(entry))
                logger.warning(
                    "Updated DLQ entry for event %s (retry_count=%d)",
                    event.event_id,
                    entry["retry_count"],
                )
                return

        # New entry
        entry: dict[str, Any] = {
            "event": self._event_to_dict(event),
            "error": error,
            "handler_name": handler_name,
            "retry_count": 0,
            "first_failed_at": now,
            "last_failed_at": now,
        }
        self._redis.rpush(DLQ_KEY, self._serialize_entry(entry))
        logger.warning(
            "Pushed event %s to DLQ (handler=%s, error=%s)",
            event.event_id,
            handler_name,
            error,
        )

    def get_all(self) -> list[dict]:
        """Return all items currently in the DLQ.

        Returns:
            List of DLQ entry dicts (deserialized from JSON).
        """
        raw_items = self._redis.lrange(DLQ_KEY, 0, -1)
        return [self._deserialize_entry(raw) for raw in raw_items]

    def retry(self, event_id: str, publisher: Any) -> bool:
        """Re-publish a specific event by event_id and remove it from the DLQ.

        Args:
            event_id:  The event_id of the event to retry.
            publisher: An EventPublisher instance used to re-publish the event.

        Returns:
            True if the event was found and successfully re-published,
            False otherwise.
        """
        raw_items = self._redis.lrange(DLQ_KEY, 0, -1)
        for raw in raw_items:
            entry = self._deserialize_entry(raw)
            if entry.get("event", {}).get("event_id") == event_id:
                event_dict = entry["event"]
                try:
                    event = Event(
                        event_id=event_dict["event_id"],
                        event_type=EventType(event_dict["event_type"]),
                        timestamp=event_dict["timestamp"],
                        store_id=event_dict["store_id"],
                        data=event_dict.get("data", {}),
                        metadata=event_dict.get("metadata", {}),
                    )
                    publisher.publish(event)
                    self._redis.lrem(DLQ_KEY, 1, raw)
                    logger.info("Retried and removed event %s from DLQ", event_id)
                    return True
                except Exception as exc:
                    logger.error(
                        "Failed to retry event %s from DLQ: %s", event_id, exc
                    )
                    return False

        logger.warning("Event %s not found in DLQ", event_id)
        return False

    def retry_all(self, publisher: Any) -> tuple[int, int]:
        """Retry all events in the DLQ.

        Args:
            publisher: An EventPublisher instance used to re-publish events.

        Returns:
            A (success_count, fail_count) tuple.
        """
        raw_items = self._redis.lrange(DLQ_KEY, 0, -1)
        success_count = 0
        fail_count = 0

        for raw in raw_items:
            entry = self._deserialize_entry(raw)
            event_id = entry.get("event", {}).get("event_id", "unknown")
            event_dict = entry["event"]
            try:
                event = Event(
                    event_id=event_dict["event_id"],
                    event_type=EventType(event_dict["event_type"]),
                    timestamp=event_dict["timestamp"],
                    store_id=event_dict["store_id"],
                    data=event_dict.get("data", {}),
                    metadata=event_dict.get("metadata", {}),
                )
                publisher.publish(event)
                self._redis.lrem(DLQ_KEY, 1, raw)
                success_count += 1
                logger.info("Retried event %s from DLQ successfully", event_id)
            except Exception as exc:
                fail_count += 1
                logger.error("Failed to retry event %s from DLQ: %s", event_id, exc)

        logger.info(
            "retry_all complete: %d succeeded, %d failed", success_count, fail_count
        )
        return success_count, fail_count

    def remove(self, event_id: str) -> bool:
        """Remove an event from the DLQ without retrying.

        Args:
            event_id: The event_id of the event to remove.

        Returns:
            True if the event was found and removed, False otherwise.
        """
        raw_items = self._redis.lrange(DLQ_KEY, 0, -1)
        for raw in raw_items:
            entry = self._deserialize_entry(raw)
            if entry.get("event", {}).get("event_id") == event_id:
                self._redis.lrem(DLQ_KEY, 1, raw)
                logger.info("Removed event %s from DLQ", event_id)
                return True

        logger.warning("Event %s not found in DLQ for removal", event_id)
        return False

    def size(self) -> int:
        """Return the number of items currently in the DLQ.

        Returns:
            Integer count of DLQ entries.
        """
        return self._redis.llen(DLQ_KEY)
