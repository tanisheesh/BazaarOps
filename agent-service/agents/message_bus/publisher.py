"""
Agent Message Bus Publisher
Publishes AgentMessages to Redis channels and priority sorted set.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from agents.message_bus.protocol import AgentMessage, AgentName, MessageType

logger = logging.getLogger(__name__)

BROADCAST_CHANNEL = "agent_messages:broadcast"
PRIORITY_QUEUE_KEY = "agent_priority_queue"


class AgentMessagePublisher:
    """Publishes agent messages to Redis pub/sub channels and priority queue."""

    def __init__(self, redis_client=None):
        if redis_client is None:
            from redis_client import get_async_client
            redis_client = get_async_client()
        self._redis = redis_client

    async def publish(self, message: AgentMessage) -> None:
        """Publish a message to the appropriate Redis channel and priority queue."""
        try:
            payload = json.dumps(message.to_dict())

            # Direct or broadcast channel
            if message.to_agent == "broadcast":
                channel = BROADCAST_CHANNEL
            else:
                channel = f"agent_messages:{message.to_agent}"

            await self._redis.publish(channel, payload)

            # Also push to priority sorted set (higher priority = higher score)
            await self._redis.zadd(
                PRIORITY_QUEUE_KEY,
                {payload: message.priority},
            )

            logger.debug(
                "Published message %s from %s to %s (priority=%d)",
                message.id,
                message.from_agent,
                message.to_agent,
                message.priority,
            )
        except Exception as exc:
            logger.error("AgentMessagePublisher.publish error: %s", exc)

    async def broadcast(
        self,
        from_agent: str,
        message_type: str,
        data: dict,
        priority: int = 5,
        correlation_id: Optional[str] = None,
    ) -> AgentMessage:
        """Convenience method to broadcast a message to all agents."""
        message = AgentMessage(
            from_agent=from_agent,
            to_agent="broadcast",
            message_type=message_type,
            data=data,
            priority=priority,
            correlation_id=correlation_id,
        )
        await self.publish(message)
        return message
