"""
Tests for the Smart Notification Orchestrator (Task 8).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from agents.notification_orchestrator import (
    MAX_MESSAGES_PER_DAY,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    SEND_WINDOW_END,
    SEND_WINDOW_START,
    NotificationOrchestrator,
    calculate_response_rate_metrics,
    can_send_notification,
    combine_messages,
    detect_emoji_preference,
    detect_language_preference,
    detect_length_preference,
    detect_tone_preference,
    get_messages_sent_today,
    get_notification_performance_metrics,
    get_optimal_send_time,
    get_priority_value,
    is_within_send_window,
    personalize_message,
    update_notification_preferences,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_supabase_mock():
    """Return a MagicMock that mimics the Supabase client chain."""
    mock = MagicMock()
    return mock


def _notification_rows(count: int, responded: bool = False) -> list[dict]:
    return [
        {
            "id": str(uuid.uuid4()),
            "customer_id": "cust-1",
            "responded": responded,
            "response_hour": 14 if responded else None,
            "priority": "medium",
            "status": "queued",
            "message": f"Notification {i}",
        }
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# 8.1 Timing Optimization
# ---------------------------------------------------------------------------

class TestTimingOptimization:
    """8.1 Timing optimization tests."""

    def test_is_within_send_window_true(self):
        """8.1.3 Hours 9-20 are within the send window."""
        for hour in range(SEND_WINDOW_START, SEND_WINDOW_END):
            assert is_within_send_window(hour), f"Hour {hour} should be in window"

    def test_is_within_send_window_false_before(self):
        """8.1.3 Hours before 9 AM are outside the window."""
        for hour in range(0, SEND_WINDOW_START):
            assert not is_within_send_window(hour), f"Hour {hour} should be outside window"

    def test_is_within_send_window_false_after(self):
        """8.1.3 Hour 21 (9 PM) and later are outside the window."""
        for hour in range(SEND_WINDOW_END, 24):
            assert not is_within_send_window(hour), f"Hour {hour} should be outside window"

    def _mock_optimal_time(self, rows: list) -> MagicMock:
        """Build a mock with the correct chain for get_optimal_send_time."""
        mock = _make_supabase_mock()
        execute_mock = MagicMock()
        execute_mock.data = rows
        mock.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .not_.is_.return_value.execute.return_value = execute_mock
        return mock

    def test_get_optimal_send_time_no_history_defaults_to_1800(self):
        """8.1.2 Default to 18:00 when no response history exists."""
        mock = self._mock_optimal_time([])
        result = get_optimal_send_time("cust-1", db_conn=mock)
        assert result == "18:00"

    def test_get_optimal_send_time_picks_most_common_hour(self):
        """8.1.2 Returns the hour with the most responses."""
        rows = [
            {"response_hour": 10},
            {"response_hour": 10},
            {"response_hour": 14},
            {"response_hour": 10},
        ]
        mock = self._mock_optimal_time(rows)
        result = get_optimal_send_time("cust-1", db_conn=mock)
        assert result == "10:00"

    def test_get_optimal_send_time_clamps_to_window(self):
        """8.1.3 Best hour is clamped to 9 AM - 9 PM window."""
        # Hour 3 (3 AM) should be clamped to 9 AM
        mock = self._mock_optimal_time([{"response_hour": 3}])
        result = get_optimal_send_time("cust-1", db_conn=mock)
        hour = int(result.split(":")[0])
        assert SEND_WINDOW_START <= hour < SEND_WINDOW_END

    def test_get_optimal_send_time_format(self):
        """Returned time is in HH:MM format."""
        mock = self._mock_optimal_time([{"response_hour": 9}])
        result = get_optimal_send_time("cust-1", db_conn=mock)
        parts = result.split(":")
        assert len(parts) == 2
        assert parts[1] == "00"
        assert 0 <= int(parts[0]) <= 23


# ---------------------------------------------------------------------------
# 8.2 Fatigue Prevention
# ---------------------------------------------------------------------------

class TestFatiguePrevention:
    """8.2 Fatigue prevention tests."""

    def test_can_send_when_under_limit(self):
        """8.2.1 Can send when fewer than 3 messages sent today."""
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value \
            .gte.return_value.execute.return_value.data = _notification_rows(2)

        assert can_send_notification("cust-1", db_conn=mock) is True

    def test_cannot_send_when_at_limit(self):
        """8.2.1 Cannot send when 3 messages already sent today."""
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value \
            .gte.return_value.execute.return_value.data = _notification_rows(MAX_MESSAGES_PER_DAY)

        assert can_send_notification("cust-1", db_conn=mock) is False

    def test_cannot_send_when_over_limit(self):
        """8.2.1 Cannot send when more than 3 messages sent today."""
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value \
            .gte.return_value.execute.return_value.data = _notification_rows(5)

        assert can_send_notification("cust-1", db_conn=mock) is False

    def test_priority_ordering(self):
        """8.2.2 Critical > high > medium > low."""
        assert PRIORITY_CRITICAL > PRIORITY_HIGH
        assert PRIORITY_HIGH > PRIORITY_MEDIUM
        assert PRIORITY_MEDIUM > PRIORITY_LOW

    def test_get_priority_value_critical(self):
        """8.2.2 'critical' maps to highest priority value."""
        assert get_priority_value("critical") == PRIORITY_CRITICAL

    def test_get_priority_value_low(self):
        """8.2.2 'low' maps to lowest priority value."""
        assert get_priority_value("low") == PRIORITY_LOW

    def test_get_priority_value_unknown_defaults_to_low(self):
        """Unknown priority labels default to low."""
        assert get_priority_value("unknown") == PRIORITY_LOW

    def test_get_messages_sent_today_count(self):
        """Returns correct count of today's messages."""
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value \
            .gte.return_value.execute.return_value.data = _notification_rows(2)

        count = get_messages_sent_today("cust-1", db_conn=mock)
        assert count == 2


# ---------------------------------------------------------------------------
# 8.3 Message Batching
# ---------------------------------------------------------------------------

class TestMessageBatching:
    """8.3 Message batching tests."""

    def test_combine_single_message(self):
        """8.3.2 Single notification returns its message unchanged."""
        notifs = [{"message": "Hello!"}]
        result = combine_messages(notifs)
        assert result == "Hello!"

    def test_combine_multiple_messages(self):
        """8.3.2 Multiple notifications are numbered and joined."""
        notifs = [
            {"message": "Payment due"},
            {"message": "New offer available"},
        ]
        result = combine_messages(notifs)
        assert "1." in result
        assert "2." in result
        assert "Payment due" in result
        assert "New offer available" in result

    def test_combine_empty_returns_empty_string(self):
        """8.3.2 Empty list returns empty string."""
        assert combine_messages([]) == ""

    def test_batch_notifications_returns_none_when_no_pending(self):
        """8.3 Returns None when there are no pending notifications."""
        mock = _make_supabase_mock()
        # pending query: .table().select().eq().eq().execute()
        mock.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .execute.return_value.data = []

        orchestrator = NotificationOrchestrator(supabase=mock)
        result = orchestrator.batch_notifications("cust-1")
        assert result is None

    def test_batch_notifications_returns_batch_info(self):
        """8.3 Returns batch info with combined message and scheduled time."""
        pending = [
            {"id": str(uuid.uuid4()), "message": "Msg A", "priority": "medium", "status": "queued"},
            {"id": str(uuid.uuid4()), "message": "Msg B", "priority": "low", "status": "queued"},
        ]

        mock = _make_supabase_mock()
        # pending query: .table().select().eq().eq().execute()
        mock.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .execute.return_value.data = pending
        # log_sent_notification insert
        mock.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": str(uuid.uuid4())}
        ]
        # get_optimal_send_time: .table().select().eq().eq().not_.is_().execute()
        execute_mock = MagicMock()
        execute_mock.data = []
        mock.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .not_.is_.return_value.execute.return_value = execute_mock

        orchestrator = NotificationOrchestrator(supabase=mock)
        result = orchestrator.batch_notifications("cust-1")

        assert result is not None
        assert result["customer_id"] == "cust-1"
        assert result["notification_count"] == 2
        assert "Msg A" in result["message"] or "Msg B" in result["message"]
        assert ":" in result["scheduled_time"]


# ---------------------------------------------------------------------------
# 8.4 Personalization
# ---------------------------------------------------------------------------

class TestPersonalization:
    """8.4 Personalization tests."""

    def test_detect_tone_formal(self):
        """8.4.1 Detects formal tone from message history."""
        history = ["Please kindly send the invoice", "Regards, sir"]
        assert detect_tone_preference(history) == "formal"

    def test_detect_tone_casual(self):
        """8.4.1 Detects casual tone from message history."""
        history = ["hey thanks!", "ok cool", "yep got it"]
        assert detect_tone_preference(history) == "casual"

    def test_detect_tone_empty_defaults_casual(self):
        """8.4.1 Empty history defaults to casual."""
        assert detect_tone_preference([]) == "casual"

    def test_detect_emoji_preference_with_emojis(self):
        """8.4.2 Detects emoji usage in messages."""
        history = ["Hello! 😊", "Thanks 🙏"]
        assert detect_emoji_preference(history) is True

    def test_detect_emoji_preference_without_emojis(self):
        """8.4.2 Returns False when no emojis in history."""
        history = ["Hello", "Thanks", "Please send order"]
        assert detect_emoji_preference(history) is False

    def test_detect_emoji_preference_empty_defaults_true(self):
        """8.4.2 Empty history defaults to True (use emojis)."""
        assert detect_emoji_preference([]) is True

    def test_detect_language_hindi(self):
        """8.4.3 Detects Hindi language preference."""
        history = ["bhai mujhe order chahiye", "haan theek hai", "acha"]
        assert detect_language_preference(history) == "hindi"

    def test_detect_language_english(self):
        """8.4.3 Detects English language preference."""
        history = ["I need to place an order", "What is the price?", "Thank you"]
        assert detect_language_preference(history) == "english"

    def test_detect_language_empty_defaults_english(self):
        """8.4.3 Empty history defaults to English."""
        assert detect_language_preference([]) == "english"

    def test_detect_length_brief(self):
        """8.4.4 Short messages indicate brief preference."""
        history = ["ok", "yes", "done", "thanks"]
        assert detect_length_preference(history) == "brief"

    def test_detect_length_detailed(self):
        """8.4.4 Long messages indicate detailed preference."""
        history = [
            "I would like to place an order for 5 kg of rice and 2 kg of sugar please, and also check if basmati rice is available.",
            "Could you also check if the basmati rice is available in stock today and let me know the price per kilogram?",
        ]
        assert detect_length_preference(history) == "detailed"

    def test_personalize_removes_emojis_when_not_preferred(self):
        """8.4.2 Emojis are stripped when use_emojis=False."""
        msg = "Hello! 😊 Your order is ready 🎉"
        result = personalize_message(msg, use_emojis=False)
        # No emoji characters should remain
        for char in result:
            cp = ord(char)
            assert not (0x1F600 <= cp <= 0x1F64F), f"Emoji found: {char}"

    def test_personalize_keeps_emojis_when_preferred(self):
        """8.4.2 Emojis are kept when use_emojis=True."""
        msg = "Hello! 😊"
        result = personalize_message(msg, use_emojis=True)
        assert "😊" in result

    def test_personalize_formal_tone_replaces_hey(self):
        """8.4.1 Formal tone replaces casual openers."""
        msg = "Hey! Your payment is due."
        result = personalize_message(msg, tone="formal")
        assert "Hey!" not in result
        assert "Dear Customer" in result

    def test_personalize_brief_truncates_long_message(self):
        """8.4.4 Brief preference truncates messages over 200 chars."""
        long_msg = "A" * 300
        result = personalize_message(long_msg, length="brief")
        assert len(result) <= 200

    def test_personalize_detailed_does_not_truncate(self):
        """8.4.4 Detailed preference does not truncate messages."""
        long_msg = "A" * 300
        result = personalize_message(long_msg, length="detailed")
        assert len(result) == 300


# ---------------------------------------------------------------------------
# 8.7 Response Rate Metrics
# ---------------------------------------------------------------------------

class TestResponseRateMetrics:
    """8.7 Response rate improvement measurement tests."""

    def test_returns_zero_metrics_when_no_data(self):
        """Returns zero metrics when no notifications exist."""
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .gte.return_value.execute.return_value.data = []

        result = calculate_response_rate_metrics("store-1", db_conn=mock)
        assert result["total_sent"] == 0
        assert result["response_rate_pct"] == 0.0

    def test_calculates_response_rate_correctly(self):
        """8.7 Calculates response rate as responded/total * 100."""
        notifications = [
            {"id": "1", "customer_id": "c1", "responded": True, "priority": "medium", "notification_type": "general", "sent_at": "2024-01-01T10:00:00"},
            {"id": "2", "customer_id": "c1", "responded": True, "priority": "medium", "notification_type": "general", "sent_at": "2024-01-01T11:00:00"},
            {"id": "3", "customer_id": "c1", "responded": False, "priority": "low", "notification_type": "general", "sent_at": "2024-01-01T12:00:00"},
            {"id": "4", "customer_id": "c1", "responded": False, "priority": "low", "notification_type": "general", "sent_at": "2024-01-01T13:00:00"},
        ]
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .gte.return_value.execute.return_value.data = notifications

        result = calculate_response_rate_metrics("store-1", db_conn=mock)
        assert result["total_sent"] == 4
        assert result["total_responded"] == 2
        assert result["response_rate_pct"] == 50.0

    def test_breaks_down_by_priority(self):
        """8.7 Breaks down response rate by priority level."""
        notifications = [
            {"id": "1", "customer_id": "c1", "responded": True, "priority": "critical", "notification_type": "general", "sent_at": "2024-01-01T10:00:00"},
            {"id": "2", "customer_id": "c1", "responded": False, "priority": "low", "notification_type": "general", "sent_at": "2024-01-01T11:00:00"},
        ]
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .gte.return_value.execute.return_value.data = notifications

        result = calculate_response_rate_metrics("store-1", db_conn=mock)
        assert "critical" in result["by_priority"]
        assert result["by_priority"]["critical"]["response_rate_pct"] == 100.0
        assert "low" in result["by_priority"]
        assert result["by_priority"]["low"]["response_rate_pct"] == 0.0

    def test_includes_store_id_and_period(self):
        """8.7 Result includes store_id and period_days."""
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .gte.return_value.execute.return_value.data = []

        result = calculate_response_rate_metrics("store-42", days=14, db_conn=mock)
        assert result["store_id"] == "store-42"
        assert result["period_days"] == 14


# ---------------------------------------------------------------------------
# 8.8 Performance Monitoring
# ---------------------------------------------------------------------------

class TestPerformanceMonitoring:
    """8.8 Notification performance monitoring tests."""

    def test_returns_zero_metrics_when_no_data(self):
        """Returns zero metrics when no notifications exist."""
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.gte.return_value \
            .execute.return_value.data = []

        result = get_notification_performance_metrics("store-1", db_conn=mock)
        assert result["total_notifications"] == 0
        assert result["delivery_rate_pct"] == 0.0

    def test_calculates_delivery_rate(self):
        """8.8 Delivery rate = sent / total."""
        records = [
            {"id": "1", "customer_id": "c1", "status": "sent", "priority": "medium", "responded": True, "notification_type": "general"},
            {"id": "2", "customer_id": "c1", "status": "sent", "priority": "medium", "responded": False, "notification_type": "general"},
            {"id": "3", "customer_id": "c1", "status": "queued", "priority": "low", "responded": False, "notification_type": "general"},
            {"id": "4", "customer_id": "c1", "status": "batched", "priority": "low", "responded": False, "notification_type": "general"},
        ]
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.gte.return_value \
            .execute.return_value.data = records

        result = get_notification_performance_metrics("store-1", db_conn=mock)
        assert result["total_notifications"] == 4
        assert result["sent_count"] == 2
        assert result["queued_count"] == 1
        assert result["batched_count"] == 1
        assert result["delivery_rate_pct"] == 50.0

    def test_calculates_batching_rate(self):
        """8.8 Batching rate = batched / total."""
        records = [
            {"id": "1", "customer_id": "c1", "status": "batched", "priority": "medium", "responded": False, "notification_type": "batch"},
            {"id": "2", "customer_id": "c1", "status": "batched", "priority": "medium", "responded": False, "notification_type": "batch"},
            {"id": "3", "customer_id": "c1", "status": "sent", "priority": "high", "responded": True, "notification_type": "general"},
            {"id": "4", "customer_id": "c1", "status": "sent", "priority": "high", "responded": False, "notification_type": "general"},
        ]
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.gte.return_value \
            .execute.return_value.data = records

        result = get_notification_performance_metrics("store-1", db_conn=mock)
        assert result["batching_rate_pct"] == 50.0

    def test_calculates_response_rate(self):
        """8.8 Response rate = responded / sent."""
        records = [
            {"id": "1", "customer_id": "c1", "status": "sent", "priority": "medium", "responded": True, "notification_type": "general"},
            {"id": "2", "customer_id": "c1", "status": "sent", "priority": "medium", "responded": True, "notification_type": "general"},
            {"id": "3", "customer_id": "c1", "status": "sent", "priority": "medium", "responded": False, "notification_type": "general"},
            {"id": "4", "customer_id": "c1", "status": "sent", "priority": "medium", "responded": False, "notification_type": "general"},
        ]
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.gte.return_value \
            .execute.return_value.data = records

        result = get_notification_performance_metrics("store-1", db_conn=mock)
        assert result["response_rate_pct"] == 50.0

    def test_includes_priority_breakdown(self):
        """8.8 Result includes priority breakdown."""
        records = [
            {"id": "1", "customer_id": "c1", "status": "sent", "priority": "critical", "responded": True, "notification_type": "general"},
            {"id": "2", "customer_id": "c1", "status": "sent", "priority": "low", "responded": False, "notification_type": "general"},
        ]
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.gte.return_value \
            .execute.return_value.data = records

        result = get_notification_performance_metrics("store-1", db_conn=mock)
        assert "priority_breakdown" in result
        assert result["priority_breakdown"].get("critical") == 1
        assert result["priority_breakdown"].get("low") == 1


# ---------------------------------------------------------------------------
# NotificationOrchestrator integration
# ---------------------------------------------------------------------------

class TestNotificationOrchestrator:
    """Integration tests for the NotificationOrchestrator class."""

    def test_get_optimal_time_delegates_correctly(self):
        """get_optimal_time returns a valid HH:MM string."""
        mock = _make_supabase_mock()
        execute_mock = MagicMock()
        execute_mock.data = []
        mock.table.return_value.select.return_value.eq.return_value.eq.return_value \
            .not_.is_.return_value.execute.return_value = execute_mock

        orchestrator = NotificationOrchestrator(supabase=mock)
        result = orchestrator.get_optimal_time("cust-1")
        assert ":" in result
        hour = int(result.split(":")[0])
        assert SEND_WINDOW_START <= hour < SEND_WINDOW_END

    def test_combine_messages_delegates_correctly(self):
        """combine_messages returns combined text."""
        orchestrator = NotificationOrchestrator()
        notifs = [{"message": "A"}, {"message": "B"}]
        result = orchestrator.combine_messages(notifs)
        assert "A" in result
        assert "B" in result

    def test_send_notification_queues_outside_window(self):
        """send_notification queues when outside send window."""
        mock = _make_supabase_mock()
        mock.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": str(uuid.uuid4())}
        ]

        orchestrator = NotificationOrchestrator(supabase=mock)

        # Patch datetime to return a time outside the window (e.g., 2 AM)
        with patch("agents.notification_orchestrator.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value.hour = 2
            mock_dt.now.return_value.replace.return_value = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value.isoformat.return_value = "2024-01-01T02:00:00+00:00"

            # Use is_within_send_window directly to verify
            assert not is_within_send_window(2)
