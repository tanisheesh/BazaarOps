"""
Customer Lifecycle Agent
Handles VIP detection, churn prediction, and re-engagement strategy.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from supabase import create_client

logger = logging.getLogger(__name__)


def _get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
    )


# ---------------------------------------------------------------------------
# 3.1 VIP Detection
# ---------------------------------------------------------------------------

class VIPDetector:
    """Identifies VIP customers based on lifetime value and order frequency."""

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or _get_supabase()

    # 3.1.1 Calculate customer lifetime value
    def calculate_lifetime_value(self, orders: list[dict]) -> float:
        """Return total amount spent across all orders."""
        return sum(float(o.get("total_amount", 0)) for o in orders)

    # 3.1.2 Calculate order frequency (orders per month)
    def calculate_order_frequency(
        self, orders: list[dict], first_order_date: datetime
    ) -> float:
        """Return average orders per month since first order."""
        order_count = len(orders)
        if order_count == 0:
            return 0.0
        days_active = (datetime.now(timezone.utc) - first_order_date).days
        if days_active <= 0:
            return float(order_count)
        return order_count / (days_active / 30)

    # 3.1.3 Determine VIP status
    def is_vip(
        self,
        total_spent: float,
        order_count: int,
        order_frequency: float,
    ) -> bool:
        """Return True if customer meets any VIP criterion."""
        return (
            total_spent > 10000
            or order_count > 20
            or order_frequency > 4
        )

    # 3.1.4 Update is_vip flag in database for all customers in a store
    def update_vip_flags(self, store_id: str) -> dict:
        """Run VIP detection for all customers in a store and update DB."""
        try:
            customers_result = (
                self.supabase.table("customers")
                .select("id, created_at")
                .eq("store_id", store_id)
                .execute()
            )
            customers = customers_result.data or []

            updated_vip = 0
            updated_non_vip = 0

            for customer in customers:
                customer_id = customer["id"]

                orders_result = (
                    self.supabase.table("orders")
                    .select("total_amount, created_at")
                    .eq("customer_id", customer_id)
                    .execute()
                )
                orders = orders_result.data or []

                total_spent = self.calculate_lifetime_value(orders)
                order_count = len(orders)

                # Parse first order date
                if orders:
                    dates = sorted(o["created_at"] for o in orders)
                    first_order_date = datetime.fromisoformat(
                        dates[0].replace("Z", "+00:00")
                    )
                else:
                    first_order_date = datetime.fromisoformat(
                        customer["created_at"].replace("Z", "+00:00")
                    )

                freq = self.calculate_order_frequency(orders, first_order_date)
                vip_status = self.is_vip(total_spent, order_count, freq)

                self.supabase.table("customers").update(
                    {"is_vip": vip_status}
                ).eq("id", customer_id).execute()

                if vip_status:
                    updated_vip += 1
                else:
                    updated_non_vip += 1

            logger.info(
                "VIP update for store %s: %d VIP, %d non-VIP",
                store_id,
                updated_vip,
                updated_non_vip,
            )
            return {"vip_count": updated_vip, "non_vip_count": updated_non_vip}

        except Exception as exc:
            logger.error("update_vip_flags error: %s", exc)
            return {"vip_count": 0, "non_vip_count": 0}

    # 3.1.3 Identify top 20% customers by revenue
    def identify_top_customers(self, store_id: str) -> list[dict]:
        """Return the top 20% of customers by lifetime value."""
        try:
            customers_result = (
                self.supabase.table("customers")
                .select("id, name")
                .eq("store_id", store_id)
                .execute()
            )
            customers = customers_result.data or []

            scored = []
            for customer in customers:
                orders_result = (
                    self.supabase.table("orders")
                    .select("total_amount")
                    .eq("customer_id", customer["id"])
                    .execute()
                )
                total = self.calculate_lifetime_value(orders_result.data or [])
                scored.append({"customer": customer, "total_spent": total})

            scored.sort(key=lambda x: x["total_spent"], reverse=True)
            top_20_count = max(1, len(scored) // 5)
            return scored[:top_20_count]

        except Exception as exc:
            logger.error("identify_top_customers error: %s", exc)
            return []


# ---------------------------------------------------------------------------
# 3.4 Churn Prediction
# ---------------------------------------------------------------------------

class ChurnPredictor:
    """Detects customers at risk of churning."""

    DEFAULT_AVG_INTERVAL = 30  # days

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or _get_supabase()

    # 3.4.1 Calculate days since last order
    def days_since_last_order(self, last_order_date: datetime) -> int:
        """Return number of days since the customer's last order."""
        now = datetime.now(timezone.utc)
        if last_order_date.tzinfo is None:
            last_order_date = last_order_date.replace(tzinfo=timezone.utc)
        return (now - last_order_date).days

    # 3.4.2 Calculate average order interval
    def calculate_avg_interval(self, order_dates: list[datetime]) -> float:
        """Return average days between consecutive orders."""
        if len(order_dates) < 2:
            return float(self.DEFAULT_AVG_INTERVAL)
        sorted_dates = sorted(order_dates)
        intervals = [
            (sorted_dates[i] - sorted_dates[i - 1]).days
            for i in range(1, len(sorted_dates))
        ]
        return sum(intervals) / len(intervals)

    # 3.4.3 & 3.4.4 Detect churn risk and assign level
    def detect_churn_risk(
        self, days_since: int, avg_interval: float
    ) -> tuple[bool, str]:
        """Return (is_at_risk, risk_level). Risk if gap > 2x average interval."""
        is_at_risk = days_since > (avg_interval * 2)
        risk_level = "high" if days_since > 30 else "medium"
        return is_at_risk, risk_level

    # 3.4.5 Update churn_risk_level in database for all customers in a store
    def update_churn_risk(self, store_id: str) -> dict:
        """Run churn detection for all customers in a store and update DB."""
        try:
            customers_result = (
                self.supabase.table("customers")
                .select("id, last_order_date")
                .eq("store_id", store_id)
                .execute()
            )
            customers = customers_result.data or []

            at_risk_count = 0
            safe_count = 0

            for customer in customers:
                customer_id = customer["id"]
                last_order_raw = customer.get("last_order_date")

                if not last_order_raw:
                    # No orders yet – skip
                    continue

                last_order_date = datetime.fromisoformat(
                    last_order_raw.replace("Z", "+00:00")
                )

                # Get all order dates for interval calculation
                orders_result = (
                    self.supabase.table("orders")
                    .select("created_at")
                    .eq("customer_id", customer_id)
                    .execute()
                )
                order_dates = [
                    datetime.fromisoformat(o["created_at"].replace("Z", "+00:00"))
                    for o in (orders_result.data or [])
                ]

                avg_interval = self.calculate_avg_interval(order_dates)
                days_since = self.days_since_last_order(last_order_date)
                is_at_risk, risk_level = self.detect_churn_risk(days_since, avg_interval)

                update_data: dict = {
                    "avg_order_interval": int(avg_interval),
                    "churn_risk_level": risk_level if is_at_risk else None,
                }
                self.supabase.table("customers").update(update_data).eq(
                    "id", customer_id
                ).execute()

                if is_at_risk:
                    at_risk_count += 1
                else:
                    safe_count += 1

            logger.info(
                "Churn update for store %s: %d at risk, %d safe",
                store_id,
                at_risk_count,
                safe_count,
            )
            return {"at_risk_count": at_risk_count, "safe_count": safe_count}

        except Exception as exc:
            logger.error("update_churn_risk error: %s", exc)
            return {"at_risk_count": 0, "safe_count": 0}

    def get_at_risk_customers(self, store_id: str) -> list[dict]:
        """Return customers with a churn_risk_level set."""
        try:
            result = (
                self.supabase.table("customers")
                .select("id, name, telegram_chat_id, churn_risk_level, last_order_date")
                .eq("store_id", store_id)
                .not_.is_("churn_risk_level", "null")
                .execute()
            )
            return result.data or []
        except Exception as exc:
            logger.error("get_at_risk_customers error: %s", exc)
            return []


# ---------------------------------------------------------------------------
# 3.5 Re-engagement Strategy
# ---------------------------------------------------------------------------

class ReEngagementStrategy:
    """Generates and tracks re-engagement messages for at-risk customers."""

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or _get_supabase()

    # 3.5.1 Generate personalized message (no discounts)
    def generate_message(
        self, customer_name: str, days_since: int, message_number: int = 1
    ) -> str:
        """Return a personalized re-engagement message without discounts."""
        if message_number == 1:
            return (
                f"Hi {customer_name}! 👋 We miss you at the store. "
                f"It's been a while since your last order. "
                f"We have fresh stock waiting for you – come back and shop anytime! 🛒"
            )
        else:
            return (
                f"Hey {customer_name}! 😊 Just checking in – we haven't seen you in "
                f"{days_since} days. Your favourite products are still available. "
                f"We'd love to have you back! 🌟"
            )

    # 3.5.4 Track response rate
    def record_response(self, message_id: str) -> bool:
        """Mark a re-engagement message as responded."""
        try:
            self.supabase.table("re_engagement_messages").update(
                {"responded": True, "responded_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", message_id).execute()
            return True
        except Exception as exc:
            logger.error("record_response error: %s", exc)
            return False

    def get_pending_followups(self, store_id: str) -> list[dict]:
        """Return first messages sent 7+ days ago with no response (for follow-up)."""
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            result = (
                self.supabase.table("re_engagement_messages")
                .select("*, customers(name, telegram_chat_id, last_order_date)")
                .eq("store_id", store_id)
                .eq("message_number", 1)
                .eq("responded", False)
                .lte("sent_at", cutoff)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            logger.error("get_pending_followups error: %s", exc)
            return []

    def log_message(
        self,
        customer_id: str,
        store_id: str,
        message_text: str,
        message_number: int = 1,
    ) -> Optional[str]:
        """Persist a re-engagement message record and return its id."""
        try:
            result = (
                self.supabase.table("re_engagement_messages")
                .insert(
                    {
                        "customer_id": customer_id,
                        "store_id": store_id,
                        "message_number": message_number,
                        "message_text": message_text,
                        "responded": False,
                    }
                )
                .execute()
            )
            return result.data[0]["id"] if result.data else None
        except Exception as exc:
            logger.error("log_message error: %s", exc)
            return None
