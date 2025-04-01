"""
Tests for the predictive credit and collection system (task 4).

Covers:
- Credit score calculation (base, payment history, frequency, spending)
- Credit limit tiers
- Collection strategy selection by days overdue
- Auto-suspend logic
- Default prediction
- Collection rate monitoring
"""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.intelligent_credit_agent import (
    calculate_credit_score,
    calculate_credit_limit,
    get_collection_strategy,
    predict_default_risk,
    auto_suspend_credit,
    auto_restore_credit,
    get_optimal_reminder_time,
    get_collection_metrics,
)
from events.monitoring import CollectionRateMonitor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_supabase_mock(payment_history=None, orders=None, customer=None):
    """Build a minimal Supabase mock that returns given data."""
    mock = MagicMock()

    def _chain(data):
        """Return a chainable mock that yields .execute().data = data."""
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.not_.is_.return_value = chain
        chain.single.return_value = chain
        chain.lte.return_value = chain
        chain.execute.return_value = MagicMock(data=data)
        return chain

    def table_side_effect(name):
        if name == "payment_history":
            return _chain(payment_history if payment_history is not None else [])
        if name == "orders":
            return _chain(orders if orders is not None else [])
        if name == "customers":
            c = _chain([customer] if customer else [])
            # single() should return the customer dict directly
            c.single.return_value = MagicMock(
                execute=MagicMock(return_value=MagicMock(data=customer or {}))
            )
            c.update.return_value = MagicMock(
                eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=None)))
            )
            return c
        if name == "notification_response_times":
            return _chain([])
        return _chain([])

    mock.table.side_effect = table_side_effect
    return mock


# ---------------------------------------------------------------------------
# 4.1 Credit Score Calculation
# ---------------------------------------------------------------------------

class TestCalculateCreditScore:
    def test_base_score_no_history(self):
        """With no payment history and no orders, score = 50 (base only)."""
        mock_db = _make_supabase_mock(payment_history=[], orders=[])
        score = calculate_credit_score("cust-1", db_conn=mock_db)
        assert score == pytest.approx(50.0)

    def test_payment_history_all_on_time(self):
        """All on-time payments → +30 payment score."""
        payments = [{"days_to_payment": 3, "was_late": False}] * 10
        mock_db = _make_supabase_mock(payment_history=payments, orders=[])
        score = calculate_credit_score("cust-1", db_conn=mock_db)
        # base 50 + payment 30 + freq 0 + spending 0 = 80
        assert score == pytest.approx(80.0)

    def test_payment_history_all_late(self):
        """All late payments → -30 payment score."""
        payments = [{"days_to_payment": 14, "was_late": True}] * 10
        mock_db = _make_supabase_mock(payment_history=payments, orders=[])
        score = calculate_credit_score("cust-1", db_conn=mock_db)
        # base 50 - 30 = 20
        assert score == pytest.approx(20.0)

    def test_order_frequency_score(self):
        """20 orders → frequency_score = min(20/2, 10) = 10."""
        orders = [{"id": str(i), "total_amount": 0} for i in range(20)]
        mock_db = _make_supabase_mock(payment_history=[], orders=orders)
        score = calculate_credit_score("cust-1", db_conn=mock_db)
        # base 50 + freq 10 = 60
        assert score == pytest.approx(60.0)

    def test_spending_score(self):
        """₹10000 total spent → spending_score = min(10000/1000, 10) = 10."""
        orders = [{"id": "o1", "total_amount": 10000}]
        mock_db = _make_supabase_mock(payment_history=[], orders=orders)
        score = calculate_credit_score("cust-1", db_conn=mock_db)
        # base 50 + freq min(1/2,10)=0.5 + spending 10 = 60.5
        assert score == pytest.approx(60.5)

    def test_score_clamped_at_100(self):
        """Score cannot exceed 100."""
        payments = [{"days_to_payment": 1, "was_late": False}] * 20
        orders = [{"id": str(i), "total_amount": 5000} for i in range(40)]
        mock_db = _make_supabase_mock(payment_history=payments, orders=orders)
        score = calculate_credit_score("cust-1", db_conn=mock_db)
        assert score <= 100.0

    def test_score_clamped_at_0(self):
        """Score cannot go below 0."""
        payments = [{"days_to_payment": 30, "was_late": True}] * 20
        mock_db = _make_supabase_mock(payment_history=payments, orders=[])
        score = calculate_credit_score("cust-1", db_conn=mock_db)
        assert score >= 0.0

    def test_mixed_payment_history(self):
        """Half on-time, half late → payment_score = 0."""
        payments = (
            [{"days_to_payment": 3, "was_late": False}] * 5
            + [{"days_to_payment": 14, "was_late": True}] * 5
        )
        mock_db = _make_supabase_mock(payment_history=payments, orders=[])
        score = calculate_credit_score("cust-1", db_conn=mock_db)
        # base 50 + payment 0 = 50
        assert score == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# 4.2 Credit Limit Calculation
# ---------------------------------------------------------------------------

class TestCalculateCreditLimit:
    def test_score_above_70_gets_5000(self):
        assert calculate_credit_limit(70.0) == 5000.0
        assert calculate_credit_limit(85.0) == 5000.0
        assert calculate_credit_limit(100.0) == 5000.0

    def test_score_50_to_69_gets_2000(self):
        assert calculate_credit_limit(50.0) == 2000.0
        assert calculate_credit_limit(60.0) == 2000.0
        assert calculate_credit_limit(69.9) == 2000.0

    def test_score_below_50_gets_0(self):
        assert calculate_credit_limit(49.9) == 0.0
        assert calculate_credit_limit(0.0) == 0.0
        assert calculate_credit_limit(30.0) == 0.0

    def test_boundary_exactly_70(self):
        assert calculate_credit_limit(70.0) == 5000.0

    def test_boundary_exactly_50(self):
        assert calculate_credit_limit(50.0) == 2000.0

    def test_boundary_just_below_50(self):
        assert calculate_credit_limit(49.0) == 0.0


# ---------------------------------------------------------------------------
# 4.4 Collection Strategy
# ---------------------------------------------------------------------------

class TestGetCollectionStrategy:
    def test_day_1_friendly(self):
        strategy = get_collection_strategy(1)
        assert strategy["tone"] == "friendly"
        assert strategy["urgency"] == "low"

    def test_day_3_friendly(self):
        strategy = get_collection_strategy(3)
        assert strategy["tone"] == "friendly"
        assert strategy["urgency"] == "low"

    def test_day_4_neutral(self):
        strategy = get_collection_strategy(4)
        assert strategy["tone"] == "neutral"
        assert strategy["urgency"] == "medium"

    def test_day_7_neutral(self):
        strategy = get_collection_strategy(7)
        assert strategy["tone"] == "neutral"
        assert strategy["urgency"] == "medium"

    def test_day_8_firm(self):
        strategy = get_collection_strategy(8)
        assert strategy["tone"] == "firm"
        assert strategy["urgency"] == "high"

    def test_day_15_firm(self):
        strategy = get_collection_strategy(15)
        assert strategy["tone"] == "firm"
        assert strategy["urgency"] == "high"

    def test_day_16_strict_with_suspend(self):
        strategy = get_collection_strategy(16)
        assert strategy["tone"] == "strict"
        assert strategy["urgency"] == "critical"
        assert strategy.get("action") == "suspend_credit"

    def test_day_30_strict(self):
        strategy = get_collection_strategy(30)
        assert strategy["tone"] == "strict"
        assert strategy.get("action") == "suspend_credit"

    def test_strategy_has_message(self):
        for days in [1, 5, 10, 20]:
            strategy = get_collection_strategy(days)
            assert "message" in strategy
            assert len(strategy["message"]) > 0

    def test_strategy_has_reminder_type(self):
        for days in [1, 5, 10, 20]:
            strategy = get_collection_strategy(days)
            assert "reminder_type" in strategy


# ---------------------------------------------------------------------------
# 4.6 Auto-Suspend / Auto-Restore
# ---------------------------------------------------------------------------

class TestAutoSuspendRestore:
    def test_auto_suspend_calls_update(self):
        mock_db = MagicMock()
        update_chain = MagicMock()
        mock_db.table.return_value.update.return_value = update_chain
        update_chain.eq.return_value.execute.return_value = None

        result = auto_suspend_credit("cust-1", db_conn=mock_db)
        assert result is True
        mock_db.table.assert_called_with("customers")
        mock_db.table.return_value.update.assert_called_once_with({"credit_suspended": True})

    def test_auto_suspend_returns_false_on_error(self):
        mock_db = MagicMock()
        mock_db.table.side_effect = Exception("DB error")
        result = auto_suspend_credit("cust-1", db_conn=mock_db)
        assert result is False

    def test_auto_restore_updates_credit_suspended_false(self):
        """auto_restore_credit should set credit_suspended=False and return True."""
        # Use a simple mock that tracks the update payload
        update_calls = []

        def make_chain(data=None):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.not_.is_.return_value = chain
            chain.single.return_value = chain
            chain.execute.return_value = MagicMock(data=data or [])
            return chain

        def update_side_effect(data):
            update_calls.append(data)
            chain = MagicMock()
            chain.eq.return_value.execute.return_value = None
            return chain

        mock_db = MagicMock()

        def table_side_effect(name):
            if name == "payment_history":
                return make_chain([])
            if name == "orders":
                return make_chain([])
            if name == "customers":
                c = make_chain([])
                c.update.side_effect = update_side_effect
                return c
            return make_chain([])

        mock_db.table.side_effect = table_side_effect

        result = auto_restore_credit("cust-1", db_conn=mock_db)
        assert result is True
        # Should have called update with credit_suspended=False
        assert any(d.get("credit_suspended") is False for d in update_calls)

    def test_auto_restore_returns_false_on_error(self):
        mock_db = MagicMock()
        mock_db.table.side_effect = Exception("DB error")
        result = auto_restore_credit("cust-1", db_conn=mock_db)
        assert result is False


# ---------------------------------------------------------------------------
# 4.7 Default Prediction
# ---------------------------------------------------------------------------

class TestPredictDefaultRisk:
    def _make_db(self, credit_score=50, suspended=False, payment_history=None, overdue_orders=None):
        mock = MagicMock()

        def table_side_effect(name):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.not_.is_.return_value = chain
            chain.lte.return_value = chain

            if name == "customers":
                chain.single.return_value = MagicMock(
                    execute=MagicMock(
                        return_value=MagicMock(
                            data={
                                "credit_score": credit_score,
                                "credit_suspended": suspended,
                                "credit_limit": 2000,
                            }
                        )
                    )
                )
            elif name == "payment_history":
                chain.execute.return_value = MagicMock(data=payment_history or [])
            elif name == "orders":
                chain.execute.return_value = MagicMock(data=overdue_orders or [])
            else:
                chain.execute.return_value = MagicMock(data=[])
            return chain

        mock.table.side_effect = table_side_effect
        return mock

    def test_low_risk_good_customer(self):
        payments = [{"days_to_payment": 3, "was_late": False}] * 5
        mock_db = self._make_db(credit_score=80, suspended=False, payment_history=payments)
        result = predict_default_risk("cust-1", db_conn=mock_db)
        assert result["risk_level"] == "low"
        assert result["default_probability"] < 0.3

    def test_high_risk_suspended_low_score(self):
        payments = [{"days_to_payment": 20, "was_late": True}] * 10
        mock_db = self._make_db(credit_score=25, suspended=True, payment_history=payments)
        result = predict_default_risk("cust-1", db_conn=mock_db)
        assert result["risk_level"] == "high"
        assert result["default_probability"] >= 0.6

    def test_risk_indicators_present(self):
        mock_db = self._make_db(credit_score=30, suspended=True)
        result = predict_default_risk("cust-1", db_conn=mock_db)
        assert len(result["risk_indicators"]) > 0
        assert "low_credit_score" in result["risk_indicators"]
        assert "credit_currently_suspended" in result["risk_indicators"]

    def test_recommended_action_high_risk(self):
        mock_db = self._make_db(credit_score=20, suspended=True)
        result = predict_default_risk("cust-1", db_conn=mock_db)
        assert result["recommended_action"] == "suspend_credit_and_contact_immediately"

    def test_recommended_action_low_risk(self):
        payments = [{"days_to_payment": 2, "was_late": False}] * 5
        mock_db = self._make_db(credit_score=85, suspended=False, payment_history=payments)
        result = predict_default_risk("cust-1", db_conn=mock_db)
        assert result["recommended_action"] == "continue_normal_operations"

    def test_probability_clamped_0_to_1(self):
        mock_db = self._make_db(credit_score=0, suspended=True)
        result = predict_default_risk("cust-1", db_conn=mock_db)
        assert 0.0 <= result["default_probability"] <= 1.0


# ---------------------------------------------------------------------------
# 4.12 Collection Rate Monitor
# ---------------------------------------------------------------------------

class TestCollectionRateMonitor:
    def setup_method(self):
        self.monitor = CollectionRateMonitor()

    def test_initial_collection_rate_zero(self):
        assert self.monitor.collection_rate() == 0.0

    def test_full_collection(self):
        self.monitor.record_payment(amount_due=1000, amount_collected=1000)
        self.monitor.record_payment(amount_due=500, amount_collected=500)
        assert self.monitor.collection_rate() == pytest.approx(100.0)

    def test_partial_collection(self):
        self.monitor.record_payment(amount_due=1000, amount_collected=500)
        assert self.monitor.collection_rate() == pytest.approx(50.0)

    def test_reminder_conversion_rate(self):
        self.monitor.record_reminder(converted=True)
        self.monitor.record_reminder(converted=False)
        self.monitor.record_reminder(converted=True)
        assert self.monitor.reminder_conversion_rate() == pytest.approx(200 / 3)

    def test_avg_days_to_collect(self):
        self.monitor.record_payment(1000, 1000, days_to_collect=5)
        self.monitor.record_payment(500, 500, days_to_collect=15)
        assert self.monitor.avg_days_to_collect() == pytest.approx(10.0)

    def test_get_stats_structure(self):
        self.monitor.record_payment(1000, 800)
        self.monitor.record_reminder(converted=True)
        stats = self.monitor.get_stats()
        assert "collection_rate_pct" in stats
        assert "reminder_conversion_rate_pct" in stats
        assert "avg_days_to_collect" in stats
        assert "reminders_sent" in stats

    def test_reset(self):
        self.monitor.record_payment(1000, 1000)
        self.monitor.record_reminder(converted=True)
        self.monitor.reset()
        assert self.monitor.collection_rate() == 0.0
        assert self.monitor.reminder_conversion_rate() == 0.0
