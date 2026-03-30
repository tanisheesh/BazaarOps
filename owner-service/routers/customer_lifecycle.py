"""
Customer Lifecycle analytics API endpoints.
Provides VIP, at-risk, and segment dashboard data.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from supabase import create_client
import os

router = APIRouter(prefix="/api/owner/customers", tags=["customer-lifecycle"])


def _get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
    )


# ---------------------------------------------------------------------------
# GET /api/owner/customers/vip/{store_id}
# ---------------------------------------------------------------------------

@router.get("/vip/{store_id}")
async def get_vip_customers(store_id: str):
    """Return all VIP customers for a store."""
    try:
        supabase = _get_supabase()
        result = (
            supabase.table("customers")
            .select("id, name, phone, is_vip, last_order_date, churn_risk_level")
            .eq("store_id", store_id)
            .eq("is_vip", True)
            .execute()
        )
        customers = result.data or []
        return {
            "success": True,
            "vip_customers": customers,
            "count": len(customers),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/owner/customers/at-risk/{store_id}
# ---------------------------------------------------------------------------

@router.get("/at-risk/{store_id}")
async def get_at_risk_customers(store_id: str):
    """Return customers with churn risk for a store."""
    try:
        supabase = _get_supabase()
        result = (
            supabase.table("customers")
            .select("id, name, phone, churn_risk_level, last_order_date, avg_order_interval")
            .eq("store_id", store_id)
            .not_.is_("churn_risk_level", "null")
            .execute()
        )
        customers = result.data or []
        high_risk = [c for c in customers if c.get("churn_risk_level") == "high"]
        medium_risk = [c for c in customers if c.get("churn_risk_level") == "medium"]
        return {
            "success": True,
            "at_risk_customers": customers,
            "high_risk_count": len(high_risk),
            "medium_risk_count": len(medium_risk),
            "total_count": len(customers),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/owner/customers/segments/{store_id}
# ---------------------------------------------------------------------------

@router.get("/segments/{store_id}")
async def get_customer_segments(store_id: str):
    """Return customer segment breakdown for the analytics dashboard."""
    try:
        supabase = _get_supabase()

        # Total customers
        all_customers = (
            supabase.table("customers")
            .select("id, is_vip, churn_risk_level, last_order_date, created_at")
            .eq("store_id", store_id)
            .execute()
        )
        customers = all_customers.data or []
        total = len(customers)

        vip_count = sum(1 for c in customers if c.get("is_vip"))
        at_risk_count = sum(1 for c in customers if c.get("churn_risk_level"))
        high_risk_count = sum(
            1 for c in customers if c.get("churn_risk_level") == "high"
        )

        # Segment table entries
        segments_result = (
            supabase.table("customer_segments")
            .select("segment_type")
            .execute()
        )
        segment_counts: dict[str, int] = {}
        for row in segments_result.data or []:
            seg = row.get("segment_type", "unknown")
            segment_counts[seg] = segment_counts.get(seg, 0) + 1

        return {
            "success": True,
            "store_id": store_id,
            "summary": {
                "total_customers": total,
                "vip_customers": vip_count,
                "at_risk_customers": at_risk_count,
                "high_risk_customers": high_risk_count,
            },
            "segment_breakdown": segment_counts,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/owner/customers/birthday-stats/{store_id}
# ---------------------------------------------------------------------------

@router.get("/birthday-stats/{store_id}")
async def get_birthday_stats(store_id: str):
    """Return birthday wish stats and redemption rate."""
    try:
        supabase = _get_supabase()

        # Wishes sent to customers in this store
        result = (
            supabase.table("birthday_wishes_sent")
            .select("id, responded, customers!inner(store_id)")
            .eq("customers.store_id", store_id)
            .execute()
        )
        wishes = result.data or []
        total = len(wishes)
        responded = sum(1 for w in wishes if w.get("responded"))
        rate = round((responded / total * 100) if total > 0 else 0.0, 1)

        return {
            "success": True,
            "total_wishes_sent": total,
            "responded": responded,
            "redemption_rate_pct": rate,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/owner/customers/reengagement-stats/{store_id}
# ---------------------------------------------------------------------------

@router.get("/reengagement-stats/{store_id}")
async def get_reengagement_stats(store_id: str):
    """Return re-engagement message stats and response rate."""
    try:
        supabase = _get_supabase()

        result = (
            supabase.table("re_engagement_messages")
            .select("id, responded, message_number")
            .eq("store_id", store_id)
            .execute()
        )
        messages = result.data or []
        total = len(messages)
        responded = sum(1 for m in messages if m.get("responded"))
        rate = round((responded / total * 100) if total > 0 else 0.0, 1)
        first_msgs = sum(1 for m in messages if m.get("message_number") == 1)
        followup_msgs = sum(1 for m in messages if m.get("message_number") == 2)

        return {
            "success": True,
            "total_messages": total,
            "first_messages": first_msgs,
            "followup_messages": followup_msgs,
            "responded": responded,
            "response_rate_pct": rate,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
