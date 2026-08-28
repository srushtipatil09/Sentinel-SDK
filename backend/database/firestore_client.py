"""Firestore live incident-state mirror — best-effort, never blocks the DB transaction.

Disabled/unavailable → every public method no-ops safely and returns False.
"""
from typing import Any, Dict, Optional

from backend.config.settings import settings
from backend.utils.logging import logger


class FirestoreManager:
    """Singleton wrapper around Google Cloud Firestore for live incident state mirroring."""

    def __init__(self) -> None:
        self._client: Optional[Any] = None
        self._init_failed: bool = False

    # ── Feature gate ────────────────────────────────────────────────────
    @property
    def enabled(self) -> bool:
        return settings.FIRESTORE_ENABLED and bool(settings.GCP_PROJECT_ID) and not self._init_failed

    # ── Lazy client ─────────────────────────────────────────────────────
    def _get_client(self) -> Optional[Any]:
        if self._init_failed:
            return None
        if self._client is None:
            try:
                from google.cloud import firestore
                self._client = firestore.Client(project=settings.GCP_PROJECT_ID)
                logger.info("Firestore client initialised", project=settings.GCP_PROJECT_ID)
            except Exception as exc:
                logger.warning("Firestore client init failed — incident mirror disabled", error=str(exc))
                self._init_failed = True
                return None
        return self._client

    # ── Upsert (merge-write) ────────────────────────────────────────────
    def upsert_incident(self, incident_id: str, data: dict) -> bool:
        """Merge-write incident data into the live incidents collection."""
        if not self.enabled:
            return False
        client = self._get_client()
        if client is None:
            return False
        try:
            from google.cloud.firestore_v1 import SERVER_TIMESTAMP
            doc_ref = client.collection(settings.FIRESTORE_INCIDENTS_COLLECTION).document(incident_id)
            data["updated_at"] = SERVER_TIMESTAMP
            doc_ref.set(data, merge=True)
            logger.debug("Firestore incident upserted", incident_id=incident_id)
            return True
        except Exception as exc:
            logger.warning("Firestore upsert_incident failed", incident_id=incident_id, error=str(exc))
            return False

    # ── Status update ───────────────────────────────────────────────────
    def update_incident_status(self, incident_id: str, status: str, extra: Dict[str, Any] | None = None) -> bool:
        """Update the status field (and optional extra fields) for an incident document."""
        if not self.enabled:
            return False
        payload: Dict[str, Any] = {"status": status}
        if extra:
            payload.update(extra)
        return self.upsert_incident(incident_id, payload)


firestore_manager = FirestoreManager()
