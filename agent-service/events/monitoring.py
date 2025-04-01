"""
EventMonitor: in-memory metrics tracking for event processing latency.

Tracks per-event-type counters and latency statistics with no external
dependencies. Provides a context manager for wrapping handler calls.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator, Optional

from events.event_types import Event, EventType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-type metrics container
# ---------------------------------------------------------------------------

@dataclass
class _EventMetrics:
    total_received: int = 0
    total_processed: int = 0
    total_failed: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0

    def to_dict(self) -> dict:
        processed = self.total_processed
        avg = (self.total_latency_ms / processed) if processed > 0 else 0.0
        return {
            "total_received": self.total_received,
            "total_processed": self.total_processed,
            "total_failed": self.total_failed,
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": avg,
            "min_latency_ms": self.min_latency_ms if processed > 0 else 0.0,
            "max_latency_ms": self.max_latency_ms,
        }


# ---------------------------------------------------------------------------
# EventMonitor
# ---------------------------------------------------------------------------

class EventMonitor:
    """Tracks event processing latency and metrics in memory."""

    def __init__(self) -> None:
        self._metrics: dict[EventType, _EventMetrics] = {}

    def _get_or_create(self, event_type: EventType) -> _EventMetrics:
        if event_type not in self._metrics:
            self._metrics[event_type] = _EventMetrics()
        return self._metrics[event_type]

    def record_received(self, event_type: EventType) -> None:
        """Increment the received counter for the given event type."""
        self._get_or_create(event_type).total_received += 1

    def record_processed(self, event_type: EventType, latency_ms: float) -> None:
        """Record a successful processing with its latency."""
        m = self._get_or_create(event_type)
        m.total_processed += 1
        m.total_latency_ms += latency_ms
        if latency_ms < m.min_latency_ms:
            m.min_latency_ms = latency_ms
        if latency_ms > m.max_latency_ms:
            m.max_latency_ms = latency_ms

    def record_failed(self, event_type: EventType, latency_ms: float) -> None:
        """Record a failed processing with its latency."""
        m = self._get_or_create(event_type)
        m.total_failed += 1
        m.total_latency_ms += latency_ms
        if latency_ms < m.min_latency_ms:
            m.min_latency_ms = latency_ms
        if latency_ms > m.max_latency_ms:
            m.max_latency_ms = latency_ms

    def get_stats(self, event_type: Optional[EventType] = None) -> dict:
        """Return stats for a specific event type or all types.

        Args:
            event_type: If provided, return stats for that type only.
                        If None, return a dict keyed by event type value.
        """
        if event_type is not None:
            m = self._metrics.get(event_type)
            return m.to_dict() if m else _EventMetrics().to_dict()
        return {et.value: m.to_dict() for et, m in self._metrics.items()}

    def get_avg_latency(self, event_type: Optional[EventType] = None) -> float:
        """Return average latency in ms across one or all event types.

        Args:
            event_type: If provided, average for that type only.
                        If None, overall average across all types.
        """
        if event_type is not None:
            m = self._metrics.get(event_type)
            if m is None or m.total_processed == 0:
                return 0.0
            return m.total_latency_ms / m.total_processed

        total_latency = sum(m.total_latency_ms for m in self._metrics.values())
        total_processed = sum(m.total_processed for m in self._metrics.values())
        return total_latency / total_processed if total_processed > 0 else 0.0

    def reset(self) -> None:
        """Reset all counters (useful for testing)."""
        self._metrics.clear()

    def log_summary(self) -> None:
        """Log a summary of all metrics using Python logging."""
        if not self._metrics:
            logger.info("EventMonitor: no metrics recorded yet.")
            return

        logger.info("EventMonitor summary:")
        for et, m in self._metrics.items():
            stats = m.to_dict()
            logger.info(
                "  [%s] received=%d processed=%d failed=%d "
                "avg_latency=%.2fms min=%.2fms max=%.2fms",
                et.value,
                stats["total_received"],
                stats["total_processed"],
                stats["total_failed"],
                stats["avg_latency_ms"],
                stats["min_latency_ms"],
                stats["max_latency_ms"],
            )


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

@contextmanager
def track_event(monitor: EventMonitor, event: Event) -> Generator[None, None, None]:
    """Context manager that records event processing metrics.

    Records the start time, calls record_received, then on exit calls
    record_processed (success) or record_failed (exception) with elapsed ms.
    Exceptions are re-raised after recording.

    Usage::

        with track_event(monitor, event):
            handler(event)
    """
    monitor.record_received(event.event_type)
    start = time.monotonic()
    try:
        yield
        latency_ms = (time.monotonic() - start) * 1000
        monitor.record_processed(event.event_type, latency_ms)
    except Exception:
        latency_ms = (time.monotonic() - start) * 1000
        monitor.record_failed(event.event_type, latency_ms)
        raise


# ---------------------------------------------------------------------------
# 2.9 Forecast Accuracy Monitor
# ---------------------------------------------------------------------------

@dataclass
class _ForecastRecord:
    predicted: float
    actual: float

    @property
    def error_pct(self) -> float:
        if self.actual == 0:
            return 0.0
        return abs(self.predicted - self.actual) / self.actual * 100


class ForecastAccuracyMonitor:
    """Tracks demand forecast accuracy (predicted vs actual sales)."""

    def __init__(self) -> None:
        self._records: list[_ForecastRecord] = []

    def record(self, predicted: float, actual: float) -> None:
        """Record a forecast vs actual pair."""
        self._records.append(_ForecastRecord(predicted=predicted, actual=actual))

    def mean_absolute_percentage_error(self) -> float:
        """Return MAPE across all recorded forecasts (0-100 scale)."""
        if not self._records:
            return 0.0
        return sum(r.error_pct for r in self._records) / len(self._records)

    def accuracy_percentage(self) -> float:
        """Return accuracy as 100 - MAPE, clamped to [0, 100]."""
        return max(0.0, min(100.0, 100.0 - self.mean_absolute_percentage_error()))

    def get_stats(self) -> dict:
        return {
            "total_forecasts": len(self._records),
            "mape": round(self.mean_absolute_percentage_error(), 2),
            "accuracy_pct": round(self.accuracy_percentage(), 2),
        }

    def reset(self) -> None:
        self._records.clear()


# Singleton instance for the agent-service
forecast_monitor = ForecastAccuracyMonitor()


# ---------------------------------------------------------------------------
# 4.12 Collection Rate Monitor
# ---------------------------------------------------------------------------

@dataclass
class _CollectionRecord:
    amount_due: float
    amount_collected: float
    days_to_collect: Optional[int]

    @property
    def collected(self) -> bool:
        return self.amount_collected >= self.amount_due


class CollectionRateMonitor:
    """Tracks payment collection rates for the credit system."""

    def __init__(self) -> None:
        self._records: list[_CollectionRecord] = []
        self._reminders_sent: int = 0
        self._reminders_converted: int = 0

    def record_payment(
        self,
        amount_due: float,
        amount_collected: float,
        days_to_collect: Optional[int] = None,
    ) -> None:
        """Record a payment outcome."""
        self._records.append(
            _CollectionRecord(
                amount_due=amount_due,
                amount_collected=amount_collected,
                days_to_collect=days_to_collect,
            )
        )

    def record_reminder(self, converted: bool = False) -> None:
        """Record a reminder sent and whether it led to payment."""
        self._reminders_sent += 1
        if converted:
            self._reminders_converted += 1

    def collection_rate(self) -> float:
        """Return percentage of outstanding amounts collected (0-100)."""
        if not self._records:
            return 0.0
        total_due = sum(r.amount_due for r in self._records)
        total_collected = sum(r.amount_collected for r in self._records)
        return (total_collected / total_due * 100) if total_due > 0 else 0.0

    def reminder_conversion_rate(self) -> float:
        """Return percentage of reminders that led to payment (0-100)."""
        if self._reminders_sent == 0:
            return 0.0
        return self._reminders_converted / self._reminders_sent * 100

    def avg_days_to_collect(self) -> float:
        """Return average days from due to collection (excludes uncollected)."""
        collected = [r for r in self._records if r.collected and r.days_to_collect is not None]
        if not collected:
            return 0.0
        return sum(r.days_to_collect for r in collected) / len(collected)

    def get_stats(self) -> dict:
        return {
            "total_records": len(self._records),
            "collection_rate_pct": round(self.collection_rate(), 2),
            "reminder_conversion_rate_pct": round(self.reminder_conversion_rate(), 2),
            "avg_days_to_collect": round(self.avg_days_to_collect(), 1),
            "reminders_sent": self._reminders_sent,
            "reminders_converted": self._reminders_converted,
        }

    def reset(self) -> None:
        self._records.clear()
        self._reminders_sent = 0
        self._reminders_converted = 0


# Singleton instance for the agent-service
collection_monitor = CollectionRateMonitor()


# ---------------------------------------------------------------------------
# 7.8 Agent Interaction Monitor
# ---------------------------------------------------------------------------

from dataclasses import field as _field


class AgentInteractionMonitor:
    """Tracks inter-agent message counts and collaboration decision outcomes."""

    def __init__(self) -> None:
        # (from_agent, to_agent, message_type) → count
        self._message_counts: dict[tuple[str, str, str], int] = {}
        # decision_type → {"success": int, "failure": int, "total": int}
        self._decision_outcomes: dict[str, dict[str, int]] = {}

    def record_agent_message(
        self, from_agent: str, to_agent: str, message_type: str
    ) -> None:
        """Increment counter for a (from_agent, to_agent, message_type) triple."""
        key = (from_agent, to_agent, message_type)
        self._message_counts[key] = self._message_counts.get(key, 0) + 1

    def record_collaboration_decision(
        self, decision_type: str, outcome: str
    ) -> None:
        """Track a decision outcome for a given decision type."""
        if decision_type not in self._decision_outcomes:
            self._decision_outcomes[decision_type] = {
                "success": 0,
                "failure": 0,
                "partial": 0,
                "overridden_by_owner": 0,
                "total": 0,
            }
        bucket = self._decision_outcomes[decision_type]
        bucket["total"] += 1
        if outcome in bucket:
            bucket[outcome] += 1

    def get_agent_interaction_stats(self) -> dict:
        """Return message counts and decision success rates per agent pair."""
        message_stats = {}
        for (from_a, to_a, msg_type), count in self._message_counts.items():
            pair_key = f"{from_a}->{to_a}"
            if pair_key not in message_stats:
                message_stats[pair_key] = {}
            message_stats[pair_key][msg_type] = count

        decision_stats = {}
        for decision_type, outcomes in self._decision_outcomes.items():
            total = outcomes.get("total", 0)
            successes = outcomes.get("success", 0)
            success_rate = round(successes / total, 3) if total > 0 else None
            decision_stats[decision_type] = {
                **outcomes,
                "success_rate": success_rate,
            }

        return {
            "message_counts": message_stats,
            "decision_outcomes": decision_stats,
        }

    def reset(self) -> None:
        """Reset all counters."""
        self._message_counts.clear()
        self._decision_outcomes.clear()


# Singleton instance
agent_interaction_monitor = AgentInteractionMonitor()
