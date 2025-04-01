"""
Coordinator Agent
Orchestrates multi-agent collaboration, resolves conflicts, and makes
goal-oriented decisions across the BazaarOps agent ecosystem.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from agents.message_bus.protocol import AgentMessage, AgentName, MessageType
from agents.message_bus.publisher import AgentMessagePublisher

logger = logging.getLogger(__name__)


def _get_supabase():
    from supabase import create_client
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
    )


# ---------------------------------------------------------------------------
# 7.2.1 Conflict Resolution
# ---------------------------------------------------------------------------

def resolve_conflict(messages: list[AgentMessage]) -> AgentMessage:
    """
    Resolve conflicting agent recommendations.
    Picks the message with the highest priority; ties broken by timestamp (latest).
    """
    if not messages:
        raise ValueError("Cannot resolve conflict with empty message list")
    return max(messages, key=lambda m: (m.priority, m.timestamp))


# ---------------------------------------------------------------------------
# 7.2.2 Goal-Oriented Behavior
# ---------------------------------------------------------------------------

VALID_GOALS = {"maximize_profit", "increase_customers", "reduce_risk", "balanced"}
DEFAULT_GOAL = "balanced"


def get_owner_goal(store_id: str, redis_client=None) -> str:
    """Read the owner's current goal from Redis. Defaults to 'balanced'."""
    try:
        if redis_client is None:
            from redis_client import get_sync_client
            redis_client = get_sync_client()
        value = redis_client.get(f"store_goal:{store_id}")
        if value and value in VALID_GOALS:
            return value
    except Exception as exc:
        logger.warning("get_owner_goal error: %s", exc)
    return DEFAULT_GOAL


def align_with_goal(goal: str, options: list) -> dict:
    """
    Pick the best option from a list based on the owner's goal.
    Each option should be a dict with at least a 'type' key.
    """
    if not options:
        return {}

    goal_priority_map = {
        "maximize_profit": ["reorder", "credit_block", "fraud_block"],
        "increase_customers": ["re_engagement", "reorder", "credit_approve"],
        "reduce_risk": ["credit_block", "fraud_block", "reorder"],
        "balanced": [],
    }

    preferred_types = goal_priority_map.get(goal, [])

    for preferred in preferred_types:
        for option in options:
            if option.get("type") == preferred:
                return option

    # Default: return first option
    return options[0]


# ---------------------------------------------------------------------------
# 7.2.3 Decision Logging
# ---------------------------------------------------------------------------

def log_decision(decision: dict, supabase=None) -> Optional[str]:
    """Insert a decision record into the agent_decisions table."""
    try:
        db = supabase or _get_supabase()
        record = {
            "from_agents": decision.get("from_agents", []),
            "decision_type": decision.get("decision_type", "unknown"),
            "input_data": decision.get("input_data", {}),
            "output_decision": decision.get("output_decision", {}),
            "goal_used": decision.get("goal_used", DEFAULT_GOAL),
            "store_id": decision.get("store_id"),
            "outcome": decision.get("outcome"),
        }
        result = db.table("agent_decisions").insert(record).execute()
        if result.data:
            return result.data[0]["id"]
    except Exception as exc:
        logger.error("log_decision error: %s", exc)
    return None


# ---------------------------------------------------------------------------
# 7.5.1 Track Collaboration Outcomes
# ---------------------------------------------------------------------------

def track_outcome(
    decision_id: str,
    outcome: str,
    metrics: dict,
    supabase=None,
) -> bool:
    """Update an agent_decisions record with outcome and metrics."""
    valid_outcomes = {"success", "failure", "partial", "overridden_by_owner"}
    if outcome not in valid_outcomes:
        logger.warning("Invalid outcome '%s', defaulting to 'partial'", outcome)
        outcome = "partial"
    try:
        db = supabase or _get_supabase()
        db.table("agent_decisions").update(
            {
                "outcome": outcome,
                "outcome_metrics": metrics,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", decision_id).execute()
        return True
    except Exception as exc:
        logger.error("track_outcome error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# 7.5.2 Strategy Adjustment
# ---------------------------------------------------------------------------

def get_strategy_adjustment(
    agent_name: str,
    store_id: str,
    supabase=None,
    redis_client=None,
) -> dict:
    """
    Query last 30 days of decisions for an agent, calculate success rate,
    and return an adjustment dict. Stores result in Redis.
    """
    try:
        db = supabase or _get_supabase()
        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        result = (
            db.table("agent_decisions")
            .select("outcome")
            .eq("store_id", store_id)
            .gte("created_at", since)
            .execute()
        )
        decisions = result.data or []

        # Filter decisions involving this agent
        relevant = [
            d for d in decisions
            if d.get("outcome") is not None
        ]

        total = len(relevant)
        if total == 0:
            adjustment = {
                "agent_name": agent_name,
                "store_id": store_id,
                "success_rate": None,
                "confidence_threshold": 0.7,
                "autonomy_level": "normal",
                "sample_size": 0,
            }
        else:
            successes = sum(1 for d in relevant if d.get("outcome") == "success")
            success_rate = successes / total

            if success_rate < 0.5:
                confidence_threshold = 0.8  # Require higher confidence
                autonomy_level = "restricted"
            elif success_rate > 0.8:
                confidence_threshold = 0.6  # Allow lower confidence
                autonomy_level = "high"
            else:
                confidence_threshold = 0.7
                autonomy_level = "normal"

            adjustment = {
                "agent_name": agent_name,
                "store_id": store_id,
                "success_rate": round(success_rate, 3),
                "confidence_threshold": confidence_threshold,
                "autonomy_level": autonomy_level,
                "sample_size": total,
            }

        # Cache in Redis
        try:
            import json
            rc = redis_client
            if rc is None:
                from redis_client import get_sync_client
                rc = get_sync_client()
            rc.setex(
                f"strategy:{agent_name}:{store_id}",
                86400,  # 24h TTL
                json.dumps(adjustment),
            )
        except Exception as exc:
            logger.warning("Failed to cache strategy adjustment: %s", exc)

        return adjustment

    except Exception as exc:
        logger.error("get_strategy_adjustment error: %s", exc)
        return {
            "agent_name": agent_name,
            "store_id": store_id,
            "success_rate": None,
            "confidence_threshold": 0.7,
            "autonomy_level": "normal",
            "sample_size": 0,
        }


# ---------------------------------------------------------------------------
# 7.9 Improvement Metrics
# ---------------------------------------------------------------------------

def calculate_improvement_metrics(
    store_id: str,
    days: int = 30,
    supabase=None,
) -> dict:
    """
    Query agent_decisions for the period and return summary metrics.
    Provides a baseline for measuring improvement over time.
    """
    try:
        db = supabase or _get_supabase()
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        result = (
            db.table("agent_decisions")
            .select("decision_type, outcome, from_agents, output_decision")
            .eq("store_id", store_id)
            .gte("created_at", since)
            .execute()
        )
        decisions = result.data or []

        total = len(decisions)
        if total == 0:
            return {
                "store_id": store_id,
                "period_days": days,
                "total_decisions": 0,
                "success_rate": None,
                "decisions_by_type": {},
                "avg_priority": None,
                "most_active_agents": [],
            }

        successes = sum(1 for d in decisions if d.get("outcome") == "success")
        success_rate = round(successes / total, 3) if total > 0 else None

        # Count by type
        decisions_by_type: dict[str, int] = {}
        for d in decisions:
            dt = d.get("decision_type", "unknown")
            decisions_by_type[dt] = decisions_by_type.get(dt, 0) + 1

        # Count agent activity
        agent_counts: dict[str, int] = {}
        for d in decisions:
            for agent in (d.get("from_agents") or []):
                agent_counts[agent] = agent_counts.get(agent, 0) + 1

        most_active = sorted(agent_counts.items(), key=lambda x: x[1], reverse=True)
        most_active_agents = [a for a, _ in most_active[:5]]

        # Average priority from output_decision if available
        priorities = []
        for d in decisions:
            od = d.get("output_decision") or {}
            if isinstance(od, dict) and "priority" in od:
                try:
                    priorities.append(float(od["priority"]))
                except (TypeError, ValueError):
                    pass
        avg_priority = round(sum(priorities) / len(priorities), 2) if priorities else None

        return {
            "store_id": store_id,
            "period_days": days,
            "total_decisions": total,
            "success_rate": success_rate,
            "decisions_by_type": decisions_by_type,
            "avg_priority": avg_priority,
            "most_active_agents": most_active_agents,
        }

    except Exception as exc:
        logger.error("calculate_improvement_metrics error: %s", exc)
        return {"store_id": store_id, "error": str(exc)}


# ---------------------------------------------------------------------------
# CoordinatorAgent class
# ---------------------------------------------------------------------------

class CoordinatorAgent:
    """
    Coordinates multi-agent collaboration, resolves conflicts, and routes
    messages based on the owner's goal.
    """

    def __init__(self, publisher: AgentMessagePublisher = None, supabase=None):
        self.publisher = publisher or AgentMessagePublisher()
        self.supabase = supabase

    async def process_message(self, message: AgentMessage) -> None:
        """Route and coordinate based on incoming message type."""
        try:
            mt = message.message_type
            if mt == MessageType.INVENTORY_LOW:
                logger.info("Coordinator: received INVENTORY_LOW from %s", message.from_agent)
                # Will be combined with demand forecast in handle_low_stock_scenario
            elif mt == MessageType.DEMAND_FORECAST:
                logger.info("Coordinator: received DEMAND_FORECAST from %s", message.from_agent)
            elif mt == MessageType.CREDIT_RISK_HIGH:
                logger.info("Coordinator: received CREDIT_RISK_HIGH from %s", message.from_agent)
            elif mt == MessageType.FRAUD_DETECTED:
                logger.info("Coordinator: received FRAUD_DETECTED from %s", message.from_agent)
            elif mt == MessageType.CUSTOMER_CHURN_RISK:
                logger.info("Coordinator: received CUSTOMER_CHURN_RISK from %s", message.from_agent)
            else:
                logger.debug("Coordinator: unhandled message type %s", mt)
        except Exception as exc:
            logger.error("CoordinatorAgent.process_message error: %s", exc)

    # ------------------------------------------------------------------
    # 7.4.1 Low Stock Scenario
    # ------------------------------------------------------------------

    async def handle_low_stock_scenario(
        self,
        inventory_msg: AgentMessage,
        demand_msg: AgentMessage,
        store_id: str = "",
    ) -> AgentMessage:
        """
        Combine inventory low + demand forecast to decide reorder urgency.
        High demand + low stock → urgent reorder (priority 9)
        Low demand + low stock → normal reorder (priority 5)
        """
        inv_data = inventory_msg.data or {}
        demand_data = demand_msg.data or {}

        product_id = inv_data.get("product_id") or demand_data.get("product_id")
        current_stock = float(inv_data.get("current_stock", 0))
        predicted_demand = float(demand_data.get("predicted_demand", 0))
        confidence = float(demand_data.get("confidence", 0))

        # Determine urgency
        is_high_demand = predicted_demand > current_stock * 2
        priority = 9 if is_high_demand else 5
        urgency = "urgent" if is_high_demand else "normal"

        suggested_quantity = max(predicted_demand - current_stock, current_stock) * 1.2

        output_decision = {
            "product_id": product_id,
            "suggested_quantity": round(suggested_quantity, 2),
            "urgency": urgency,
            "priority": priority,
            "reason": "high_demand_low_stock" if is_high_demand else "low_stock_normal_demand",
        }

        # Log decision
        goal = get_owner_goal(store_id) if store_id else DEFAULT_GOAL
        log_decision(
            {
                "from_agents": [inventory_msg.from_agent, demand_msg.from_agent],
                "decision_type": "low_stock_reorder",
                "input_data": {"inventory": inv_data, "demand": demand_data},
                "output_decision": output_decision,
                "goal_used": goal,
                "store_id": store_id or None,
            },
            supabase=self.supabase,
        )

        # Publish REORDER_NEEDED
        reorder_msg = AgentMessage(
            from_agent=AgentName.COORDINATOR.value,
            to_agent=AgentName.REORDER.value,
            message_type=MessageType.REORDER_NEEDED,
            data=output_decision,
            priority=priority,
            correlation_id=inventory_msg.id,
        )
        await self.publisher.publish(reorder_msg)
        return reorder_msg

    # ------------------------------------------------------------------
    # 7.4.2 Customer Churn Scenario
    # ------------------------------------------------------------------

    async def handle_churn_scenario(
        self,
        churn_msg: AgentMessage,
        credit_msg: AgentMessage,
        store_id: str = "",
    ) -> AgentMessage:
        """
        Churn risk + credit assessment → decide action.
        Good credit → re-engagement offer
        Bad credit → notify owner only
        """
        churn_data = churn_msg.data or {}
        credit_data = credit_msg.data or {}

        customer_id = churn_data.get("customer_id") or credit_data.get("customer_id")
        risk_score = float(credit_data.get("risk_score", 50))
        has_good_credit = risk_score < 50  # Lower risk score = better credit

        if has_good_credit:
            action = "send_re_engagement_offer"
            priority = 7
        else:
            action = "notify_owner_only"
            priority = 4

        output_decision = {
            "customer_id": customer_id,
            "action": action,
            "priority": priority,
            "credit_risk_score": risk_score,
        }

        goal = get_owner_goal(store_id) if store_id else DEFAULT_GOAL
        log_decision(
            {
                "from_agents": [churn_msg.from_agent, credit_msg.from_agent],
                "decision_type": "churn_intervention",
                "input_data": {"churn": churn_data, "credit": credit_data},
                "output_decision": output_decision,
                "goal_used": goal,
                "store_id": store_id or None,
            },
            supabase=self.supabase,
        )

        response_msg = AgentMessage(
            from_agent=AgentName.COORDINATOR.value,
            to_agent=AgentName.NOTIFICATION.value,
            message_type=MessageType.COLLABORATION_RESPONSE,
            data=output_decision,
            priority=priority,
            correlation_id=churn_msg.id,
        )
        await self.publisher.publish(response_msg)
        return response_msg

    # ------------------------------------------------------------------
    # 7.4.3 Credit Risk Scenario
    # ------------------------------------------------------------------

    async def handle_credit_risk_scenario(
        self,
        credit_msg: AgentMessage,
        order_msg: AgentMessage,
        store_id: str = "",
    ) -> AgentMessage:
        """
        High credit risk + large order → block order, notify owner.
        Medium credit risk → require confirmation.
        """
        credit_data = credit_msg.data or {}
        order_data = order_msg.data or {}

        customer_id = credit_data.get("customer_id") or order_data.get("customer_id")
        risk_score = float(credit_data.get("risk_score", 0))
        order_amount = float(order_data.get("order_amount", 0))

        # Thresholds
        is_high_risk = risk_score >= 70
        is_large_order = order_amount >= 2000

        if is_high_risk and is_large_order:
            action = "block_order_notify_owner"
            priority = 10
        elif is_high_risk or risk_score >= 50:
            action = "require_confirmation"
            priority = 7
        else:
            action = "approve"
            priority = 3

        output_decision = {
            "customer_id": customer_id,
            "action": action,
            "priority": priority,
            "risk_score": risk_score,
            "order_amount": order_amount,
        }

        goal = get_owner_goal(store_id) if store_id else DEFAULT_GOAL
        decision_id = log_decision(
            {
                "from_agents": [credit_msg.from_agent, order_msg.from_agent],
                "decision_type": "credit_risk_order",
                "input_data": {"credit": credit_data, "order": order_data},
                "output_decision": output_decision,
                "goal_used": goal,
                "store_id": store_id or None,
            },
            supabase=self.supabase,
        )

        response_msg = AgentMessage(
            from_agent=AgentName.COORDINATOR.value,
            to_agent=AgentName.NOTIFICATION.value,
            message_type=MessageType.COLLABORATION_RESPONSE,
            data={**output_decision, "decision_id": decision_id},
            priority=priority,
            correlation_id=credit_msg.id,
        )
        await self.publisher.publish(response_msg)
        return response_msg
