"""
Intelligent Credit Agent
Handles credit scoring, collection strategy, timing optimization,
auto-suspend/restore, and default prediction.
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
# 4.1 Credit Scoring Algorithm
# ---------------------------------------------------------------------------

def calculate_credit_score(customer_id: str, db_conn=None) -> float:
    """
    Calculate credit score (0-100) for a customer.

    Components:
    - Base score: 50
    - Payment history: max +30 / -30
    - Order frequency: max +10
    - Total spending: max +10
    """
    supabase = db_conn or _get_supabase()

    # 4.1.1 Base score
    base_score = 50.0

    # Fetch payment history
    try:
        ph_result = (
            supabase.table("payment_history")
            .select("days_to_payment, was_late")
            .eq("customer_id", customer_id)
            .execute()
        )
        payment_history = ph_result.data or []
    except Exception as exc:
        logger.error("calculate_credit_score: payment_history fetch error: %s", exc)
        payment_history = []

    # 4.1.2 Payment history score
    total_payments = len(payment_history)
    if total_payments > 0:
        on_time = sum(1 for p in payment_history if (p.get("days_to_payment") or 0) <= 7)
        late = sum(1 for p in payment_history if (p.get("days_to_payment") or 0) > 7)
        payment_score = ((on_time - late) / total_payments) * 30
    else:
        payment_score = 0.0

    # Fetch orders
    try:
        orders_result = (
            supabase.table("orders")
            .select("id, total_amount")
            .eq("customer_id", customer_id)
            .execute()
        )
        orders = orders_result.data or []
    except Exception as exc:
        logger.error("calculate_credit_score: orders fetch error: %s", exc)
        orders = []

    # 4.1.3 Order frequency score
    order_count = len(orders)
    frequency_score = min(order_count / 2, 10.0)

    # 4.1.4 Spending score
    total_spent = sum(float(o.get("total_amount", 0)) for o in orders)
    spending_score = min(total_spent / 1000, 10.0)

    # 4.1.5 Clamp between 0-100
    final_score = base_score + payment_score + frequency_score + spending_score
    return max(0.0, min(100.0, final_score))


# ---------------------------------------------------------------------------
# 4.2 Credit Limit Calculation
# ---------------------------------------------------------------------------

def calculate_credit_limit(credit_score: float) -> float:
    """
    Return credit limit based on score tier.

    4.2.1 Score >= 70: ₹5000
    4.2.2 Score 50-69: ₹2000
    4.2.3 Score < 50: Cash only (0)
    """
    if credit_score >= 70:
        return 5000.0
    elif credit_score >= 50:
        return 2000.0
    else:
        return 0.0


# ---------------------------------------------------------------------------
# 4.4 Collection Strategy
# ---------------------------------------------------------------------------

def get_collection_strategy(days_overdue: int) -> dict:
    """
    Return collection strategy based on days overdue.

    4.4.2 Day 3: friendly reminder
    4.4.3 Day 7: firm reminder
    4.4.4 Day 15: urgent reminder
    4.4.5 Day 30+: suspend credit + final notice
    """
    if days_overdue <= 3:
        return {
            "tone": "friendly",
            "message": "Hi! Just a gentle reminder about your pending payment of ₹{amount} 😊",
            "urgency": "low",
            "reminder_type": "friendly",
        }
    elif days_overdue <= 7:
        return {
            "tone": "neutral",
            "message": "Payment of ₹{amount} pending for {days} days. Please pay soon.",
            "urgency": "medium",
            "reminder_type": "neutral",
        }
    elif days_overdue <= 15:
        return {
            "tone": "firm",
            "message": "⚠️ Payment of ₹{amount} overdue by {days} days. Please clear immediately.",
            "urgency": "high",
            "reminder_type": "firm",
        }
    else:
        return {
            "tone": "strict",
            "message": "🚨 URGENT: Payment of ₹{amount} overdue by {days} days. Credit suspended until payment received.",
            "urgency": "critical",
            "reminder_type": "strict",
            "action": "suspend_credit",
        }


# ---------------------------------------------------------------------------
# 4.5 Timing Optimization
# ---------------------------------------------------------------------------

def get_optimal_reminder_time(customer_id: str, db_conn=None) -> str:
    """
    4.5.1-4.5.3 Learn optimal notification time per customer.
    Returns HH:MM string (24h). Defaults to 18:00 if no data.
    """
    supabase = db_conn or _get_supabase()
    try:
        result = (
            supabase.table("notification_response_times")
            .select("response_hour")
            .eq("customer_id", customer_id)
            .not_.is_("response_hour", "null")
            .execute()
        )
        rows = result.data or []
        if not rows:
            return "18:00"

        # Count responses per hour
        hour_counts: dict[int, int] = {}
        for row in rows:
            h = row.get("response_hour")
            if h is not None:
                hour_counts[h] = hour_counts.get(h, 0) + 1

        if not hour_counts:
            return "18:00"

        best_hour = max(hour_counts, key=hour_counts.get)
        return f"{best_hour:02d}:00"
    except Exception as exc:
        logger.error("get_optimal_reminder_time error: %s", exc)
        return "18:00"


# ---------------------------------------------------------------------------
# 4.6 Auto-Suspend / Auto-Restore
# ---------------------------------------------------------------------------

def auto_suspend_credit(customer_id: str, db_conn=None) -> bool:
    """
    4.6.1 Suspend credit for a customer with 30+ days overdue payment.
    4.6.3 Notifies customer of status change (logs notification).
    """
    supabase = db_conn or _get_supabase()
    try:
        supabase.table("customers").update(
            {"credit_suspended": True}
        ).eq("id", customer_id).execute()

        # Log the suspension event
        logger.info("Credit suspended for customer %s", customer_id)
        return True
    except Exception as exc:
        logger.error("auto_suspend_credit error: %s", exc)
        return False


def auto_restore_credit(customer_id: str, db_conn=None) -> bool:
    """
    4.6.2 Restore credit after payment is received.
    4.6.3 Notifies customer of status change (logs notification).
    Recalculates credit score and limit.
    """
    supabase = db_conn or _get_supabase()
    try:
        new_score = calculate_credit_score(customer_id, db_conn=supabase)
        new_limit = calculate_credit_limit(new_score)

        supabase.table("customers").update(
            {
                "credit_suspended": False,
                "credit_score": int(new_score),
                "credit_limit": new_limit,
            }
        ).eq("id", customer_id).execute()

        logger.info(
            "Credit restored for customer %s — score=%.1f limit=%.0f",
            customer_id,
            new_score,
            new_limit,
        )
        return True
    except Exception as exc:
        logger.error("auto_restore_credit error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# 4.7 Default Prediction
# ---------------------------------------------------------------------------

def predict_default_risk(customer_id: str, db_conn=None) -> dict:
    """
    4.7.1-4.7.4 Predict default probability and flag high-risk customers.

    Returns:
        {
            "default_probability": float (0-1),
            "risk_level": "low" | "medium" | "high",
            "risk_indicators": list[str],
            "recommended_action": str,
        }
    """
    supabase = db_conn or _get_supabase()
    risk_indicators: list[str] = []
    risk_score = 0.0

    # 4.7.1 Identify risk indicators
    try:
        customer_result = (
            supabase.table("customers")
            .select("credit_score, credit_suspended, credit_limit")
            .eq("id", customer_id)
            .single()
            .execute()
        )
        customer = customer_result.data or {}
    except Exception as exc:
        logger.error("predict_default_risk: customer fetch error: %s", exc)
        customer = {}

    credit_score = float(customer.get("credit_score") or 50)
    is_suspended = bool(customer.get("credit_suspended", False))

    # Low credit score
    if credit_score < 40:
        risk_score += 0.35
        risk_indicators.append("low_credit_score")
    elif credit_score < 55:
        risk_score += 0.15
        risk_indicators.append("below_average_credit_score")

    # Currently suspended
    if is_suspended:
        risk_score += 0.30
        risk_indicators.append("credit_currently_suspended")

    # Payment history
    try:
        ph_result = (
            supabase.table("payment_history")
            .select("days_to_payment, was_late")
            .eq("customer_id", customer_id)
            .execute()
        )
        payment_history = ph_result.data or []
    except Exception:
        payment_history = []

    if payment_history:
        late_count = sum(1 for p in payment_history if p.get("was_late"))
        late_ratio = late_count / len(payment_history)
        if late_ratio > 0.5:
            risk_score += 0.25
            risk_indicators.append("high_late_payment_ratio")
        elif late_ratio > 0.25:
            risk_score += 0.10
            risk_indicators.append("moderate_late_payment_ratio")
    else:
        # No payment history — slight risk
        risk_score += 0.05
        risk_indicators.append("no_payment_history")

    # Outstanding overdue orders
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        overdue_result = (
            supabase.table("orders")
            .select("id")
            .eq("customer_id", customer_id)
            .eq("payment_status", "unpaid")
            .lte("created_at", cutoff)
            .execute()
        )
        overdue_count = len(overdue_result.data or [])
        if overdue_count > 0:
            risk_score += min(overdue_count * 0.10, 0.30)
            risk_indicators.append(f"overdue_orders_{overdue_count}")
    except Exception:
        pass

    # 4.7.2 Calculate default probability (clamp 0-1)
    default_probability = max(0.0, min(1.0, risk_score))

    # 4.7.3 Flag high-risk customers
    if default_probability >= 0.6:
        risk_level = "high"
    elif default_probability >= 0.3:
        risk_level = "medium"
    else:
        risk_level = "low"

    # 4.7.4 Recommend actions
    if risk_level == "high":
        recommended_action = "suspend_credit_and_contact_immediately"
    elif risk_level == "medium":
        recommended_action = "send_firm_reminder_and_monitor"
    else:
        recommended_action = "continue_normal_operations"

    return {
        "default_probability": round(default_probability, 3),
        "risk_level": risk_level,
        "risk_indicators": risk_indicators,
        "recommended_action": recommended_action,
    }


# ---------------------------------------------------------------------------
# 4.4.1 / 4.9 Main Collection Cycle
# ---------------------------------------------------------------------------

def run_collection_cycle(store_id: str, db_conn=None) -> dict:
    """
    4.4.1 Main collection loop: find overdue orders and apply strategy.
    Returns summary of actions taken.
    """
    supabase = db_conn or _get_supabase()
    actions_taken = []
    suspended_count = 0
    reminders_sent = 0

    try:
        # Get all unpaid credit orders for the store
        orders_result = (
            supabase.table("orders")
            .select("id, customer_id, total_amount, created_at")
            .eq("store_id", store_id)
            .eq("payment_status", "unpaid")
            .eq("is_credit", True)
            .execute()
        )
        orders = orders_result.data or []
    except Exception as exc:
        logger.error("run_collection_cycle: orders fetch error: %s", exc)
        return {"error": str(exc), "actions_taken": []}

    now = datetime.now(timezone.utc)

    for order in orders:
        try:
            order_date = datetime.fromisoformat(
                order["created_at"].replace("Z", "+00:00")
            )
            days_overdue = (now - order_date).days
            customer_id = order["customer_id"]
            amount = float(order.get("total_amount", 0))

            strategy = get_collection_strategy(days_overdue)

            # 4.4.5 Day 30+: auto-suspend
            if strategy.get("action") == "suspend_credit":
                auto_suspend_credit(customer_id, db_conn=supabase)
                suspended_count += 1

            # Log reminder
            try:
                supabase.table("payment_reminders").insert(
                    {
                        "customer_id": customer_id,
                        "order_id": order["id"],
                        "reminder_type": strategy["reminder_type"],
                    }
                ).execute()
                reminders_sent += 1
            except Exception as exc:
                logger.warning("Failed to log reminder: %s", exc)

            actions_taken.append(
                {
                    "order_id": order["id"],
                    "customer_id": customer_id,
                    "days_overdue": days_overdue,
                    "strategy": strategy["tone"],
                    "amount": amount,
                }
            )
        except Exception as exc:
            logger.error("run_collection_cycle: order processing error: %s", exc)

    logger.info(
        "Collection cycle for store %s: %d orders processed, %d reminders, %d suspended",
        store_id,
        len(orders),
        reminders_sent,
        suspended_count,
    )
    return {
        "orders_processed": len(orders),
        "reminders_sent": reminders_sent,
        "suspended_count": suspended_count,
        "actions_taken": actions_taken,
    }


# ---------------------------------------------------------------------------
# 4.12 Collection Rate Metrics
# ---------------------------------------------------------------------------

def get_collection_metrics(store_id: str, db_conn=None) -> dict:
    """
    4.12 Return collection rate and related metrics for a store.
    """
    supabase = db_conn or _get_supabase()
    try:
        # Total credit orders
        all_credit = (
            supabase.table("orders")
            .select("id, total_amount, payment_status")
            .eq("store_id", store_id)
            .eq("is_credit", True)
            .execute()
        )
        all_orders = all_credit.data or []
        total_credit_amount = sum(float(o.get("total_amount", 0)) for o in all_orders)

        paid_orders = [o for o in all_orders if o.get("payment_status") == "paid"]
        paid_amount = sum(float(o.get("total_amount", 0)) for o in paid_orders)

        collection_rate = (paid_amount / total_credit_amount * 100) if total_credit_amount > 0 else 0.0

        # Overdue (unpaid > 7 days)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        overdue_result = (
            supabase.table("orders")
            .select("id, total_amount")
            .eq("store_id", store_id)
            .eq("is_credit", True)
            .eq("payment_status", "unpaid")
            .lte("created_at", cutoff)
            .execute()
        )
        overdue_orders = overdue_result.data or []
        overdue_amount = sum(float(o.get("total_amount", 0)) for o in overdue_orders)

        # Reminders sent
        reminders_result = (
            supabase.table("payment_reminders")
            .select("id, payment_received")
            .execute()
        )
        reminders = reminders_result.data or []
        reminders_total = len(reminders)
        reminders_converted = sum(1 for r in reminders if r.get("payment_received"))
        reminder_conversion_rate = (
            (reminders_converted / reminders_total * 100) if reminders_total > 0 else 0.0
        )

        return {
            "store_id": store_id,
            "total_credit_orders": len(all_orders),
            "total_credit_amount": round(total_credit_amount, 2),
            "paid_amount": round(paid_amount, 2),
            "collection_rate_pct": round(collection_rate, 1),
            "overdue_orders": len(overdue_orders),
            "overdue_amount": round(overdue_amount, 2),
            "reminders_sent": reminders_total,
            "reminder_conversion_rate_pct": round(reminder_conversion_rate, 1),
        }
    except Exception as exc:
        logger.error("get_collection_metrics error: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 7.3.4 / 7.3.5 Credit & Fraud Collaboration
# ---------------------------------------------------------------------------

async def publish_credit_risk_high(
    customer_id: str,
    risk_score: float,
    outstanding_amount: float,
) -> None:
    """7.3.4 Publish CREDIT_RISK_HIGH to coordinator after detecting high credit risk."""
    try:
        from agents.message_bus.protocol import AgentMessage, AgentName, MessageType
        from agents.message_bus.publisher import AgentMessagePublisher

        publisher = AgentMessagePublisher()
        msg = AgentMessage(
            from_agent=AgentName.CREDIT.value,
            to_agent=AgentName.COORDINATOR.value,
            message_type=MessageType.CREDIT_RISK_HIGH,
            data={
                "customer_id": customer_id,
                "risk_score": risk_score,
                "outstanding_amount": outstanding_amount,
            },
            priority=8,
        )
        await publisher.publish(msg)
        logger.info("Published CREDIT_RISK_HIGH for customer %s", customer_id)
    except Exception as exc:
        logger.error("publish_credit_risk_high error: %s", exc)


async def publish_fraud_detected(
    customer_id: str,
    risk_score: float,
    flags: list,
) -> None:
    """7.3.5 Publish FRAUD_DETECTED to coordinator after detecting fraud."""
    try:
        from agents.message_bus.protocol import AgentMessage, AgentName, MessageType
        from agents.message_bus.publisher import AgentMessagePublisher

        publisher = AgentMessagePublisher()
        msg = AgentMessage(
            from_agent=AgentName.FRAUD.value,
            to_agent=AgentName.COORDINATOR.value,
            message_type=MessageType.FRAUD_DETECTED,
            data={
                "customer_id": customer_id,
                "risk_score": risk_score,
                "flags": flags,
            },
            priority=9,
        )
        await publisher.publish(msg)
        logger.info("Published FRAUD_DETECTED for customer %s", customer_id)
    except Exception as exc:
        logger.error("publish_fraud_detected error: %s", exc)
