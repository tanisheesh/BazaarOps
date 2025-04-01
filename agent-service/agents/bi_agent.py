"""
Autonomous Business Intelligence Agent
Handles trend detection, anomaly detection, profitability analysis,
forecasting, and comprehensive BI report generation.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta, date
from typing import Optional

import numpy as np
from supabase import create_client

logger = logging.getLogger(__name__)


def _get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
    )


# ---------------------------------------------------------------------------
# 6.1 Trend Detection
# ---------------------------------------------------------------------------

def calculate_trends(store_id: str, db_conn=None) -> dict:
    """
    6.1.1 Calculate week-over-week sales comparison.
    6.1.2 Identify top/bottom products.
    6.1.3 Detect seasonal patterns.
    6.1.4 Generate trend insights.
    """
    supabase = db_conn or _get_supabase()
    now = datetime.now(timezone.utc)

    # 6.1.1 Week-over-week sales
    this_week_start = (now - timedelta(days=7)).isoformat()
    last_week_start = (now - timedelta(days=14)).isoformat()
    last_week_end = (now - timedelta(days=7)).isoformat()

    try:
        this_week_orders = (
            supabase.table("orders")
            .select("total_amount, created_at, order_items(quantity, unit_price, product_id, products(name))")
            .eq("store_id", store_id)
            .gte("created_at", this_week_start)
            .execute()
        ).data or []

        last_week_orders = (
            supabase.table("orders")
            .select("total_amount, created_at, order_items(quantity, unit_price, product_id, products(name))")
            .eq("store_id", store_id)
            .gte("created_at", last_week_start)
            .lt("created_at", last_week_end)
            .execute()
        ).data or []
    except Exception as exc:
        logger.error("calculate_trends: orders fetch error: %s", exc)
        this_week_orders = []
        last_week_orders = []

    this_week_revenue = sum(float(o.get("total_amount", 0)) for o in this_week_orders)
    last_week_revenue = sum(float(o.get("total_amount", 0)) for o in last_week_orders)

    if last_week_revenue > 0:
        change_pct = ((this_week_revenue - last_week_revenue) / last_week_revenue) * 100
    else:
        change_pct = 100.0 if this_week_revenue > 0 else 0.0

    # 6.1.2 Top/bottom products by revenue this week
    product_revenue: dict[str, float] = {}
    for order in this_week_orders:
        for item in order.get("order_items", []):
            name = (item.get("products") or {}).get("name", "Unknown")
            rev = float(item.get("quantity", 0)) * float(item.get("unit_price", 0))
            product_revenue[name] = product_revenue.get(name, 0) + rev

    sorted_products = sorted(product_revenue.items(), key=lambda x: x[1], reverse=True)
    top_products = sorted_products[:5]
    bottom_products = sorted_products[-5:] if len(sorted_products) > 5 else []

    # 6.1.3 Seasonal pattern: compare day-of-week averages
    daily_revenue: dict[int, list[float]] = {i: [] for i in range(7)}
    for order in this_week_orders + last_week_orders:
        try:
            dt = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
            daily_revenue[dt.weekday()].append(float(order.get("total_amount", 0)))
        except Exception:
            pass

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    seasonal_pattern = {
        day_names[d]: round(sum(vals) / len(vals), 2) if vals else 0.0
        for d, vals in daily_revenue.items()
    }

    # 6.1.4 Generate trend insights
    trend = "up" if change_pct > 0 else "down" if change_pct < 0 else "flat"
    insights = []
    if abs(change_pct) >= 20:
        insights.append(f"Revenue {trend} significantly by {abs(change_pct):.1f}% vs last week")
    elif abs(change_pct) >= 5:
        insights.append(f"Revenue {trend} moderately by {abs(change_pct):.1f}% vs last week")
    else:
        insights.append("Revenue is stable week-over-week")

    if top_products:
        insights.append(f"Top product: {top_products[0][0]} (₹{top_products[0][1]:.0f})")
    if bottom_products:
        insights.append(f"Lowest product: {bottom_products[-1][0]} (₹{bottom_products[-1][1]:.0f})")

    return {
        "this_week_revenue": round(this_week_revenue, 2),
        "last_week_revenue": round(last_week_revenue, 2),
        "change_percentage": round(change_pct, 2),
        "trend": trend,
        "top_products": [{"name": n, "revenue": round(r, 2)} for n, r in top_products],
        "bottom_products": [{"name": n, "revenue": round(r, 2)} for n, r in bottom_products],
        "seasonal_pattern": seasonal_pattern,
        "insights": insights,
    }


# ---------------------------------------------------------------------------
# 6.2 Anomaly Detection
# ---------------------------------------------------------------------------

def detect_anomalies(store_id: str, db_conn=None) -> list[dict]:
    """
    6.2.1 Calculate average daily orders over 30 days.
    6.2.2 Detect order anomalies (>50% deviation).
    6.2.3 Detect inventory anomalies.
    6.2.4 Returns list of anomalies (caller should alert owner).
    """
    supabase = db_conn or _get_supabase()
    anomalies = []
    now = datetime.now(timezone.utc)

    # 6.2.1 Average daily orders (30-day window)
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    try:
        orders_30d = (
            supabase.table("orders")
            .select("id, total_amount, created_at")
            .eq("store_id", store_id)
            .gte("created_at", thirty_days_ago)
            .execute()
        ).data or []

        today_orders = (
            supabase.table("orders")
            .select("id, total_amount")
            .eq("store_id", store_id)
            .gte("created_at", today_start)
            .execute()
        ).data or []
    except Exception as exc:
        logger.error("detect_anomalies: orders fetch error: %s", exc)
        orders_30d = []
        today_orders = []

    avg_daily_orders = len(orders_30d) / 30.0
    today_count = len(today_orders)

    # 6.2.2 Order anomaly: >50% deviation
    if avg_daily_orders > 0:
        deviation = abs(today_count - avg_daily_orders) / avg_daily_orders
        if deviation > 0.5:
            direction = "low" if today_count < avg_daily_orders else "high"
            anomalies.append({
                "type": f"order_count_{direction}",
                "severity": "high",
                "message": (
                    f"Orders {direction} today: {today_count} vs avg {avg_daily_orders:.1f} "
                    f"({deviation * 100:.0f}% deviation)"
                ),
                "today_count": today_count,
                "avg_daily": round(avg_daily_orders, 1),
                "deviation_pct": round(deviation * 100, 1),
            })

    # Revenue anomaly
    avg_daily_revenue = sum(float(o.get("total_amount", 0)) for o in orders_30d) / 30.0
    today_revenue = sum(float(o.get("total_amount", 0)) for o in today_orders)
    if avg_daily_revenue > 0:
        rev_deviation = abs(today_revenue - avg_daily_revenue) / avg_daily_revenue
        if rev_deviation > 0.5:
            direction = "low" if today_revenue < avg_daily_revenue else "high"
            anomalies.append({
                "type": f"revenue_{direction}",
                "severity": "high",
                "message": (
                    f"Revenue {direction} today: ₹{today_revenue:.0f} vs avg ₹{avg_daily_revenue:.0f} "
                    f"({rev_deviation * 100:.0f}% deviation)"
                ),
                "today_revenue": round(today_revenue, 2),
                "avg_daily_revenue": round(avg_daily_revenue, 2),
                "deviation_pct": round(rev_deviation * 100, 1),
            })

    # 6.2.3 Inventory anomalies: items below reorder threshold
    try:
        inventory = (
            supabase.table("inventory")
            .select("id, quantity, reorder_threshold, products(name)")
            .eq("store_id", store_id)
            .execute()
        ).data or []

        for item in inventory:
            qty = float(item.get("quantity", 0))
            threshold = float(item.get("reorder_threshold", 0))
            if threshold > 0 and qty <= threshold:
                product_name = (item.get("products") or {}).get("name", "Unknown")
                anomalies.append({
                    "type": "inventory_low",
                    "severity": "critical" if qty == 0 else "medium",
                    "message": f"Low stock: {product_name} ({qty} remaining, threshold {threshold})",
                    "product_name": product_name,
                    "quantity": qty,
                    "threshold": threshold,
                })
    except Exception as exc:
        logger.error("detect_anomalies: inventory fetch error: %s", exc)

    return anomalies


# ---------------------------------------------------------------------------
# 6.3 Profitability Analysis
# ---------------------------------------------------------------------------

def analyze_profitability(store_id: str, db_conn=None) -> dict:
    """
    6.3.1 Calculate product-level profitability.
    6.3.2 Identify low-margin products (<10%).
    6.3.3 Calculate customer-level profitability.
    6.3.4 Recommend actions.
    """
    supabase = db_conn or _get_supabase()
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    # 6.3.1 Product-level profitability
    product_profitability = []
    try:
        order_items = (
            supabase.table("order_items")
            .select("quantity, unit_price, product_id, products(name, cost_price)")
            .execute()
        ).data or []

        # Aggregate by product
        product_data: dict[str, dict] = {}
        for item in order_items:
            pid = item.get("product_id")
            if not pid:
                continue
            product = item.get("products") or {}
            name = product.get("name", "Unknown")
            cost = float(product.get("cost_price") or 0)
            qty = float(item.get("quantity", 0))
            price = float(item.get("unit_price", 0))

            if pid not in product_data:
                product_data[pid] = {"name": name, "revenue": 0.0, "cost": 0.0, "units_sold": 0.0}
            product_data[pid]["revenue"] += qty * price
            product_data[pid]["cost"] += qty * cost
            product_data[pid]["units_sold"] += qty

        for pid, data in product_data.items():
            revenue = data["revenue"]
            cost = data["cost"]
            profit = revenue - cost
            margin_pct = (profit / revenue * 100) if revenue > 0 else 0.0
            product_profitability.append({
                "product_id": pid,
                "name": data["name"],
                "revenue": round(revenue, 2),
                "cost": round(cost, 2),
                "profit": round(profit, 2),
                "margin_pct": round(margin_pct, 1),
                "units_sold": round(data["units_sold"], 2),
            })
    except Exception as exc:
        logger.error("analyze_profitability: product fetch error: %s", exc)

    # 6.3.2 Low-margin products (<10%)
    low_margin = [p for p in product_profitability if p["margin_pct"] < 10]

    # 6.3.3 Customer-level profitability
    customer_profitability = []
    try:
        orders = (
            supabase.table("orders")
            .select("customer_id, total_amount, profit_amount, customers(name)")
            .eq("store_id", store_id)
            .gte("created_at", thirty_days_ago)
            .execute()
        ).data or []

        cust_data: dict[str, dict] = {}
        for order in orders:
            cid = order.get("customer_id")
            if not cid:
                continue
            customer = order.get("customers") or {}
            name = customer.get("name", "Unknown")
            revenue = float(order.get("total_amount", 0))
            profit = float(order.get("profit_amount") or 0)

            if cid not in cust_data:
                cust_data[cid] = {"name": name, "revenue": 0.0, "profit": 0.0, "order_count": 0}
            cust_data[cid]["revenue"] += revenue
            cust_data[cid]["profit"] += profit
            cust_data[cid]["order_count"] += 1

        for cid, data in cust_data.items():
            margin = (data["profit"] / data["revenue"] * 100) if data["revenue"] > 0 else 0.0
            customer_profitability.append({
                "customer_id": cid,
                "name": data["name"],
                "revenue": round(data["revenue"], 2),
                "profit": round(data["profit"], 2),
                "margin_pct": round(margin, 1),
                "order_count": data["order_count"],
            })
    except Exception as exc:
        logger.error("analyze_profitability: customer fetch error: %s", exc)

    # Sort by profit descending
    product_profitability.sort(key=lambda x: x["profit"], reverse=True)
    customer_profitability.sort(key=lambda x: x["profit"], reverse=True)

    # 6.3.4 Recommend actions
    recommendations = []
    for p in low_margin:
        recommendations.append(
            f"Consider raising price or reducing cost for '{p['name']}' (margin: {p['margin_pct']}%)"
        )
    if not low_margin:
        recommendations.append("All products have healthy margins (>10%)")

    return {
        "product_profitability": product_profitability,
        "low_margin_products": low_margin,
        "customer_profitability": customer_profitability[:10],
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 6.4 Forecasting
# ---------------------------------------------------------------------------

def forecast_revenue(store_id: str, db_conn=None) -> dict:
    """
    6.4.1 Revenue forecasting using linear regression on last 30 days.
    6.4.4 Calculate confidence intervals.
    """
    supabase = db_conn or _get_supabase()
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    try:
        orders = (
            supabase.table("orders")
            .select("total_amount, created_at")
            .eq("store_id", store_id)
            .gte("created_at", thirty_days_ago.isoformat())
            .execute()
        ).data or []
    except Exception as exc:
        logger.error("forecast_revenue: orders fetch error: %s", exc)
        orders = []

    # Build daily revenue dict
    daily_revenue: dict[date, float] = {}
    for i in range(30):
        d = (thirty_days_ago + timedelta(days=i)).date()
        daily_revenue[d] = 0.0

    for order in orders:
        try:
            dt = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
            daily_revenue[dt.date()] = daily_revenue.get(dt.date(), 0.0) + float(order.get("total_amount", 0))
        except Exception:
            pass

    days_sorted = sorted(daily_revenue.keys())
    revenues = [daily_revenue[d] for d in days_sorted]

    if len(revenues) < 2:
        return {
            "next_7_days_total": 0.0,
            "daily_forecast": [],
            "confidence": "low",
            "confidence_interval": {"lower": 0.0, "upper": 0.0},
            "r_squared": 0.0,
        }

    x = np.array(range(len(revenues)), dtype=float)
    y = np.array(revenues, dtype=float)

    # 6.4.1 Linear regression
    slope, intercept = np.polyfit(x, y, 1)

    # R² for confidence
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # 6.4.4 Confidence intervals (±1 std dev of residuals)
    residuals = y - y_pred
    std_residual = float(np.std(residuals))

    # Forecast next 7 days
    forecast = []
    for i in range(7):
        idx = len(revenues) + i
        predicted = max(0.0, float(slope * idx + intercept))
        forecast.append({
            "day": i + 1,
            "date": (now + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
            "predicted_revenue": round(predicted, 2),
            "lower_bound": round(max(0.0, predicted - std_residual), 2),
            "upper_bound": round(predicted + std_residual, 2),
        })

    next_7_total = sum(f["predicted_revenue"] for f in forecast)

    if r_squared >= 0.7:
        confidence = "high"
    elif r_squared >= 0.4:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "next_7_days_total": round(next_7_total, 2),
        "daily_forecast": forecast,
        "confidence": confidence,
        "confidence_interval": {
            "lower": round(max(0.0, next_7_total - std_residual * 7), 2),
            "upper": round(next_7_total + std_residual * 7, 2),
        },
        "r_squared": round(r_squared, 3),
        "slope": round(float(slope), 4),
    }


def forecast_stockouts(store_id: str, db_conn=None) -> list[dict]:
    """
    6.4.2 Predict stockout dates for each product based on sales velocity.
    """
    supabase = db_conn or _get_supabase()
    now = datetime.now(timezone.utc)
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    predictions = []

    try:
        inventory = (
            supabase.table("inventory")
            .select("id, quantity, product_id, products(name)")
            .eq("store_id", store_id)
            .execute()
        ).data or []

        for item in inventory:
            pid = item.get("product_id")
            qty = float(item.get("quantity", 0))
            product_name = (item.get("products") or {}).get("name", "Unknown")

            # Get 30-day sales for this product
            try:
                sold_items = (
                    supabase.table("order_items")
                    .select("quantity, orders!inner(store_id, created_at)")
                    .eq("product_id", pid)
                    .gte("orders.created_at", thirty_days_ago)
                    .execute()
                ).data or []
            except Exception:
                sold_items = []

            total_sold = sum(float(i.get("quantity", 0)) for i in sold_items)
            daily_velocity = total_sold / 30.0

            if daily_velocity > 0:
                days_until_stockout = qty / daily_velocity
            else:
                days_until_stockout = 999

            stockout_date = (now + timedelta(days=days_until_stockout)).strftime("%Y-%m-%d")

            predictions.append({
                "product_id": pid,
                "product_name": product_name,
                "current_stock": qty,
                "daily_velocity": round(daily_velocity, 3),
                "days_until_stockout": round(days_until_stockout, 1),
                "predicted_stockout_date": stockout_date,
                "risk": "critical" if days_until_stockout <= 3 else "high" if days_until_stockout <= 7 else "medium" if days_until_stockout <= 14 else "low",
            })
    except Exception as exc:
        logger.error("forecast_stockouts: error: %s", exc)

    predictions.sort(key=lambda x: x["days_until_stockout"])
    return predictions


def forecast_churn(store_id: str, db_conn=None) -> dict:
    """
    6.4.3 Churn forecasting: predict number of customers likely to churn next 30 days.
    """
    supabase = db_conn or _get_supabase()
    try:
        customers = (
            supabase.table("customers")
            .select("id, churn_risk_level, avg_order_interval, last_order_date")
            .eq("store_id", store_id)
            .execute()
        ).data or []
    except Exception as exc:
        logger.error("forecast_churn: error: %s", exc)
        customers = []

    high_risk = [c for c in customers if c.get("churn_risk_level") == "high"]
    medium_risk = [c for c in customers if c.get("churn_risk_level") == "medium"]

    # Estimate churn: 80% of high-risk, 30% of medium-risk will churn
    predicted_churn = int(len(high_risk) * 0.8 + len(medium_risk) * 0.3)
    total = len(customers)
    churn_rate_pct = (predicted_churn / total * 100) if total > 0 else 0.0

    return {
        "total_customers": total,
        "high_risk_count": len(high_risk),
        "medium_risk_count": len(medium_risk),
        "predicted_churn_30d": predicted_churn,
        "predicted_churn_rate_pct": round(churn_rate_pct, 1),
    }


# ---------------------------------------------------------------------------
# 6.5 Comprehensive BI Report
# ---------------------------------------------------------------------------

async def generate_bi_report(store_id: str, db_conn=None) -> bool:
    """
    6.5.1 Combine all insights.
    6.5.2 Generate narrative with Claude AI.
    6.5.3 Send via Telegram to owner.
    """
    import json
    import anthropic
    from telegram import Bot

    supabase = db_conn or _get_supabase()

    try:
        store_result = supabase.table("stores").select("*").eq("id", store_id).single().execute()
        store = store_result.data or {}
        chat_id = store.get("telegram_chat_id")
        store_name = store.get("name", "Your Store")
    except Exception as exc:
        logger.error("generate_bi_report: store fetch error: %s", exc)
        return False

    if not chat_id:
        logger.warning("generate_bi_report: no telegram_chat_id for store %s", store_id)
        return False

    # 6.5.1 Gather all insights
    trends = calculate_trends(store_id, db_conn=supabase)
    anomalies = detect_anomalies(store_id, db_conn=supabase)
    profitability = analyze_profitability(store_id, db_conn=supabase)
    revenue_forecast = forecast_revenue(store_id, db_conn=supabase)
    stockout_forecast = forecast_stockouts(store_id, db_conn=supabase)
    churn_forecast = forecast_churn(store_id, db_conn=supabase)

    report_data = {
        "store_name": store_name,
        "date": datetime.now().strftime("%d %B %Y"),
        "trends": trends,
        "anomalies": anomalies,
        "profitability_summary": {
            "low_margin_count": len(profitability["low_margin_products"]),
            "top_products": profitability["product_profitability"][:3],
            "recommendations": profitability["recommendations"],
        },
        "revenue_forecast": {
            "next_7_days": revenue_forecast["next_7_days_total"],
            "confidence": revenue_forecast["confidence"],
        },
        "stockout_risks": [s for s in stockout_forecast if s["risk"] in ("critical", "high")][:5],
        "churn_forecast": churn_forecast,
    }

    # 6.5.2 Generate with Claude
    try:
        ai_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        prompt = f"""You are a business intelligence analyst for a retail store. 
Analyze the following data and provide a concise, actionable daily BI report.

Data:
{json.dumps(report_data, indent=2)}

Provide:
1. Executive summary (2-3 sentences)
2. Key wins and concerns
3. Top 3 actionable recommendations
4. Revenue outlook

Format as a clear Telegram message with emojis. Keep it under 500 words."""

        message = ai_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        ai_narrative = message.content[0].text
    except Exception as exc:
        logger.error("generate_bi_report: Claude API error: %s", exc)
        ai_narrative = "AI narrative unavailable."

    # Build final report
    anomaly_text = ""
    if anomalies:
        anomaly_text = "\n⚠️ *Anomalies Detected:*\n" + "\n".join(f"• {a['message']}" for a in anomalies[:3])

    final_report = f"""📊 *Daily BI Report - {datetime.now().strftime('%d %B %Y')}*
*{store_name}*

📈 *This Week vs Last Week:*
• Revenue: ₹{trends['this_week_revenue']:,.0f} ({'+' if trends['change_percentage'] >= 0 else ''}{trends['change_percentage']:.1f}%)
• Trend: {trends['trend'].upper()}
{anomaly_text}

🔮 *7-Day Revenue Forecast:* ₹{revenue_forecast['next_7_days_total']:,.0f} ({revenue_forecast['confidence']} confidence)

👥 *Churn Risk:* {churn_forecast['predicted_churn_30d']} customers at risk

{ai_narrative}
"""

    # 6.5.3 Send via Telegram
    try:
        bot_token = os.getenv("OWNER_BOT_TOKEN")
        if not bot_token:
            logger.error("generate_bi_report: OWNER_BOT_TOKEN not set")
            return False
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=final_report, parse_mode="Markdown")
        logger.info("BI report sent to store %s", store_id)
        return True
    except Exception as exc:
        logger.error("generate_bi_report: Telegram send error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# 6.9 BI Agent Performance Monitoring
# ---------------------------------------------------------------------------

def get_bi_metrics(store_id: str, db_conn=None) -> dict:
    """
    6.9 Return BI agent performance metrics.
    Tracks forecast accuracy and report delivery.
    """
    supabase = db_conn or _get_supabase()
    try:
        # Check recent BI reports sent (stored in event log)
        result = (
            supabase.table("event_log")
            .select("id, created_at, status")
            .eq("event_type", "bi_report.sent")
            .eq("store_id", store_id)
            .order("created_at", desc=True)
            .limit(30)
            .execute()
        )
        reports = result.data or []
        successful = sum(1 for r in reports if r.get("status") == "success")
        total = len(reports)
        delivery_rate = (successful / total * 100) if total > 0 else 0.0

        return {
            "store_id": store_id,
            "reports_sent_30d": total,
            "successful_deliveries": successful,
            "delivery_rate_pct": round(delivery_rate, 1),
            "last_report_at": reports[0]["created_at"] if reports else None,
        }
    except Exception as exc:
        logger.error("get_bi_metrics error: %s", exc)
        return {"store_id": store_id, "error": str(exc)}
