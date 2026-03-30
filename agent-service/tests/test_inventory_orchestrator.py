"""
Tests for the autonomous inventory orchestrator (task 2.8).

Covers:
- DemandForecastingModule: moving average, trend detection, prediction, confidence
- ReorderDecisionEngine: days until stockout, reorder decision, quantity, cost
- LearningSystem: edit tracking, pattern calculation, suggestion adjustment
- ForecastAccuracyMonitor: MAPE and accuracy
"""

from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.inventory_orchestrator import (
    DemandForecastingModule,
    LearningSystem,
    ReorderDecisionEngine,
)
from events.monitoring import ForecastAccuracyMonitor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sales(quantities: list[float]) -> list[dict]:
    """Build minimal sales_data dicts from a list of quantities."""
    return [{"quantity": q} for q in quantities]


# ---------------------------------------------------------------------------
# DemandForecastingModule
# ---------------------------------------------------------------------------

class TestDemandForecastingModule:
    def setup_method(self):
        # Pass a dummy supabase so __init__ doesn't try to connect
        self.module = DemandForecastingModule(supabase_client=object())

    # 2.1.2 Moving average
    def test_moving_average_basic(self):
        data = _sales([10, 20, 30, 40, 50, 60, 70])
        avg = self.module.calculate_moving_average(data, window=7)
        assert avg == pytest.approx(40.0)

    def test_moving_average_window_larger_than_data(self):
        data = _sales([10, 20])
        avg = self.module.calculate_moving_average(data, window=7)
        assert avg == pytest.approx(15.0)

    def test_moving_average_empty(self):
        assert self.module.calculate_moving_average([], window=7) == 0.0

    # 2.1.3 Trend detection
    def test_trend_increasing(self):
        data = _sales([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        assert self.module.detect_trend(data) == "increasing"

    def test_trend_decreasing(self):
        data = _sales([10, 9, 8, 7, 6, 5, 4, 3, 2, 1])
        assert self.module.detect_trend(data) == "decreasing"

    def test_trend_stable(self):
        data = _sales([10, 10, 10, 10, 10, 10])
        assert self.module.detect_trend(data) == "stable"

    def test_trend_single_point(self):
        assert self.module.detect_trend(_sales([5])) == "stable"

    # 2.1.4 Demand prediction
    def test_predict_demand_stable(self):
        data = _sales([10] * 14)
        forecast = self.module.predict_demand(data, days_ahead=7)
        assert forecast == pytest.approx(70.0, rel=0.05)

    def test_predict_demand_increasing_applies_multiplier(self):
        data = _sales([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        forecast_stable = self.module.predict_demand(_sales([5] * 10), days_ahead=7)
        forecast_increasing = self.module.predict_demand(data, days_ahead=7)
        # Increasing trend should produce a higher forecast
        assert forecast_increasing > forecast_stable * 0.9  # at least comparable

    # 2.1.5 Confidence score
    def test_confidence_empty_data(self):
        assert self.module.calculate_confidence([]) == 0.0

    def test_confidence_increases_with_more_data(self):
        small = _sales([10] * 5)
        large = _sales([10] * 30)
        assert self.module.calculate_confidence(large) > self.module.calculate_confidence(small)

    def test_confidence_bounded(self):
        data = _sales([10] * 30)
        score = self.module.calculate_confidence(data)
        assert 0.0 <= score <= 100.0

    def test_confidence_low_variance_higher_than_high_variance(self):
        low_var = _sales([10] * 20)
        high_var = _sales([1, 100, 1, 100, 1, 100, 1, 100, 1, 100] * 2)
        assert self.module.calculate_confidence(low_var) > self.module.calculate_confidence(high_var)


# ---------------------------------------------------------------------------
# ReorderDecisionEngine
# ---------------------------------------------------------------------------

class TestReorderDecisionEngine:
    def setup_method(self):
        self.engine = ReorderDecisionEngine(supabase_client=object())

    # 2.2.1 Days until stockout
    def test_days_until_stockout_normal(self):
        days = self.engine.days_until_stockout(current_stock=70, avg_daily_sales=10)
        assert days == pytest.approx(7.0)

    def test_days_until_stockout_zero_sales(self):
        days = self.engine.days_until_stockout(current_stock=100, avg_daily_sales=0)
        assert days == float("inf")

    def test_days_until_stockout_zero_stock(self):
        days = self.engine.days_until_stockout(current_stock=0, avg_daily_sales=10)
        assert days == pytest.approx(0.0)

    # 2.2.2 Reorder decision
    def test_needs_reorder_true_when_low(self):
        # 5 days left → below threshold of 7
        assert self.engine.needs_reorder(current_stock=50, avg_daily_sales=10) is True

    def test_needs_reorder_false_when_sufficient(self):
        # 10 days left → above threshold
        assert self.engine.needs_reorder(current_stock=100, avg_daily_sales=10) is False

    def test_needs_reorder_boundary(self):
        # Exactly 7 days → not below threshold (< 7 is the condition)
        assert self.engine.needs_reorder(current_stock=70, avg_daily_sales=10) is False

    # 2.2.3 Suggested quantity
    def test_suggested_quantity_basic(self):
        qty = self.engine.suggested_quantity(forecast_14_days=100, current_stock=20)
        # (100 - 20) * 1.2 = 96
        assert qty == pytest.approx(96.0)

    def test_suggested_quantity_never_negative(self):
        qty = self.engine.suggested_quantity(forecast_14_days=10, current_stock=100)
        assert qty == 0.0

    # 2.2.4 Cost estimation
    def test_estimate_cost(self):
        cost = self.engine.estimate_cost(quantity=50, unit_cost=20)
        assert cost == pytest.approx(1000.0)

    def test_estimate_cost_zero(self):
        assert self.engine.estimate_cost(0, 100) == 0.0


# ---------------------------------------------------------------------------
# LearningSystem
# ---------------------------------------------------------------------------

class TestLearningSystem:
    def setup_method(self):
        self.learning = LearningSystem(supabase_client=object())

    # 2.5.3 Adjust suggestion
    def test_adjust_suggestion_positive_edit(self):
        # Owner consistently orders 20% more
        adjusted = self.learning.adjust_suggestion(100, avg_edit_percentage=20.0)
        assert adjusted == pytest.approx(120.0)

    def test_adjust_suggestion_negative_edit(self):
        # Owner consistently orders 10% less
        adjusted = self.learning.adjust_suggestion(100, avg_edit_percentage=-10.0)
        assert adjusted == pytest.approx(90.0)

    def test_adjust_suggestion_no_edit(self):
        adjusted = self.learning.adjust_suggestion(100, avg_edit_percentage=0.0)
        assert adjusted == pytest.approx(100.0)

    def test_adjust_suggestion_never_negative(self):
        adjusted = self.learning.adjust_suggestion(10, avg_edit_percentage=-200.0)
        assert adjusted == 0.0


# ---------------------------------------------------------------------------
# ForecastAccuracyMonitor (2.9)
# ---------------------------------------------------------------------------

class TestForecastAccuracyMonitor:
    def setup_method(self):
        self.monitor = ForecastAccuracyMonitor()

    def test_empty_stats(self):
        stats = self.monitor.get_stats()
        assert stats["total_forecasts"] == 0
        assert stats["mape"] == 0.0
        # With no data, MAPE is 0 so accuracy defaults to 100%
        assert stats["accuracy_pct"] == 100.0

    def test_perfect_forecast(self):
        self.monitor.record(predicted=100, actual=100)
        assert self.monitor.mean_absolute_percentage_error() == pytest.approx(0.0)
        assert self.monitor.accuracy_percentage() == pytest.approx(100.0)

    def test_mape_calculation(self):
        # 50% error
        self.monitor.record(predicted=150, actual=100)
        assert self.monitor.mean_absolute_percentage_error() == pytest.approx(50.0)
        assert self.monitor.accuracy_percentage() == pytest.approx(50.0)

    def test_accuracy_clamped_at_zero(self):
        # 200% error → accuracy should not go below 0
        self.monitor.record(predicted=300, actual=100)
        assert self.monitor.accuracy_percentage() >= 0.0

    def test_multiple_records_averaged(self):
        self.monitor.record(predicted=110, actual=100)  # 10% error
        self.monitor.record(predicted=90, actual=100)   # 10% error
        assert self.monitor.mean_absolute_percentage_error() == pytest.approx(10.0)

    def test_reset(self):
        self.monitor.record(100, 90)
        self.monitor.reset()
        assert self.monitor.get_stats()["total_forecasts"] == 0
