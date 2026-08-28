"""EventBus — Google Cloud Pub/Sub event transport.

Publishes events to Pub/Sub topics. Never raises; logs and returns bool.
"""
import asyncio
from typing import Any, Dict

from backend.queue.pubsub_client import pubsub_manager
from backend.utils.logging import logger


class EventBus:
    """Singleton async event bus that publishes via Google Cloud Pub/Sub."""

    async def publish(self, name: str, payload: Dict[str, Any]) -> bool:
        """Publish *payload* to Pub/Sub topic *name*.

        Returns True on success, False on failure. Never raises.
        """
        try:
            # pubsub_manager.publish_message is synchronous (gRPC),
            # run in a thread to avoid blocking the async loop.
            success = await asyncio.to_thread(pubsub_manager.publish_message, name, payload)
            if not success:
                logger.warning("Pub/Sub publish returned False", topic=name)
            return success
        except Exception as exc:
            logger.warning("EventBus publish failed", topic=name, error=str(exc))
            return False


event_bus = EventBus()
