"""
Agent Priority Message Queue
Uses Redis sorted set to manage messages by priority.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from agents.message_bus.protocol import AgentMessage

logger = logging.getLogger(__name__)

PRIORITY_QUEUE_KEY = "agent_priority_queue"


class PriorityMessageQueue:
    """Priority queue for agent messages backed by a Redis sorted set."""

    def __init__(self, redis_client=None):
        if redis_client is None:
            from redis_client import get_async_client
            redis_client = get_async_client()
        self._redis = redis_client

    async def push(self, message: AgentMessage) -> None:
        """Add a message to the priority queue with its priority as score."""
        try:
            payload = json.dumps(message.to_dict())
            await self._redis.zadd(PRIORITY_QUEUE_KEY, {payload: message.priority})
            logger.debug("Pushed message %s with priority %d", message.id, message.priority)
        except Exception as exc:
            logger.error("PriorityMessageQueue.push error: %s", exc)

    async def pop_highest(self) -> Optional[AgentMessage]:
        """Remove and return the highest priority message."""
        try:
            # zpopmax returns list of (member, score) tuples
            results = await self._redis.zpopmax(PRIORITY_QUEUE_KEY, count=1)
            if not results:
                return None
            payload, _score = results[0]
            data = json.loads(payload)
            return AgentMessage.from_dict(data)
        except Exception as exc:
            logger.error("PriorityMessageQueue.pop_highest error: %s", exc)
            return None

    async def peek(self, n: int = 10) -> list[AgentMessage]:
        """View top N messages by priority without removing them."""
        try:
            # zrange with rev=True and scores returns highest first
            results = await self._redis.zrange(
                PRIORITY_QUEUE_KEY, 0, n - 1, desc=True, withscores=False
            )
            messages = []
            for payload in results:
                try:
                    data = json.loads(payload)
                    messages.append(AgentMessage.from_dict(data))
                except Exception as exc:
                    logger.warning("Failed to deserialize queued message: %s", exc)
            return messages
        except Exception as exc:
            logger.error("PriorityMessageQueue.peek error: %s", exc)
            return []
