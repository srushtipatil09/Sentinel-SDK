"""Google Cloud Pub/Sub event transport.

Disabled/unavailable → every public method no-ops safely and returns False.
"""
import json
from typing import Any, Dict, Optional

from backend.config.settings import settings
from backend.utils.logging import logger


class PubSubManager:
    """Singleton wrapper around Google Cloud Pub/Sub PublisherClient."""

    def __init__(self) -> None:
        self._publisher: Optional[Any] = None
        self._init_failed: bool = False

    # ── Feature gate ────────────────────────────────────────────────────
    @property
    def enabled(self) -> bool:
        return settings.PUBSUB_ENABLED and bool(settings.GCP_PROJECT_ID) and not self._init_failed

    # ── Lazy publisher ──────────────────────────────────────────────────
    def _get_publisher(self) -> Optional[Any]:
        if self._init_failed:
            return None
        if self._publisher is None:
            try:
                from google.cloud import pubsub_v1
                self._publisher = pubsub_v1.PublisherClient()
                logger.info("Pub/Sub publisher client initialised", project=settings.GCP_PROJECT_ID)
            except Exception as exc:
                logger.warning("Pub/Sub publisher init failed — event bus disabled", error=str(exc))
                self._init_failed = True
                return None
        return self._publisher

    # ── Provisioning ────────────────────────────────────────────────────
    def ensure_topics(self) -> None:
        """Idempotently create the configured Pub/Sub topics."""
        if not self.enabled:
            return
        publisher = self._get_publisher()
        if publisher is None:
            return
        try:
            from google.api_core.exceptions import AlreadyExists

            topic_names = [
                settings.PUBSUB_TELEMETRY_TOPIC,
                settings.PUBSUB_INCIDENT_TOPIC,
                settings.PUBSUB_RCA_TOPIC,
            ]
            for name in topic_names:
                topic_path = publisher.topic_path(settings.GCP_PROJECT_ID, name)
                try:
                    publisher.create_topic(request={"name": topic_path})
                    logger.info("Pub/Sub topic created", topic=name)
                except AlreadyExists:
                    logger.debug("Pub/Sub topic already exists", topic=name)
        except Exception as exc:
            logger.warning("Pub/Sub topic provisioning failed", error=str(exc))

    # ── Publish ─────────────────────────────────────────────────────────
    def publish_message(self, topic_name: str, payload: Dict[str, Any]) -> bool:
        """Publish a JSON payload to a Pub/Sub topic."""
        if not self.enabled:
            return False
        publisher = self._get_publisher()
        if publisher is None:
            return False
        try:
            topic_path = publisher.topic_path(settings.GCP_PROJECT_ID, topic_name)
            data = json.dumps(payload, default=str).encode("utf-8")
            future = publisher.publish(topic_path, data)
            future.result(timeout=10)
            logger.debug("Pub/Sub message published", topic=topic_name)
            return True
        except Exception as exc:
            logger.warning("Pub/Sub publish failed", topic=topic_name, error=str(exc))
            return False


pubsub_manager = PubSubManager()
