"""
EventPublisher: publishes domain events to Redis pub/sub channels.

Each event is published to:
  - A channel named after the event type  (e.g. "order.created")
  - A wildcard channel "events.all" for catch-all subscribers
"""

from __future__ import annotations

import dataclasses
import json
import logging
from typing import Any

import redis

from events.event_types import Event

logger = logging.getLogger(__name__)

WILDCARD_CHANNEL = "events.all"


def _serialize_event(event: Event) -> str:
    """Convert an Event dataclass to a JSON string.

    EventType enum values are serialised as their .value string so the
    resulting JSON is plain text and easy to consume by any subscriber.
    """
    raw: dict[str, Any] = dataclasses.asdict(event)
    # dataclasses.asdict keeps enum members as-is; convert to string value.
    raw["event_type"] = event.event_type.value
    return json.dumps(raw)


class EventPublisher:
    """Publishes events to Redis pub/sub channels."""

    def __init__(self, redis_client: redis.Redis) -> None:
        """
        Args:
            redis_client: A synchronous Redis client (e.g. from redis_client.get_sync_client()).
        """
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish(self, event: Event) -> int:
        """Serialise and publish an Event to Redis.

        Publishes to two channels:
          1. The channel named after the event type (e.g. "order.created").
          2. The wildcard channel "events.all".

        Args:
            event: The Event instance to publish.

        Returns:
            Total number of subscribers that received the message across
            both channels (sum of both publish calls).

        Raises:
            Nothing – connection errors are caught and logged; 0 is returned.
        """
        channel = event.event_type.value
        payload = _serialize_event(event)

        try:
            count_specific = self._redis.publish(channel, payload)
            count_all = self._redis.publish(WILDCARD_CHANNEL, payload)
            total = (count_specific or 0) + (count_all or 0)
            logger.debug(
                "Published event %s to '%s' and '%s' (%d subscriber(s))",
                event.event_id,
                channel,
                WILDCARD_CHANNEL,
                total,
            )
            return total
        except redis.ConnectionError as exc:
            logger.error(
                "Redis connection error while publishing event %s to '%s': %s",
                event.event_id,
                channel,
                exc,
            )
            return 0
        except Exception as exc:  # pragma: no cover
            logger.error(
                "Unexpected error while publishing event %s: %s",
                event.event_id,
                exc,
            )
            return 0

    def publish_raw(self, channel: str, data: dict[str, Any]) -> int:
        """Low-level publish: serialise *data* as JSON and send to *channel*.

        Args:
            channel: Redis pub/sub channel name.
            data:    Arbitrary dict that will be JSON-serialised.

        Returns:
            Number of subscribers that received the message, or 0 on error.
        """
        try:
            payload = json.dumps(data)
            count = self._redis.publish(channel, payload)
            logger.debug(
                "Published raw message to '%s' (%d subscriber(s))",
                channel,
                count or 0,
            )
            return count or 0
        except redis.ConnectionError as exc:
            logger.error(
                "Redis connection error while publishing raw message to '%s': %s",
                channel,
                exc,
            )
            return 0
        except Exception as exc:  # pragma: no cover
            logger.error(
                "Unexpected error while publishing raw message to '%s': %s",
                channel,
                exc,
            )
            return 0
