"""
Tests for the intelligent customer lifecycle manager (task 3).

Covers:
- VIPDetector: lifetime value, order frequency, VIP criteria
- ChurnPredictor: days since last order, avg interval, churn detection
- ReEngagementStrategy: message generation, response tracking
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.customer_lifecycle_agent import (
    VIPDetector,
    ChurnPredictor,
    ReEngagementStrategy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _orders(amounts: list[float], days_ago: list[int] | None = None) -> list[dict]:
    """Build minimal order dicts."""
    if days_ago is None:
        days_ago = list(range(len(amounts)))
    result = []
    for amount, d in zip(amounts, days_ago):
        ts = (datetime.now(timezone.utc) - timedelta(days=d)).isoformat()
        result.append({"total_amount": amount, "created_at": ts})
    return result


def _order_dates(days_ago_list: list[int]) -> list[datetime]:
    """Build a list of datetime objects from days-ago values."""
    return [
        datetime.now(timezone.utc) - timedelta(days=d) for d in days_ago_list
    ]


# ---------------------------------------------------------------------------
# VIPDetector
# ---------------------------------------------------------------------------

class TestVIPDetector:
    def setup_method(self):
        self.detector = VIPDetector(supabase_client=object())

    # 3.1.1 Lifetime value
    def test_lifetime_value_basic(self):
        orders = _orders([100.0, 200.0, 300.0])
        assert self.detector.calculate_lifetime_value(orders) == pytest.approx(600.0)

    def test_lifetime_value_empty(self):
        assert self.detector.calculate_lifetime_value([]) == 0.0

    def test_lifetime_value_single(self):
        orders = _orders([500.0])
        assert self.detector.calculate_lifetime_value(orders) == pytest.approx(500.0)

    # 3.1.2 Order frequency
    def test_order_frequency_basic(self):
        # 6 orders over 60 days = 1 order per 10 days = ~3 per month
        orders = _orders([100.0] * 6)
        first_order_date = datetime.now(timezone.utc) - timedelta(days=60)
        freq = self.detector.calculate_order_frequency(orders, first_order_date)
        assert freq == pytest.approx(3.0, rel=0.1)

    def test_order_frequency_no_orders(self):
        first_order_date = datetime.now(timezone.utc) - timedelta(days=30)
        freq = self.detector.calculate_order_frequency([], first_order_date)
        assert freq == 0.0

    def test_order_frequency_same_day(self):
        # days_active = 0 → returns order_count directly
        orders = _orders([100.0] * 3)
        first_order_date = datetime.now(timezone.utc)
        freq = self.detector.calculate_order_frequency(orders, first_order_date)
        assert freq == pytest.approx(3.0)

    # 3.1.3 VIP criteria
    def test_vip_by_total_spent(self):
        assert self.detector.is_vip(total_spent=15000, order_count=5, order_frequency=1) is True

    def test_vip_by_order_count(self):
        assert self.detector.is_vip(total_spent=500, order_count=25, order_frequency=1) is True

    def test_vip_by_frequency(self):
        assert self.detector.is_vip(total_spent=500, order_count=5, order_frequency=5) is True

    def test_not_vip(self):
        assert self.detector.is_vip(total_spent=500, order_count=5, order_frequency=1) is False

    def test_vip_boundary_spent(self):
        # Exactly 10000 is NOT > 10000
        assert self.detector.is_vip(total_spent=10000, order_count=5, order_frequency=1) is False

    def test_vip_boundary_order_count(self):
        # Exactly 20 is NOT > 20
        assert self.detector.is_vip(total_spent=500, order_count=20, order_frequency=1) is False

    def test_vip_boundary_frequency(self):
        # Exactly 4 is NOT > 4
        assert self.detector.is_vip(total_spent=500, order_count=5, order_frequency=4) is False


# ---------------------------------------------------------------------------
# ChurnPredictor
# ---------------------------------------------------------------------------

class TestChurnPredictor:
    def setup_method(self):
        self.predictor = ChurnPredictor(supabase_client=object())

    # 3.4.1 Days since last order
    def test_days_since_last_order_recent(self):
        last_order = datetime.now(timezone.utc) - timedelta(days=5)
        assert self.predictor.days_since_last_order(last_order) == 5

    def test_days_since_last_order_today(self):
        last_order = datetime.now(timezone.utc)
        assert self.predictor.days_since_last_order(last_order) == 0

    def test_days_since_last_order_naive_datetime(self):
        # Should handle naive datetimes gracefully
        last_order = datetime.now() - timedelta(days=10)
        result = self.predictor.days_since_last_order(last_order)
        assert result == pytest.approx(10, abs=1)

    # 3.4.2 Average order interval
    def test_avg_interval_basic(self):
        # Orders every 10 days
        dates = _order_dates([30, 20, 10, 0])
        avg = self.predictor.calculate_avg_interval(dates)
        assert avg == pytest.approx(10.0)

    def test_avg_interval_single_order(self):
        dates = _order_dates([15])
        avg = self.predictor.calculate_avg_interval(dates)
        assert avg == float(ChurnPredictor.DEFAULT_AVG_INTERVAL)

    def test_avg_interval_empty(self):
        avg = self.predictor.calculate_avg_interval([])
        assert avg == float(ChurnPredictor.DEFAULT_AVG_INTERVAL)

    def test_avg_interval_two_orders(self):
        dates = _order_dates([20, 0])
        avg = self.predictor.calculate_avg_interval(dates)
        assert avg == pytest.approx(20.0)

    # 3.4.3 & 3.4.4 Churn risk detection
    def test_churn_risk_detected(self):
        # 60 days since last order, avg interval 20 → 60 > 40 → at risk
        is_at_risk, level = self.predictor.detect_churn_risk(
            days_since=60, avg_interval=20.0
        )
        assert is_at_risk is True
        assert level == "high"  # 60 > 30

    def test_churn_risk_medium(self):
        # 25 days since last order, avg interval 10 → 25 > 20 → at risk, medium
        is_at_risk, level = self.predictor.detect_churn_risk(
            days_since=25, avg_interval=10.0
        )
        assert is_at_risk is True
        assert level == "medium"  # 25 <= 30

    def test_no_churn_risk(self):
        # 10 days since last order, avg interval 15 → 10 < 30 → not at risk
        is_at_risk, level = self.predictor.detect_churn_risk(
            days_since=10, avg_interval=15.0
        )
        assert is_at_risk is False

    def test_churn_risk_boundary(self):
        # Exactly 2x average → NOT > 2x, so not at risk
        is_at_risk, _ = self.predictor.detect_churn_risk(
            days_since=20, avg_interval=10.0
        )
        assert is_at_risk is False

    def test_churn_risk_just_over_boundary(self):
        # 21 days, avg 10 → 21 > 20 → at risk
        is_at_risk, _ = self.predictor.detect_churn_risk(
            days_since=21, avg_interval=10.0
        )
        assert is_at_risk is True

    def test_high_risk_threshold(self):
        # > 30 days → high risk
        _, level = self.predictor.detect_churn_risk(days_since=31, avg_interval=5.0)
        assert level == "high"

    def test_medium_risk_threshold(self):
        # <= 30 days → medium risk
        _, level = self.predictor.detect_churn_risk(days_since=30, avg_interval=5.0)
        assert level == "medium"


# ---------------------------------------------------------------------------
# ReEngagementStrategy
# ---------------------------------------------------------------------------

class TestReEngagementStrategy:
    def setup_method(self):
        self.strategy = ReEngagementStrategy(supabase_client=object())

    # 3.5.1 Message generation (no discounts)
    def test_first_message_contains_name(self):
        msg = self.strategy.generate_message("Alice", days_since=20, message_number=1)
        assert "Alice" in msg

    def test_first_message_no_discount(self):
        msg = self.strategy.generate_message("Bob", days_since=20, message_number=1)
        lower = msg.lower()
        assert "discount" not in lower
        assert "%" not in lower
        assert "off" not in lower

    def test_followup_message_contains_name(self):
        msg = self.strategy.generate_message("Carol", days_since=35, message_number=2)
        assert "Carol" in msg

    def test_followup_message_no_discount(self):
        msg = self.strategy.generate_message("Dave", days_since=35, message_number=2)
        lower = msg.lower()
        assert "discount" not in lower
        assert "%" not in lower

    def test_followup_message_mentions_days(self):
        msg = self.strategy.generate_message("Eve", days_since=35, message_number=2)
        assert "35" in msg

    def test_messages_are_different(self):
        msg1 = self.strategy.generate_message("Frank", days_since=20, message_number=1)
        msg2 = self.strategy.generate_message("Frank", days_since=20, message_number=2)
        assert msg1 != msg2
