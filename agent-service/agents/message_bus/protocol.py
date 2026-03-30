"""
Agent Message Bus Protocol
Defines the message structure and enums for inter-agent communication.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class MessageType(str, Enum):
    INVENTORY_LOW = "inventory.low"
    INVENTORY_CRITICAL = "inventory.critical"
    DEMAND_FORECAST = "demand.forecast"
    REORDER_NEEDED = "reorder.needed"
    REORDER_APPROVED = "reorder.approved"
    CUSTOMER_CHURN_RISK = "customer.churn_risk"
    CREDIT_RISK_HIGH = "credit.risk_high"
    FRAUD_DETECTED = "fraud.detected"
    COLLABORATION_REQUEST = "collaboration.request"
    COLLABORATION_RESPONSE = "collaboration.response"
    GOAL_UPDATE = "goal.update"


class AgentName(str, Enum):
    INVENTORY = "inventory"
    DEMAND = "demand"
    REORDER = "reorder"
    CREDIT = "credit"
    FRAUD = "fraud"
    LIFECYCLE = "lifecycle"
    BI = "bi"
    COORDINATOR = "coordinator"
    NOTIFICATION = "notification"


@dataclass
class AgentMessage:
    """Canonical message structure for inter-agent communication."""

    from_agent: str
    to_agent: str  # AgentName value or "broadcast"
    message_type: str  # MessageType value
    data: dict
    priority: int = 5  # 1-10
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type,
            "data": self.data,
            "priority": self.priority,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AgentMessage":
        ts = d.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        elif ts is None:
            ts = datetime.now(timezone.utc)
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            from_agent=d["from_agent"],
            to_agent=d["to_agent"],
            message_type=d["message_type"],
            data=d.get("data", {}),
            priority=d.get("priority", 5),
            timestamp=ts,
            correlation_id=d.get("correlation_id"),
        )
