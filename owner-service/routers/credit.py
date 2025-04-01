"""
Credit management API endpoints.
Provides credit score, payment history, at-risk customers, and suspend/restore.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from supabase import create_client
import os
import sys
from pathlib import Path

router = APIRouter(prefix="/api/owner/credit", tags=["credit"])


def _get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
    )


# ---------------------------------------------------------------------------
# GET /api/owner/credit/score/{customer_id}
# ---------------------------------------------------------------------------

@router.get("/score/{customer_id}")
async def get_credit_score(customer_id: str):
    """Return credit score and limit for a customer."""
    try:
        supabase = _get_supabase()
        result = (
            supabase.table("customers")
            .select("id, name, credit_score, credit_limit, credit_suspended")
            .eq("id", customer_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"success": True, "customer": result.data}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /api/owner/credit/update-limit/{customer_id}
# ---------------------------------------------------------------------------

@router.post("/update-limit/{customer_id}")
async def update_credit_limit(customer_id: str):
    """Recalculate and update credit score and limit for a customer."""
    try:
        supabase = _get_supabase()

        # Fetch payment history
        ph_result = (
            supabase.table("payment_history")
            .select("days_to_payment, was_late")
            .eq("customer_id", customer_id)
            .execute()
        )
        payment_history = ph_result.data or []

        # Fetch orders
        orders_result = (
            supabase.table("orders")
            .select("id, total_amount")
            .eq("customer_id", customer_id)
            .execute()
        )
        orders = orders_result.data or []

        # Calculate score
        base_score = 50.0
        total_payments = len(payment_history)
        if total_payments > 0:
            on_time = sum(1 for p in payment_history if (p.get("days_to_payment") or 0) <= 7)
            late = total_payments - on_time
            payment_score = ((on_time - late) / total_payments) * 30
        else:
            payment_score = 0.0

        order_count = len(orders)
        frequency_score = min(order_count / 2, 10.0)
        total_spent = sum(float(o.get("total_amount", 0)) for o in orders)
        spending_score = min(total_spent / 1000, 10.0)

        new_score = max(0.0, min(100.0, base_score + payment_score + frequency_score + spending_score))

        # Determine limit
        if new_score >= 70:
            new_limit = 5000.0
        elif new_score >= 50:
            new_limit = 2000.0
        else:
            new_limit = 0.0

        supabase.table("customers").update(
            {"credit_score": int(new_score), "credit_limit": new_limit}
        ).eq("id", customer_id).execute()

        return {
            "success": True,
            "customer_id": customer_id,
            "credit_score": int(new_score),
            "credit_limit": new_limit,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/owner/credit/payment-history/{customer_id}
# ---------------------------------------------------------------------------

@router.get("/payment-history/{customer_id}")
async def get_payment_history(customer_id: str):
    """Return payment history for a customer."""
    try:
        supabase = _get_supabase()
        result = (
            supabase.table("payment_history")
            .select("id, order_id, amount, due_date, paid_date, days_to_payment, was_late, created_at")
            .eq("customer_id", customer_id)
            .order("created_at", desc=True)
            .execute()
        )
        records = result.data or []
        return {
            "success": True,
            "customer_id": customer_id,
            "payment_history": records,
            "count": len(records),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/owner/credit/at-risk/{store_id}
# ---------------------------------------------------------------------------

@router.get("/at-risk/{store_id}")
async def get_at_risk_customers(store_id: str):
    """Return customers with high default risk for a store."""
    try:
        supabase = _get_supabase()

        # Customers with low credit score or suspended credit
        result = (
            supabase.table("customers")
            .select("id, name, phone, credit_score, credit_limit, credit_suspended")
            .eq("store_id", store_id)
            .execute()
        )
        customers = result.data or []

        at_risk = [
            c for c in customers
            if c.get("credit_suspended") or (c.get("credit_score") or 50) < 50
        ]

        return {
            "success": True,
            "store_id": store_id,
            "at_risk_customers": at_risk,
            "count": len(at_risk),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /api/owner/credit/suspend/{customer_id}
# ---------------------------------------------------------------------------

@router.post("/suspend/{customer_id}")
async def suspend_credit(customer_id: str):
    """Manually suspend credit for a customer."""
    try:
        supabase = _get_supabase()
        supabase.table("customers").update(
            {"credit_suspended": True}
        ).eq("id", customer_id).execute()
        return {"success": True, "customer_id": customer_id, "credit_suspended": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /api/owner/credit/restore/{customer_id}
# ---------------------------------------------------------------------------

@router.post("/restore/{customer_id}")
async def restore_credit(customer_id: str):
    """Restore credit for a customer after payment."""
    try:
        supabase = _get_supabase()

        # Recalculate score
        ph_result = (
            supabase.table("payment_history")
            .select("days_to_payment, was_late")
            .eq("customer_id", customer_id)
            .execute()
        )
        payment_history = ph_result.data or []
        orders_result = (
            supabase.table("orders")
            .select("id, total_amount")
            .eq("customer_id", customer_id)
            .execute()
        )
        orders = orders_result.data or []

        base_score = 50.0
        total_payments = len(payment_history)
        if total_payments > 0:
            on_time = sum(1 for p in payment_history if (p.get("days_to_payment") or 0) <= 7)
            late = total_payments - on_time
            payment_score = ((on_time - late) / total_payments) * 30
        else:
            payment_score = 0.0

        order_count = len(orders)
        frequency_score = min(order_count / 2, 10.0)
        total_spent = sum(float(o.get("total_amount", 0)) for o in orders)
        spending_score = min(total_spent / 1000, 10.0)

        new_score = max(0.0, min(100.0, base_score + payment_score + frequency_score + spending_score))
        new_limit = 5000.0 if new_score >= 70 else (2000.0 if new_score >= 50 else 0.0)

        supabase.table("customers").update(
            {
                "credit_suspended": False,
                "credit_score": int(new_score),
                "credit_limit": new_limit,
            }
        ).eq("id", customer_id).execute()

        return {
            "success": True,
            "customer_id": customer_id,
            "credit_suspended": False,
            "credit_score": int(new_score),
            "credit_limit": new_limit,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
