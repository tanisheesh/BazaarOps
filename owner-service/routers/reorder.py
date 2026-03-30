"""
Reorder management API endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client
import os

router = APIRouter(prefix="/api/owner/reorder", tags=["reorder"])


def _get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
    )


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class EditReorderRequest(BaseModel):
    quantity: float


# ---------------------------------------------------------------------------
# GET /api/owner/reorder/pending/{store_id}
# ---------------------------------------------------------------------------

@router.get("/pending/{store_id}")
async def get_pending_reorders(store_id: str):
    """Return all pending reorder requests for a store."""
    try:
        supabase = _get_supabase()
        result = (
            supabase.table("pending_supplier_orders")
            .select("*, products(name, unit, cost_price, supplier_name)")
            .eq("store_id", store_id)
            .eq("status", "pending")
            .order("created_at", desc=True)
            .execute()
        )
        return {"success": True, "reorders": result.data or [], "count": len(result.data or [])}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /api/owner/reorder/approve/{reorder_id}
# ---------------------------------------------------------------------------

@router.post("/approve/{reorder_id}")
async def approve_reorder(reorder_id: str):
    """Approve a pending reorder at the suggested quantity."""
    try:
        supabase = _get_supabase()

        # Fetch current record
        result = (
            supabase.table("pending_supplier_orders")
            .select("id, quantity, status")
            .eq("id", reorder_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Reorder not found")

        order = result.data
        if order["status"] not in ("pending",):
            raise HTTPException(
                status_code=400, detail=f"Cannot approve reorder in status '{order['status']}'"
            )

        suggested_qty = float(order["quantity"])

        # Update order
        supabase.table("pending_supplier_orders").update(
            {
                "owner_approved": True,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "status": "approved",
            }
        ).eq("id", reorder_id).execute()

        # Record approval (no edit)
        supabase.table("reorder_approvals").insert(
            {
                "reorder_id": reorder_id,
                "suggested_quantity": suggested_qty,
                "approved_quantity": suggested_qty,
                "owner_edited": False,
                "edit_percentage": 0.0,
            }
        ).execute()

        return {"success": True, "message": "Reorder approved", "reorder_id": reorder_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /api/owner/reorder/reject/{reorder_id}
# ---------------------------------------------------------------------------

@router.post("/reject/{reorder_id}")
async def reject_reorder(reorder_id: str):
    """Reject a pending reorder."""
    try:
        supabase = _get_supabase()

        result = (
            supabase.table("pending_supplier_orders")
            .select("id, status")
            .eq("id", reorder_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Reorder not found")

        supabase.table("pending_supplier_orders").update(
            {"status": "rejected", "owner_approved": False}
        ).eq("id", reorder_id).execute()

        return {"success": True, "message": "Reorder rejected", "reorder_id": reorder_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# PUT /api/owner/reorder/edit/{reorder_id}
# ---------------------------------------------------------------------------

@router.put("/edit/{reorder_id}")
async def edit_reorder(reorder_id: str, body: EditReorderRequest):
    """Edit the quantity of a pending reorder and approve it."""
    if body.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    try:
        supabase = _get_supabase()

        result = (
            supabase.table("pending_supplier_orders")
            .select("id, quantity, status")
            .eq("id", reorder_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Reorder not found")

        order = result.data
        suggested_qty = float(order["quantity"])
        approved_qty = body.quantity
        edit_pct = (
            ((approved_qty - suggested_qty) / suggested_qty * 100)
            if suggested_qty > 0
            else 0.0
        )

        # Update order with new quantity and approve
        supabase.table("pending_supplier_orders").update(
            {
                "quantity": approved_qty,
                "owner_approved": True,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "status": "approved",
            }
        ).eq("id", reorder_id).execute()

        # Record edit for learning
        supabase.table("reorder_approvals").insert(
            {
                "reorder_id": reorder_id,
                "suggested_quantity": suggested_qty,
                "approved_quantity": approved_qty,
                "owner_edited": True,
                "edit_percentage": round(edit_pct, 2),
            }
        ).execute()

        return {
            "success": True,
            "message": "Reorder quantity updated and approved",
            "reorder_id": reorder_id,
            "approved_quantity": approved_qty,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
