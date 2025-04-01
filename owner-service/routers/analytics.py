"""
Analytics API endpoints for Business Intelligence.
Provides trends, forecasts, anomalies, and profitability data.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/owner/analytics", tags=["analytics"])

# ---------------------------------------------------------------------------
# Lazy-load the BI agent from agent-service
# ---------------------------------------------------------------------------

def _get_bi_agent_module():
    """Import bi_agent from agent-service/agents."""
    agent_path = Path(__file__).parent.parent.parent / "agent-service" / "agents"
    if str(agent_path) not in sys.path:
        sys.path.insert(0, str(agent_path))
    import bi_agent
    return bi_agent


# ---------------------------------------------------------------------------
# GET /api/owner/analytics/trends/{store_id}
# ---------------------------------------------------------------------------

@router.get("/trends/{store_id}")
async def get_trends(store_id: str):
    """
    Return week-over-week sales trends, top/bottom products,
    seasonal patterns, and trend insights.
    """
    try:
        bi = _get_bi_agent_module()
        result = bi.calculate_trends(store_id)
        return {"success": True, "store_id": store_id, **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/owner/analytics/anomalies/{store_id}
# ---------------------------------------------------------------------------

@router.get("/anomalies/{store_id}")
async def get_anomalies(store_id: str):
    """
    Return detected anomalies in orders and inventory.
    """
    try:
        bi = _get_bi_agent_module()
        anomalies = bi.detect_anomalies(store_id)
        return {
            "success": True,
            "store_id": store_id,
            "anomalies": anomalies,
            "count": len(anomalies),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/owner/analytics/profitability/{store_id}
# ---------------------------------------------------------------------------

@router.get("/profitability/{store_id}")
async def get_profitability(store_id: str):
    """
    Return product and customer profitability analysis with recommendations.
    """
    try:
        bi = _get_bi_agent_module()
        result = bi.analyze_profitability(store_id)
        return {"success": True, "store_id": store_id, **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/owner/analytics/forecast/{store_id}
# ---------------------------------------------------------------------------

@router.get("/forecast/{store_id}")
async def get_forecast(store_id: str):
    """
    Return revenue forecast, stockout predictions, and churn forecast.
    """
    try:
        bi = _get_bi_agent_module()
        revenue = bi.forecast_revenue(store_id)
        stockouts = bi.forecast_stockouts(store_id)
        churn = bi.forecast_churn(store_id)
        return {
            "success": True,
            "store_id": store_id,
            "revenue_forecast": revenue,
            "stockout_predictions": stockouts,
            "churn_forecast": churn,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/owner/analytics/bi-metrics/{store_id}
# ---------------------------------------------------------------------------

@router.get("/bi-metrics/{store_id}")
async def get_bi_metrics(store_id: str):
    """Return BI agent performance monitoring metrics."""
    try:
        bi = _get_bi_agent_module()
        result = bi.get_bi_metrics(store_id)
        return {"success": True, **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
