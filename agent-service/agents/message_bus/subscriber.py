"""
Agent Message Bus Subscriber
Subscribes to Redis channels and dispatches AgentMessages to handlers.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Optional

from agents.message_bus.protocol import AgentMessage, AgentName

logger = logging.getLogger(__name__)

BROADCAST_CHANNEL = "agent_messages:broadcast"


class AgentMessageSubscriber:
    """Subscribes to agent message channels and dispatches to handlers."""

    def __init__(self, redis_client=None):
        if redis_client is None:
            from redis_client import get_async_client
            redis_client = get_async_client()
        self._redis = redis_client
        self._task: Optional[asyncio.Task] = None

    async def subscribe(
        self,
        agent_name: AgentName,
        handler: Callable[[AgentMessage], None],
    ) -> None:
        """Start listening for messages addressed to agent_name and broadcasts."""
        direct_channel = f"agent_messages:{agent_name.value}"

        async def _listen():
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(direct_channel, BROADCAST_CHANNEL)
            logger.info(
                "AgentMessageSubscriber listening on %s and %s",
                direct_channel,
                BROADCAST_CHANNEL,
            )
            async for raw_message in pubsub.listen():
                if raw_message.get("type") != "message":
                    continue
                try:
                    data = json.loads(raw_message["data"])
                    message = AgentMessage.from_dict(data)
                    try:
                        result = handler(message)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as handler_exc:
                        logger.error(
                            "Handler error for message %s: %s",
                            message.id,
                            handler_exc,
                        )
                except Exception as exc:
                    logger.error("Failed to deserialize agent message: %s", exc)

        self._task = asyncio.create_task(_listen())

    def stop(self) -> None:
        """Cancel the subscriber task."""
        if self._task and not self._task.done():
            self._task.cancel()
