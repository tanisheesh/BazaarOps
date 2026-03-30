"""
Tests for the multi-agent collaboration system (Task 7).
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.message_bus.protocol import AgentMessage, AgentName, MessageType
from agents.message_bus.queue import PriorityMessageQueue
from agents.coordinator_agent import (
    CoordinatorAgent,
    get_strategy_adjustment,
    resolve_conflict,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_message(
    from_agent: str = AgentName.INVENTORY.value,
    to_agent: str = "broadcast",
    message_type: str = MessageType.INVENTORY_LOW,
    data: dict = None,
    priority: int = 5,
) -> AgentMessage:
    return AgentMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=message_type,
        data=data or {},
        priority=priority,
    )


def run(coro):
    """Run a coroutine synchronously using the event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# 7.1.1 AgentMessage serialization / deserialization
# ---------------------------------------------------------------------------

class TestAgentMessageProtocol:
    def test_to_dict_contains_required_fields(self):
        msg = make_message(data={"product_id": "p1", "current_stock": 5})
        d = msg.to_dict()
        assert "id" in d
        assert d["from_agent"] == AgentName.INVENTORY.value
        assert d["to_agent"] == "broadcast"
        assert d["message_type"] == MessageType.INVENTORY_LOW
        assert d["data"]["product_id"] == "p1"
        assert d["priority"] == 5
        assert "timestamp" in d

    def test_from_dict_roundtrip(self):
        original = make_message(data={"product_id": "p2"}, priority=8)
        d = original.to_dict()
        restored = AgentMessage.from_dict(d)
        assert restored.id == original.id
        assert restored.from_agent == original.from_agent
        assert restored.to_agent == original.to_agent
        assert restored.message_type == original.message_type
        assert restored.data == original.data
        assert restored.priority == original.priority

    def test_correlation_id_preserved(self):
        corr_id = str(uuid.uuid4())
        msg = AgentMessage(
            from_agent="inventory",
            to_agent="coordinator",
            message_type=MessageType.INVENTORY_LOW,
            data={},
            correlation_id=corr_id,
        )
        restored = AgentMessage.from_dict(msg.to_dict())
        assert restored.correlation_id == corr_id

    def test_json_serializable(self):
        msg = make_message(data={"key": "value"})
        payload = json.dumps(msg.to_dict())
        data = json.loads(payload)
        assert data["from_agent"] == AgentName.INVENTORY.value


# ---------------------------------------------------------------------------
# 7.1.4 PriorityMessageQueue push/pop ordering
# ---------------------------------------------------------------------------

class TestPriorityMessageQueue:
    def _make_redis_mock(self, stored: list):
        mock = AsyncMock()

        async def zadd(key, mapping):
            for payload, score in mapping.items():
                stored.append((payload, score))

        async def zpopmax(key, count=1):
            if not stored:
                return []
            stored.sort(key=lambda x: x[1], reverse=True)
            item = stored.pop(0)
            return [item]

        async def zrange(key, start, end, desc=False, withscores=False):
            sorted_items = sorted(stored, key=lambda x: x[1], reverse=desc)
            return [item[0] for item in sorted_items[start : end + 1]]

        mock.zadd = zadd
        mock.zpopmax = zpopmax
        mock.zrange = zrange
        return mock

    def test_pop_returns_highest_priority(self):
        stored = []
        queue = PriorityMessageQueue(redis_client=self._make_redis_mock(stored))

        run(queue.push(make_message(priority=2)))
        run(queue.push(make_message(priority=9)))
        run(queue.push(make_message(priority=5)))

        result = run(queue.pop_highest())
        assert result is not None
        assert result.priority == 9

    def test_pop_empty_returns_none(self):
        stored = []
        queue = PriorityMessageQueue(redis_client=self._make_redis_mock(stored))
        assert run(queue.pop_highest()) is None

    def test_peek_does_not_remove(self):
        stored = []
        queue = PriorityMessageQueue(redis_client=self._make_redis_mock(stored))
        run(queue.push(make_message(priority=7)))
        peeked = run(queue.peek(n=5))
        assert len(peeked) == 1
        assert len(stored) == 1  # item still in queue


# ---------------------------------------------------------------------------
# 7.2.1 resolve_conflict
# ---------------------------------------------------------------------------

class TestResolveConflict:
    def test_picks_highest_priority(self):
        msgs = [make_message(priority=3), make_message(priority=9), make_message(priority=5)]
        assert resolve_conflict(msgs).priority == 9

    def test_single_message_returns_it(self):
        msg = make_message(priority=7)
        assert resolve_conflict([msg]) is msg

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            resolve_conflict([])

    def test_tie_broken_by_latest_timestamp(self):
        earlier = make_message(priority=8)
        later = make_message(priority=8)
        later.timestamp = datetime(2099, 1, 2, tzinfo=timezone.utc)
        earlier.timestamp = datetime(2099, 1, 1, tzinfo=timezone.utc)
        assert resolve_conflict([earlier, later]) is later


# ---------------------------------------------------------------------------
# 7.4.1 handle_low_stock_scenario
# ---------------------------------------------------------------------------

class TestLowStockScenario:
    def _make_coordinator(self):
        publisher_mock = AsyncMock()
        publisher_mock.publish = AsyncMock()
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": str(uuid.uuid4())}
        ]
        return CoordinatorAgent(publisher=publisher_mock, supabase=supabase_mock), publisher_mock

    def test_high_demand_produces_urgent_reorder(self):
        coordinator, publisher_mock = self._make_coordinator()
        inventory_msg = make_message(
            from_agent=AgentName.INVENTORY.value,
            message_type=MessageType.INVENTORY_LOW,
            data={"product_id": "p1", "current_stock": 5},
        )
        demand_msg = make_message(
            from_agent=AgentName.DEMAND.value,
            message_type=MessageType.DEMAND_FORECAST,
            data={"product_id": "p1", "predicted_demand": 50, "confidence": 0.85},
        )
        result = run(coordinator.handle_low_stock_scenario(inventory_msg, demand_msg))
        assert result.message_type == MessageType.REORDER_NEEDED
        assert result.priority == 9
        assert result.data["urgency"] == "urgent"
        publisher_mock.publish.assert_called_once()

    def test_low_demand_produces_normal_reorder(self):
        coordinator, publisher_mock = self._make_coordinator()
        inventory_msg = make_message(
            from_agent=AgentName.INVENTORY.value,
            message_type=MessageType.INVENTORY_LOW,
            data={"product_id": "p1", "current_stock": 8},
        )
        demand_msg = make_message(
            from_agent=AgentName.DEMAND.value,
            message_type=MessageType.DEMAND_FORECAST,
            data={"product_id": "p1", "predicted_demand": 10, "confidence": 0.6},
        )
        result = run(coordinator.handle_low_stock_scenario(inventory_msg, demand_msg))
        assert result.message_type == MessageType.REORDER_NEEDED
        assert result.priority == 5
        assert result.data["urgency"] == "normal"


# ---------------------------------------------------------------------------
# 7.4.2 handle_churn_scenario
# ---------------------------------------------------------------------------

class TestChurnScenario:
    def _make_coordinator(self):
        publisher_mock = AsyncMock()
        publisher_mock.publish = AsyncMock()
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": str(uuid.uuid4())}
        ]
        return CoordinatorAgent(publisher=publisher_mock, supabase=supabase_mock), publisher_mock

    def test_good_credit_sends_re_engagement(self):
        coordinator, publisher_mock = self._make_coordinator()
        churn_msg = make_message(
            from_agent=AgentName.LIFECYCLE.value,
            message_type=MessageType.CUSTOMER_CHURN_RISK,
            data={"customer_id": "c1"},
        )
        credit_msg = make_message(
            from_agent=AgentName.CREDIT.value,
            message_type=MessageType.CREDIT_RISK_HIGH,
            data={"customer_id": "c1", "risk_score": 20},
        )
        result = run(coordinator.handle_churn_scenario(churn_msg, credit_msg))
        assert result.data["action"] == "send_re_engagement_offer"
        publisher_mock.publish.assert_called_once()

    def test_bad_credit_notifies_owner_only(self):
        coordinator, publisher_mock = self._make_coordinator()
        churn_msg = make_message(
            from_agent=AgentName.LIFECYCLE.value,
            message_type=MessageType.CUSTOMER_CHURN_RISK,
            data={"customer_id": "c2"},
        )
        credit_msg = make_message(
            from_agent=AgentName.CREDIT.value,
            message_type=MessageType.CREDIT_RISK_HIGH,
            data={"customer_id": "c2", "risk_score": 80},
        )
        result = run(coordinator.handle_churn_scenario(churn_msg, credit_msg))
        assert result.data["action"] == "notify_owner_only"


# ---------------------------------------------------------------------------
# 7.4.3 handle_credit_risk_scenario
# ---------------------------------------------------------------------------

class TestCreditRiskScenario:
    def _make_coordinator(self):
        publisher_mock = AsyncMock()
        publisher_mock.publish = AsyncMock()
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": str(uuid.uuid4())}
        ]
        return CoordinatorAgent(publisher=publisher_mock, supabase=supabase_mock), publisher_mock

    def test_high_risk_large_order_blocks(self):
        coordinator, publisher_mock = self._make_coordinator()
        credit_msg = make_message(
            from_agent=AgentName.CREDIT.value,
            message_type=MessageType.CREDIT_RISK_HIGH,
            data={"customer_id": "c1", "risk_score": 85, "outstanding_amount": 500},
        )
        order_msg = make_message(
            from_agent=AgentName.COORDINATOR.value,
            message_type=MessageType.COLLABORATION_REQUEST,
            data={"customer_id": "c1", "order_amount": 3000},
        )
        result = run(coordinator.handle_credit_risk_scenario(credit_msg, order_msg))
        assert result.data["action"] == "block_order_notify_owner"
        assert result.priority == 10

    def test_medium_risk_requires_confirmation(self):
        coordinator, publisher_mock = self._make_coordinator()
        credit_msg = make_message(
            from_agent=AgentName.CREDIT.value,
            message_type=MessageType.CREDIT_RISK_HIGH,
            data={"customer_id": "c2", "risk_score": 55, "outstanding_amount": 100},
        )
        order_msg = make_message(
            from_agent=AgentName.COORDINATOR.value,
            message_type=MessageType.COLLABORATION_REQUEST,
            data={"customer_id": "c2", "order_amount": 500},
        )
        result = run(coordinator.handle_credit_risk_scenario(credit_msg, order_msg))
        assert result.data["action"] == "require_confirmation"


# ---------------------------------------------------------------------------
# 7.5.2 get_strategy_adjustment
# ---------------------------------------------------------------------------

class TestStrategyAdjustment:
    def _make_supabase_mock(self, decisions: list):
        mock = MagicMock()
        mock.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = decisions
        return mock

    def _make_redis_mock(self):
        mock = MagicMock()
        mock.setex = MagicMock()
        return mock

    def test_high_success_rate_raises_autonomy(self):
        decisions = [{"outcome": "success"}] * 9 + [{"outcome": "failure"}]
        result = get_strategy_adjustment(
            "inventory", "store-1",
            supabase=self._make_supabase_mock(decisions),
            redis_client=self._make_redis_mock(),
        )
        assert result["autonomy_level"] == "high"
        assert result["confidence_threshold"] < 0.7

    def test_low_success_rate_restricts_autonomy(self):
        decisions = [{"outcome": "failure"}] * 8 + [{"outcome": "success"}] * 2
        result = get_strategy_adjustment(
            "inventory", "store-1",
            supabase=self._make_supabase_mock(decisions),
            redis_client=self._make_redis_mock(),
        )
        assert result["autonomy_level"] == "restricted"
        assert result["confidence_threshold"] > 0.7

    def test_no_decisions_returns_defaults(self):
        result = get_strategy_adjustment(
            "inventory", "store-1",
            supabase=self._make_supabase_mock([]),
            redis_client=self._make_redis_mock(),
        )
        assert result["success_rate"] is None
        assert result["autonomy_level"] == "normal"
        assert result["sample_size"] == 0
