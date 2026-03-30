"""
End-to-end tests for the event flow:
  EventType / create_event → EventPublisher → EventSubscriber → DeadLetterQueue
"""

from __future__ import annotations

import json
import logging
import sys
import os

import pytest

# ---------------------------------------------------------------------------
# Make agent-service importable when running from the repo root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import fakeredis
    _FAKEREDIS_AVAILABLE = True
except ImportError:
    _FAKEREDIS_AVAILABLE = False

from unittest.mock import MagicMock, patch, call

from events.event_types import Event, EventType, create_event
from events.publisher import EventPublisher, WILDCARD_CHANNEL
from events.subscriber import EventSubscriber
from events.dead_letter_queue import DeadLetterQueue, DLQ_KEY, MAX_RETRIES


# ---------------------------------------------------------------------------
# Minimal in-memory Redis stub (list + pubsub operations only)
# ---------------------------------------------------------------------------

class _FakeRedis:
    """Minimal stateful Redis stub supporting list and publish operations."""

    def __init__(self):
        self._lists: dict[str, list[str]] = {}
        self._publish_calls: list[tuple[str, str]] = []

    # List operations
    def rpush(self, key: str, *values: str) -> int:
        self._lists.setdefault(key, []).extend(values)
        return len(self._lists[key])

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        items = self._lists.get(key, [])
        if end == -1:
            return list(items[start:])
        return list(items[start: end + 1])

    def lrem(self, key: str, count: int, value: str) -> int:
        items = self._lists.get(key, [])
        removed = 0
        new_items = []
        for item in items:
            if item == value and (count == 0 or removed < abs(count)):
                removed += 1
            else:
                new_items.append(item)
        self._lists[key] = new_items
        return removed

    def llen(self, key: str) -> int:
        return len(self._lists.get(key, []))

    # Pub/sub
    def publish(self, channel: str, message: str) -> int:
        self._publish_calls.append((channel, message))
        return 1

    def pubsub(self):
        return MagicMock()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def redis_client():
    """Return a fake or mock Redis client."""
    if _FAKEREDIS_AVAILABLE:
        return fakeredis.FakeRedis(decode_responses=True)
    return _FakeRedis()


@pytest.fixture()
def publisher(redis_client):
    return EventPublisher(redis_client)


@pytest.fixture()
def dlq(redis_client):
    return DeadLetterQueue(redis_client)


@pytest.fixture()
def sample_event():
    return create_event(
        event_type=EventType.ORDER_CREATED,
        store_id="store-123",
        data={"order_id": "ord-001", "amount": 99.99},
    )


# ---------------------------------------------------------------------------
# 1. test_create_event
# ---------------------------------------------------------------------------

def test_create_event():
    event = create_event(
        event_type=EventType.ORDER_CREATED,
        store_id="store-abc",
        data={"order_id": "ord-42"},
    )

    assert isinstance(event, Event)
    assert event.event_type == EventType.ORDER_CREATED
    assert event.store_id == "store-abc"
    assert event.data == {"order_id": "ord-42"}
    assert event.metadata["source"] == "agent-service"
    assert event.metadata["version"] == "1.0"
    # event_id must be a non-empty string (UUID)
    assert isinstance(event.event_id, str) and len(event.event_id) == 36
    # timestamp must be a non-empty ISO string
    assert isinstance(event.timestamp, str) and "T" in event.timestamp


# ---------------------------------------------------------------------------
# 2. test_event_type_enum
# ---------------------------------------------------------------------------

def test_event_type_enum():
    expected = {
        "ORDER_CREATED",
        "ORDER_UPDATED",
        "ORDER_COMPLETED",
        "PAYMENT_RECEIVED",
        "PAYMENT_OVERDUE",
        "INVENTORY_LOW",
        "INVENTORY_CRITICAL",
        "CUSTOMER_INACTIVE",
        "CUSTOMER_CHURN_RISK",
        "PRODUCT_TRENDING",
        "FRAUD_DETECTED",
    }
    actual = {member.name for member in EventType}
    assert actual == expected
    assert len(actual) == 11


# ---------------------------------------------------------------------------
# 3. test_publisher_publish
# ---------------------------------------------------------------------------

def test_publisher_publish(sample_event):
    mock_redis = MagicMock()
    mock_redis.publish.return_value = 1

    pub = EventPublisher(mock_redis)
    pub.publish(sample_event)

    expected_channel = sample_event.event_type.value  # "order.created"
    calls = mock_redis.publish.call_args_list
    channels_called = [c.args[0] for c in calls]

    assert expected_channel in channels_called
    assert WILDCARD_CHANNEL in channels_called
    assert mock_redis.publish.call_count == 2


# ---------------------------------------------------------------------------
# 4. test_publisher_publish_raw
# ---------------------------------------------------------------------------

def test_publisher_publish_raw():
    mock_redis = MagicMock()
    mock_redis.publish.return_value = 1

    pub = EventPublisher(mock_redis)
    data = {"key": "value", "number": 42}
    pub.publish_raw("my.channel", data)

    mock_redis.publish.assert_called_once()
    channel_arg, payload_arg = mock_redis.publish.call_args.args
    assert channel_arg == "my.channel"
    assert json.loads(payload_arg) == data


# ---------------------------------------------------------------------------
# 5. test_publisher_handles_connection_error
# ---------------------------------------------------------------------------

def test_publisher_handles_connection_error(sample_event):
    import redis as redis_lib

    mock_redis = MagicMock()
    mock_redis.publish.side_effect = redis_lib.ConnectionError("refused")

    pub = EventPublisher(mock_redis)
    result = pub.publish(sample_event)

    assert result == 0  # must not raise, must return 0


# ---------------------------------------------------------------------------
# 6. test_subscriber_register_and_dispatch
# ---------------------------------------------------------------------------

def test_subscriber_register_and_dispatch(redis_client, sample_event):
    import dataclasses

    subscriber = EventSubscriber(redis_client)
    received: list[Event] = []

    subscriber.register(EventType.ORDER_CREATED, received.append)

    # Build the raw pub/sub message the subscriber would receive
    raw_dict = dataclasses.asdict(sample_event)
    raw_dict["event_type"] = sample_event.event_type.value
    message = {
        "type": "message",
        "channel": sample_event.event_type.value,
        "data": json.dumps(raw_dict),
    }

    subscriber._dispatch(message)

    assert len(received) == 1
    dispatched = received[0]
    assert dispatched.event_id == sample_event.event_id
    assert dispatched.event_type == EventType.ORDER_CREATED
    assert dispatched.store_id == sample_event.store_id


# ---------------------------------------------------------------------------
# 7. test_subscriber_dlq_on_handler_failure
# ---------------------------------------------------------------------------

def test_subscriber_dlq_on_handler_failure(redis_client, sample_event):
    import dataclasses

    dlq = DeadLetterQueue(redis_client)
    subscriber = EventSubscriber(redis_client, dlq=dlq)

    def bad_handler(event: Event) -> None:
        raise RuntimeError("handler exploded")

    subscriber.register(EventType.ORDER_CREATED, bad_handler)

    raw_dict = dataclasses.asdict(sample_event)
    raw_dict["event_type"] = sample_event.event_type.value
    message = {
        "type": "message",
        "channel": sample_event.event_type.value,
        "data": json.dumps(raw_dict),
    }

    subscriber._dispatch(message)

    entries = dlq.get_all()
    assert len(entries) == 1
    assert entries[0]["event"]["event_id"] == sample_event.event_id
    assert "handler exploded" in entries[0]["error"]


# ---------------------------------------------------------------------------
# 8. test_dlq_push_and_get
# ---------------------------------------------------------------------------

def test_dlq_push_and_get(dlq, sample_event):
    dlq.push(sample_event, "some error", "my_handler")

    entries = dlq.get_all()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["event"]["event_id"] == sample_event.event_id
    assert entry["error"] == "some error"
    assert entry["handler_name"] == "my_handler"
    assert entry["retry_count"] == 0


# ---------------------------------------------------------------------------
# 9. test_dlq_retry
# ---------------------------------------------------------------------------

def test_dlq_retry(dlq, sample_event):
    dlq.push(sample_event, "error", "handler")

    mock_publisher = MagicMock()
    result = dlq.retry(sample_event.event_id, mock_publisher)

    assert result is True
    mock_publisher.publish.assert_called_once()
    published_event = mock_publisher.publish.call_args.args[0]
    assert published_event.event_id == sample_event.event_id

    # Event should be removed from DLQ after retry
    assert dlq.get_all() == []


# ---------------------------------------------------------------------------
# 10. test_dlq_remove
# ---------------------------------------------------------------------------

def test_dlq_remove(dlq, sample_event):
    dlq.push(sample_event, "error", "handler")
    assert len(dlq.get_all()) == 1

    result = dlq.remove(sample_event.event_id)

    assert result is True
    assert dlq.get_all() == []


# ---------------------------------------------------------------------------
# 11. test_dlq_max_retries
# ---------------------------------------------------------------------------

def test_dlq_max_retries(dlq, sample_event, caplog):
    # Push the event once (retry_count = 0)
    dlq.push(sample_event, "error 1", "handler")

    # Simulate MAX_RETRIES - 1 additional failures so retry_count reaches MAX_RETRIES
    with caplog.at_level(logging.CRITICAL):
        for i in range(MAX_RETRIES):
            dlq.push(sample_event, f"error {i + 2}", "handler")

    critical_messages = [r for r in caplog.records if r.levelno == logging.CRITICAL]
    assert len(critical_messages) >= 1
    assert any(sample_event.event_id in r.message for r in critical_messages)
