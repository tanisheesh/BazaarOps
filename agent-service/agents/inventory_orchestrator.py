"""
Autonomous Inventory Orchestrator
Demand forecasting, reorder decision engine, and learning system.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from supabase import create_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Message bus helper (lazy import to avoid circular deps)
# ---------------------------------------------------------------------------

def _get_publisher():
    from agents.message_bus.publisher import AgentMessagePublisher
    return AgentMessagePublisher()


async def send_collaboration_message(from_agent: str, to_agent: str, message_type: str, data: dict, priority: int = 5) -> None:
    """Publish a collaboration message via the agent message bus."""
    try:
        from agents.message_bus.protocol import AgentMessage
        publisher = _get_publisher()
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            data=data,
            priority=priority,
        )
        await publisher.publish(msg)
    except Exception as exc:
        logger.error("send_collaboration_message error: %s", exc)

# ---------------------------------------------------------------------------
# Supabase helper
# ---------------------------------------------------------------------------

def _get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
    )


# ---------------------------------------------------------------------------
# 2.1 Demand Forecasting Module
# ---------------------------------------------------------------------------

class DemandForecastingModule:
    """Predicts future demand using historical sales data."""

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or _get_supabase()

    # 2.1.1 Fetch historical sales data
    def fetch_historical_sales(
        self, store_id: str, product_id: str, days: int = 30
    ) -> list[dict]:
        """Return daily sales quantities for the last *days* days."""
        try:
            since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            result = (
                self.supabase.table("order_items")
                .select("quantity, orders!inner(store_id, created_at)")
                .eq("product_id", product_id)
                .eq("orders.store_id", store_id)
                .gte("orders.created_at", since)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            logger.error("fetch_historical_sales error: %s", exc)
            return []

    # 2.1.2 Calculate moving average
    def calculate_moving_average(self, sales_data: list[dict], window: int = 7) -> float:
        """Return the moving average of daily sales over the last *window* days."""
        if not sales_data:
            return 0.0
        quantities = [float(item.get("quantity", 0)) for item in sales_data]
        window_data = quantities[-window:] if len(quantities) >= window else quantities
        return sum(window_data) / len(window_data) if window_data else 0.0

    # 2.1.3 Detect trends
    def detect_trend(self, sales_data: list[dict]) -> str:
        """Return 'increasing', 'decreasing', or 'stable'."""
        if len(sales_data) < 2:
            return "stable"
        quantities = [float(item.get("quantity", 0)) for item in sales_data]
        mid = len(quantities) // 2
        first_half_avg = sum(quantities[:mid]) / mid if mid else 0
        second_half_avg = sum(quantities[mid:]) / (len(quantities) - mid) if (len(quantities) - mid) else 0
        diff = second_half_avg - first_half_avg
        if diff > first_half_avg * 0.1:
            return "increasing"
        if diff < -first_half_avg * 0.1:
            return "decreasing"
        return "stable"

    # 2.1.4 Predict next 7-14 days demand
    def predict_demand(
        self, sales_data: list[dict], days_ahead: int = 14
    ) -> float:
        """Predict total demand for the next *days_ahead* days."""
        avg_daily = self.calculate_moving_average(sales_data, window=7)
        trend = self.detect_trend(sales_data)
        multiplier = 1.0
        if trend == "increasing":
            multiplier = 1.1
        elif trend == "decreasing":
            multiplier = 0.9
        return avg_daily * days_ahead * multiplier

    # 2.1.5 Calculate confidence score
    def calculate_confidence(self, sales_data: list[dict]) -> float:
        """Return a confidence score 0-100 based on data volume and variance."""
        if not sales_data:
            return 0.0
        n = len(sales_data)
        # More data → higher confidence (caps at 30 data points → 70 base)
        data_score = min(n / 30, 1.0) * 70
        # Low variance → higher confidence (up to 30 extra points)
        quantities = [float(item.get("quantity", 0)) for item in sales_data]
        if len(quantities) > 1:
            mean = sum(quantities) / len(quantities)
            variance = sum((q - mean) ** 2 for q in quantities) / len(quantities)
            cv = (variance ** 0.5 / mean) if mean > 0 else 1.0
            variance_score = max(0.0, 30.0 * (1 - min(cv, 1.0)))
        else:
            variance_score = 0.0
        return round(min(data_score + variance_score, 100.0), 1)

    def run_forecast(
        self, store_id: str, product_id: str, days_history: int = 30
    ) -> dict:
        """Full forecast pipeline for a product."""
        sales_data = self.fetch_historical_sales(store_id, product_id, days_history)
        avg_daily = self.calculate_moving_average(sales_data)
        trend = self.detect_trend(sales_data)
        forecast_7 = self.predict_demand(sales_data, 7)
        forecast_14 = self.predict_demand(sales_data, 14)
        confidence = self.calculate_confidence(sales_data)
        return {
            "avg_daily_sales": round(avg_daily, 3),
            "trend": trend,
            "forecast_7_days": round(forecast_7, 2),
            "forecast_14_days": round(forecast_14, 2),
            "confidence_score": confidence,
            "data_points": len(sales_data),
        }


# ---------------------------------------------------------------------------
# 2.2 Reorder Decision Engine
# ---------------------------------------------------------------------------

class ReorderDecisionEngine:
    """Decides whether to reorder and how much."""

    STOCKOUT_THRESHOLD_DAYS = 7

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or _get_supabase()

    # 2.2.1 Calculate days until stockout
    def days_until_stockout(self, current_stock: float, avg_daily_sales: float) -> float:
        """Return estimated days until stock runs out."""
        if avg_daily_sales <= 0:
            return float("inf")
        return current_stock / avg_daily_sales

    # 2.2.2 Determine if reorder needed
    def needs_reorder(self, current_stock: float, avg_daily_sales: float) -> bool:
        """Return True if stockout is within threshold."""
        days = self.days_until_stockout(current_stock, avg_daily_sales)
        return days < self.STOCKOUT_THRESHOLD_DAYS

    # 2.2.3 Calculate suggested quantity
    def suggested_quantity(
        self, forecast_14_days: float, current_stock: float, buffer: float = 1.2
    ) -> float:
        """Return suggested reorder quantity with buffer."""
        qty = (forecast_14_days - current_stock) * buffer
        return max(round(qty, 2), 0.0)

    # 2.2.4 Estimate reorder cost
    def estimate_cost(self, quantity: float, unit_cost: float) -> float:
        """Return estimated cost for the reorder."""
        return round(quantity * unit_cost, 2)

    def evaluate(
        self,
        store_id: str,
        product_id: str,
        current_stock: float,
        forecast: dict,
        unit_cost: float = 0.0,
    ) -> dict:
        """Full evaluation for a product."""
        avg_daily = forecast.get("avg_daily_sales", 0)
        forecast_14 = forecast.get("forecast_14_days", 0)
        days_left = self.days_until_stockout(current_stock, avg_daily)
        reorder = self.needs_reorder(current_stock, avg_daily)
        qty = self.suggested_quantity(forecast_14, current_stock) if reorder else 0.0
        cost = self.estimate_cost(qty, unit_cost)
        return {
            "days_until_stockout": round(days_left, 1) if days_left != float("inf") else None,
            "needs_reorder": reorder,
            "suggested_quantity": qty,
            "estimated_cost": cost,
        }


# ---------------------------------------------------------------------------
# 2.5 Learning System
# ---------------------------------------------------------------------------

class LearningSystem:
    """Tracks owner edits and adjusts future suggestions."""

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or _get_supabase()

    # 2.5.1 Track owner's edits
    def record_edit(
        self,
        reorder_id: str,
        suggested_quantity: float,
        approved_quantity: float,
    ) -> Optional[dict]:
        """Persist an approval record with edit info."""
        try:
            owner_edited = abs(approved_quantity - suggested_quantity) > 0.01
            edit_pct = (
                ((approved_quantity - suggested_quantity) / suggested_quantity * 100)
                if suggested_quantity > 0
                else 0.0
            )
            data = {
                "reorder_id": reorder_id,
                "suggested_quantity": suggested_quantity,
                "approved_quantity": approved_quantity,
                "owner_edited": owner_edited,
                "edit_percentage": round(edit_pct, 2),
            }
            result = self.supabase.table("reorder_approvals").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as exc:
            logger.error("record_edit error: %s", exc)
            return None

    # 2.5.2 Calculate edit patterns
    def get_edit_pattern(self, store_id: str, product_id: str) -> dict:
        """Return average edit percentage for a product in a store."""
        try:
            result = (
                self.supabase.table("reorder_approvals")
                .select(
                    "edit_percentage, pending_supplier_orders!inner(store_id, product_id)"
                )
                .eq("pending_supplier_orders.store_id", store_id)
                .eq("pending_supplier_orders.product_id", product_id)
                .eq("owner_edited", True)
                .execute()
            )
            rows = result.data or []
            if not rows:
                return {"avg_edit_percentage": 0.0, "sample_size": 0}
            pcts = [float(r.get("edit_percentage", 0)) for r in rows]
            return {
                "avg_edit_percentage": round(sum(pcts) / len(pcts), 2),
                "sample_size": len(pcts),
            }
        except Exception as exc:
            logger.error("get_edit_pattern error: %s", exc)
            return {"avg_edit_percentage": 0.0, "sample_size": 0}

    # 2.5.3 Adjust future suggestions
    def adjust_suggestion(
        self, base_quantity: float, avg_edit_percentage: float
    ) -> float:
        """Apply learned edit pattern to a base suggestion."""
        adjusted = base_quantity * (1 + avg_edit_percentage / 100)
        return max(round(adjusted, 2), 0.0)


# ---------------------------------------------------------------------------
# 7.3.1 / 7.3.2 Inventory & Demand Collaboration
# ---------------------------------------------------------------------------

class InventoryCollaborationMixin:
    """
    Mixin that adds message bus collaboration to inventory/demand modules.
    Call check_and_publish_stock_alerts() after updating stock levels.
    """

    message_bus = None  # Set to AgentMessagePublisher instance if needed

    async def check_and_publish_stock_alerts(
        self,
        store_id: str,
        product_id: str,
        current_stock: float,
        threshold: float,
        low_threshold: float = None,
        critical_threshold: float = None,
    ) -> None:
        """
        7.3.1 After detecting low/critical stock, publish to broadcast.
        7.3.2 After calculating forecast, publish DEMAND_FORECAST to reorder agent.
        """
        from agents.message_bus.protocol import AgentName, MessageType

        low_t = low_threshold if low_threshold is not None else threshold
        critical_t = critical_threshold if critical_threshold is not None else threshold * 0.5

        if current_stock <= critical_t:
            await send_collaboration_message(
                from_agent=AgentName.INVENTORY.value,
                to_agent="broadcast",
                message_type=MessageType.INVENTORY_CRITICAL,
                data={
                    "product_id": product_id,
                    "store_id": store_id,
                    "current_stock": current_stock,
                    "threshold": critical_t,
                },
                priority=9,
            )
        elif current_stock <= low_t:
            await send_collaboration_message(
                from_agent=AgentName.INVENTORY.value,
                to_agent="broadcast",
                message_type=MessageType.INVENTORY_LOW,
                data={
                    "product_id": product_id,
                    "store_id": store_id,
                    "current_stock": current_stock,
                    "threshold": low_t,
                },
                priority=7,
            )

    async def publish_demand_forecast(
        self,
        store_id: str,
        product_id: str,
        predicted_demand: float,
        confidence: float,
    ) -> None:
        """7.3.2 Publish demand forecast to reorder agent."""
        from agents.message_bus.protocol import AgentName, MessageType

        await send_collaboration_message(
            from_agent=AgentName.DEMAND.value,
            to_agent=AgentName.REORDER.value,
            message_type=MessageType.DEMAND_FORECAST,
            data={
                "product_id": product_id,
                "store_id": store_id,
                "predicted_demand": predicted_demand,
                "confidence": confidence,
            },
            priority=6,
        )
