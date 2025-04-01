"""Tests for the Business Intelligence Agent (task 6)."""
from __future__ import annotations
import sys, os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.bi_agent import (
    calculate_trends, detect_anomalies, analyze_profitability,
    forecast_revenue, forecast_stockouts, forecast_churn,
)


def _make_chain(data):
    result = MagicMock()
    result.data = data
    c = MagicMock()
    c.execute.return_value = result
    for m in ("eq", "gte", "lt", "lte", "select", "order", "limit", "single"):
        getattr(c, m).return_value = c
    c.not_ = c
    c.is_ = c
    return c


def _make_db(table_map):
    mock = MagicMock()
    counts = {}
    def side(name):
        counts[name] = counts.get(name, 0) + 1
        data = table_map.get(name, [])
        if data and isinstance(data[0], list):
            idx = counts[name] - 1
            actual = data[idx] if idx < len(data) else []
        else:
            actual = data
        return _make_chain(actual)
    mock.table.side_effect = side
    return mock


def _o(amount, days_ago=0, product="Rice"):
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "total_amount": str(amount), "created_at": dt.isoformat(),
        "profit_amount": str(amount * 0.2), "customer_id": "c1",
        "customers": {"name": "T"},
        "order_items": [{"quantity": "1", "unit_price": str(amount),
                         "product_id": "p1", "products": {"name": product}}],
    }


class TestCalculateTrends:
    def test_up_trend(self):
        this_week = [_o(1000, i) for i in range(7)]
        last_week = [_o(500, i + 7) for i in range(7)]
        db = _make_db({"orders": [this_week, last_week]})
        r = calculate_trends("s1", db_conn=db)
        assert r["trend"] == "up"
        assert r["change_percentage"] > 0
        assert r["this_week_revenue"] == pytest.approx(7000.0)

    def test_down_trend(self):
        this_week = [_o(200, i) for i in range(7)]
        last_week = [_o(1000, i + 7) for i in range(7)]
        db = _make_db({"orders": [this_week, last_week]})
        r = calculate_trends("s1", db_conn=db)
        assert r["trend"] == "down"

    def test_flat_trend(self):
        this_week = [_o(500, i) for i in range(7)]
        last_week = [_o(500, i + 7) for i in range(7)]
        db = _make_db({"orders": [this_week, last_week]})
        r = calculate_trends("s1", db_conn=db)
        assert r["trend"] == "flat"

    def test_no_last_week_gives_100pct(self):
        this_week = [_o(500, i) for i in range(3)]
        db = _make_db({"orders": [this_week, []]})
        r = calculate_trends("s1", db_conn=db)
        assert r["change_percentage"] == pytest.approx(100.0)

    def test_top_products_sorted(self):
        this_week = [_o(300, 1, "Rice"), _o(500, 2, "Sugar"), _o(100, 3, "Salt")]
        db = _make_db({"orders": [this_week, []]})
        r = calculate_trends("s1", db_conn=db)
        assert len(r["top_products"]) > 0
        revs = [p["revenue"] for p in r["top_products"]]
        assert revs == sorted(revs, reverse=True)

    def test_insights_non_empty(self):
        this_week = [_o(1000, i) for i in range(7)]
        last_week = [_o(500, i + 7) for i in range(7)]
        db = _make_db({"orders": [this_week, last_week]})
        r = calculate_trends("s1", db_conn=db)
        assert len(r["insights"]) > 0

    def test_seasonal_pattern_all_days(self):
        db = _make_db({"orders": [[], []]})
        r = calculate_trends("s1", db_conn=db)
        assert set(r["seasonal_pattern"].keys()) == {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}


class TestDetectAnomalies:
    def test_low_order_anomaly(self):
        orders_30d = [_o(100, d % 30) for d in range(300)]
        today = [_o(100, 0)]
        db = _make_db({"orders": [orders_30d, today], "inventory": []})
        anomalies = detect_anomalies("s1", db_conn=db)
        order_a = [a for a in anomalies if "order_count" in a["type"]]
        assert len(order_a) > 0
        assert order_a[0]["severity"] == "high"

    def test_no_anomaly_normal_day(self):
        orders_30d = [_o(100, d % 30) for d in range(150)]
        today = [_o(100, 0) for _ in range(5)]
        db = _make_db({"orders": [orders_30d, today], "inventory": []})
        anomalies = detect_anomalies("s1", db_conn=db)
        order_a = [a for a in anomalies if "order_count" in a["type"]]
        assert len(order_a) == 0

    def test_inventory_low_detected(self):
        inv = [{"id": "i1", "quantity": "5", "reorder_threshold": "10", "products": {"name": "Rice"}}]
        db = _make_db({"orders": [[], []], "inventory": inv})
        anomalies = detect_anomalies("s1", db_conn=db)
        inv_a = [a for a in anomalies if a["type"] == "inventory_low"]
        assert len(inv_a) == 1
        assert inv_a[0]["product_name"] == "Rice"

    def test_zero_stock_is_critical(self):
        inv = [{"id": "i1", "quantity": "0", "reorder_threshold": "10", "products": {"name": "Sugar"}}]
        db = _make_db({"orders": [[], []], "inventory": inv})
        anomalies = detect_anomalies("s1", db_conn=db)
        inv_a = [a for a in anomalies if a["type"] == "inventory_low"]
        assert inv_a[0]["severity"] == "critical"


class TestAnalyzeProfitability:
    def test_low_margin_flagged(self):
        items = [{"quantity": "10", "unit_price": "100", "product_id": "p1",
                  "products": {"name": "Low Margin", "cost_price": "95"}}]
        db = _make_db({"order_items": items, "orders": []})
        r = analyze_profitability("s1", db_conn=db)
        assert len(r["low_margin_products"]) == 1
        assert r["low_margin_products"][0]["margin_pct"] < 10

    def test_recommendations_for_low_margin(self):
        items = [{"quantity": "10", "unit_price": "100", "product_id": "p1",
                  "products": {"name": "Cheap Product", "cost_price": "98"}}]
        db = _make_db({"order_items": items, "orders": []})
        r = analyze_profitability("s1", db_conn=db)
        assert any("Cheap Product" in rec for rec in r["recommendations"])

    def test_healthy_margin_not_flagged(self):
        items = [{"quantity": "10", "unit_price": "100", "product_id": "p1",
                  "products": {"name": "Good Product", "cost_price": "50"}}]
        db = _make_db({"order_items": items, "orders": []})
        r = analyze_profitability("s1", db_conn=db)
        assert len(r["low_margin_products"]) == 0

    def test_margin_calculation(self):
        items = [{"quantity": "10", "unit_price": "100", "product_id": "p1",
                  "products": {"name": "Test", "cost_price": "80"}}]
        db = _make_db({"order_items": items, "orders": []})
        r = analyze_profitability("s1", db_conn=db)
        assert r["product_profitability"][0]["margin_pct"] == pytest.approx(20.0)


class TestForecastRevenue:
    def _linear_orders(self, base=100.0, slope=10.0):
        now = datetime.now(timezone.utc)
        return [
            {"total_amount": str(base + slope * i),
             "created_at": (now - timedelta(days=29 - i)).isoformat()}
            for i in range(30)
        ]

    def test_returns_7_days(self):
        db = _make_db({"orders": self._linear_orders()})
        r = forecast_revenue("s1", db_conn=db)
        assert len(r["daily_forecast"]) == 7

    def test_non_negative_revenue(self):
        db = _make_db({"orders": self._linear_orders()})
        r = forecast_revenue("s1", db_conn=db)
        for d in r["daily_forecast"]:
            assert d["predicted_revenue"] >= 0

    def test_confidence_valid(self):
        db = _make_db({"orders": self._linear_orders()})
        r = forecast_revenue("s1", db_conn=db)
        assert r["confidence"] in ("high", "medium", "low")

    def test_forecast_accuracy_80pct(self):
        """6.8: R2 >= 0.8 on perfect linear data."""
        db = _make_db({"orders": self._linear_orders(base=100.0, slope=10.0)})
        r = forecast_revenue("s1", db_conn=db)
        assert r["r_squared"] >= 0.8, f"R2={r['r_squared']:.3f} < 0.8"

    def test_empty_orders_safe_defaults(self):
        db = _make_db({"orders": []})
        r = forecast_revenue("s1", db_conn=db)
        assert r["next_7_days_total"] == 0.0
        assert r["confidence"] == "low"

    def test_confidence_interval_valid(self):
        db = _make_db({"orders": self._linear_orders()})
        r = forecast_revenue("s1", db_conn=db)
        assert r["confidence_interval"]["lower"] <= r["confidence_interval"]["upper"]


class TestForecastChurn:
    def test_calculation(self):
        customers = (
            [{"id": f"c{i}", "churn_risk_level": "high", "avg_order_interval": 30, "last_order_date": None} for i in range(10)]
            + [{"id": f"c{i+10}", "churn_risk_level": "medium", "avg_order_interval": 30, "last_order_date": None} for i in range(10)]
            + [{"id": f"c{i+20}", "churn_risk_level": None, "avg_order_interval": 30, "last_order_date": None} for i in range(5)]
        )
        db = _make_db({"customers": customers})
        r = forecast_churn("s1", db_conn=db)
        assert r["high_risk_count"] == 10
        assert r["medium_risk_count"] == 10
        assert r["predicted_churn_30d"] == 11
        assert r["total_customers"] == 25

    def test_no_risk_zero_churn(self):
        customers = [{"id": f"c{i}", "churn_risk_level": None, "avg_order_interval": 30, "last_order_date": None} for i in range(10)]
        db = _make_db({"customers": customers})
        r = forecast_churn("s1", db_conn=db)
        assert r["predicted_churn_30d"] == 0


class TestForecastStockouts:
    def test_critical_stockout(self):
        inv = [{"id": "i1", "quantity": "3", "product_id": "p1", "products": {"name": "Rice"}}]
        sold = [{"quantity": "1", "orders": {"store_id": "s", "created_at": "2024-01-01"}} for _ in range(30)]
        db = _make_db({"inventory": inv, "order_items": sold})
        preds = forecast_stockouts("s1", db_conn=db)
        assert len(preds) > 0
        rice = next((p for p in preds if p["product_name"] == "Rice"), None)
        assert rice is not None
        assert rice["risk"] in ("critical", "high")

    def test_no_velocity_low_risk(self):
        inv = [{"id": "i1", "quantity": "100", "product_id": "p1", "products": {"name": "Slow"}}]
        db = _make_db({"inventory": inv, "order_items": []})
        preds = forecast_stockouts("s1", db_conn=db)
        assert preds[0]["risk"] == "low"
        assert preds[0]["days_until_stockout"] == 999
