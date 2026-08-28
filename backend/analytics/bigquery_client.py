"""BigQuery Analytics — telemetry warehouse + BigQuery ML anomaly detection.

Best-effort: disabled/unavailable → every public method no-ops safely and
returns 0 / False / [].  Never raises; never blocks the PostgreSQL pipeline.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.config.settings import settings
from backend.utils.logging import logger


class BigQueryAnalytics:
    """Singleton wrapper around BigQuery for telemetry streaming and ARIMA+ anomaly detection."""

    def __init__(self) -> None:
        self._client: Optional[Any] = None
        self._init_failed: bool = False

    # ── Feature gate ────────────────────────────────────────────────────
    @property
    def enabled(self) -> bool:
        return settings.BIGQUERY_ENABLED and bool(settings.GCP_PROJECT_ID) and not self._init_failed

    # ── Lazy client ─────────────────────────────────────────────────────
    def _get_client(self) -> Optional[Any]:
        if self._init_failed:
            return None
        if self._client is None:
            try:
                from google.cloud import bigquery
                self._client = bigquery.Client(project=settings.GCP_PROJECT_ID)
                logger.info("BigQuery client initialised", project=settings.GCP_PROJECT_ID)
            except Exception as exc:
                logger.warning("BigQuery client init failed — analytics disabled", error=str(exc))
                self._init_failed = True
                return None
        return self._client

    # ── Provisioning ────────────────────────────────────────────────────
    def ensure_dataset_and_table(self) -> None:
        """Idempotently create the dataset and hour-partitioned telemetry table."""
        if not self.enabled:
            return
        client = self._get_client()
        if client is None:
            return
        try:
            from google.cloud import bigquery

            dataset_ref = bigquery.DatasetReference(settings.GCP_PROJECT_ID, settings.BIGQUERY_DATASET)
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = settings.GCP_LOCATION
            client.create_dataset(dataset, exists_ok=True)

            table_id = f"{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}.{settings.BIGQUERY_TELEMETRY_TABLE}"
            schema = [
                bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("project_id", "STRING"),
                bigquery.SchemaField("service_name", "STRING"),
                bigquery.SchemaField("environment", "STRING"),
                bigquery.SchemaField("event_type", "STRING"),
                bigquery.SchemaField("severity_level", "STRING"),
                bigquery.SchemaField("message", "STRING"),
                bigquery.SchemaField("fingerprint", "STRING"),
                bigquery.SchemaField("status_code", "INTEGER"),
                bigquery.SchemaField("duration_ms", "FLOAT"),
                bigquery.SchemaField("is_error", "BOOLEAN"),
                bigquery.SchemaField("trace_id", "STRING"),
                bigquery.SchemaField("app_version", "STRING"),
                bigquery.SchemaField("event_timestamp", "TIMESTAMP"),
            ]
            table = bigquery.Table(table_id, schema=schema)
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.HOUR,
                field="event_timestamp",
            )
            table.clustering_fields = ["service_name", "event_type"]
            client.create_table(table, exists_ok=True)
            logger.info("BigQuery dataset and table ensured", dataset=settings.BIGQUERY_DATASET)
        except Exception as exc:
            logger.warning("BigQuery provisioning failed", error=str(exc))

    # ── Streaming insert ────────────────────────────────────────────────
    def stream_telemetry(
        self,
        project_id: str,
        service_name: str,
        environment: str,
        logs: List[Dict[str, Any]],
        exceptions: List[Dict[str, Any]],
        traces: List[Dict[str, Any]],
        metrics: List[Dict[str, Any]],
        fingerprint: Optional[str] = None,
        app_version: Optional[str] = None,
    ) -> int:
        """Flatten telemetry items to rows and stream-insert into BigQuery.

        Returns the count of rows successfully inserted (0 when disabled/error).
        """
        if not self.enabled:
            return 0
        client = self._get_client()
        if client is None:
            return 0

        rows: List[Dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        import uuid as _uuid

        def _ts(item: Dict[str, Any]) -> str:
            raw = item.get("timestamp")
            if raw:
                try:
                    return datetime.fromisoformat(str(raw)).isoformat()
                except Exception:
                    pass
            return now_iso

        # Logs
        for item in logs:
            level = str(item.get("level", "INFO")).upper()
            rows.append({
                "event_id": str(_uuid.uuid4()),
                "project_id": str(project_id),
                "service_name": service_name,
                "environment": environment,
                "event_type": "log",
                "severity_level": level,
                "message": str(item.get("message", ""))[:4096],
                "fingerprint": fingerprint or "",
                "status_code": 0,
                "duration_ms": 0.0,
                "is_error": level in ("ERROR", "CRITICAL", "FATAL"),
                "trace_id": item.get("trace_id", ""),
                "app_version": app_version or "",
                "event_timestamp": _ts(item),
            })

        # Exceptions
        for item in exceptions:
            rows.append({
                "event_id": str(_uuid.uuid4()),
                "project_id": str(project_id),
                "service_name": service_name,
                "environment": environment,
                "event_type": "exception",
                "severity_level": "ERROR",
                "message": str(item.get("message", ""))[:4096],
                "fingerprint": fingerprint or "",
                "status_code": 0,
                "duration_ms": 0.0,
                "is_error": True,
                "trace_id": item.get("trace_id", ""),
                "app_version": app_version or "",
                "event_timestamp": _ts(item),
            })

        # Traces
        for item in traces:
            sc = int(item.get("status_code", 200))
            rows.append({
                "event_id": str(_uuid.uuid4()),
                "project_id": str(project_id),
                "service_name": service_name,
                "environment": environment,
                "event_type": "trace",
                "severity_level": "ERROR" if sc >= 400 else "INFO",
                "message": str(item.get("operation_name", ""))[:4096],
                "fingerprint": fingerprint or "",
                "status_code": sc,
                "duration_ms": float(item.get("duration_ms", 0.0)),
                "is_error": sc >= 400,
                "trace_id": item.get("trace_id", ""),
                "app_version": app_version or "",
                "event_timestamp": _ts(item),
            })

        # Metrics
        for item in metrics:
            rows.append({
                "event_id": str(_uuid.uuid4()),
                "project_id": str(project_id),
                "service_name": service_name,
                "environment": environment,
                "event_type": "metric",
                "severity_level": "INFO",
                "message": str(item.get("name", ""))[:4096],
                "fingerprint": fingerprint or "",
                "status_code": 0,
                "duration_ms": 0.0,
                "is_error": False,
                "trace_id": "",
                "app_version": app_version or "",
                "event_timestamp": _ts(item),
            })

        if not rows:
            return 0

        try:
            table_id = f"{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}.{settings.BIGQUERY_TELEMETRY_TABLE}"
            errors = client.insert_rows_json(table_id, rows)
            if errors:
                logger.warning("BigQuery streaming insert partial errors", errors=str(errors)[:500])
            inserted = len(rows) - len(errors) if errors else len(rows)
            logger.debug("BigQuery telemetry streamed", rows=inserted)
            return inserted
        except Exception as exc:
            logger.warning("BigQuery streaming insert failed", error=str(exc))
            return 0

    # ── BigQuery ML: Train ARIMA+ anomaly model ─────────────────────────
    def train_anomaly_model(self) -> bool:
        """Create or replace an ARIMA_PLUS model on per-minute error counts over the last 30 days."""
        if not self.enabled:
            return False
        client = self._get_client()
        if client is None:
            return False
        try:
            fq_model = f"`{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}.{settings.BIGQUERY_ANOMALY_MODEL}`"
            fq_table = f"`{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}.{settings.BIGQUERY_TELEMETRY_TABLE}`"
            query = f"""
            CREATE OR REPLACE MODEL {fq_model}
            OPTIONS(
                model_type='ARIMA_PLUS',
                time_series_timestamp_col='minute',
                time_series_data_col='error_count',
                time_series_id_col='service_name',
                auto_arima=TRUE,
                data_frequency='AUTO_FREQUENCY',
                holiday_region='GLOBAL'
            ) AS
            SELECT
                TIMESTAMP_TRUNC(event_timestamp, MINUTE) AS minute,
                service_name,
                COUNTIF(is_error) AS error_count
            FROM {fq_table}
            WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            GROUP BY minute, service_name
            """
            job = client.query(query)
            job.result()  # blocks until training completes
            logger.info("BigQuery ML ARIMA+ anomaly model trained", model=settings.BIGQUERY_ANOMALY_MODEL)
            return True
        except Exception as exc:
            logger.warning("BigQuery ML model training failed", error=str(exc))
            return False

    # ── BigQuery ML: Detect anomalies ───────────────────────────────────
    def detect_anomalies(self, anomaly_prob_threshold: float = 0.95) -> List[Dict[str, Any]]:
        """Run ML.DETECT_ANOMALIES and return recent anomalous service-minutes."""
        if not self.enabled:
            return []
        client = self._get_client()
        if client is None:
            return []
        try:
            fq_model = f"`{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}.{settings.BIGQUERY_ANOMALY_MODEL}`"
            query = f"""
            SELECT
                service_name,
                minute AS timestamp,
                error_count,
                upper_bound,
                anomaly_probability
            FROM ML.DETECT_ANOMALIES(
                MODEL {fq_model},
                STRUCT({anomaly_prob_threshold} AS anomaly_prob_threshold)
            )
            WHERE is_anomaly = TRUE
              AND minute >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
            ORDER BY anomaly_probability DESC
            """
            rows = list(client.query(query).result())
            anomalies: List[Dict[str, Any]] = []
            for row in rows:
                anomalies.append({
                    "service_name": row.service_name,
                    "timestamp": row.timestamp.isoformat() if hasattr(row.timestamp, "isoformat") else str(row.timestamp),
                    "error_count": row.error_count,
                    "upper_bound": row.upper_bound,
                    "anomaly_probability": row.anomaly_probability,
                })
            logger.info("BigQuery ML anomalies detected", count=len(anomalies))
            return anomalies
        except Exception as exc:
            logger.warning("BigQuery ML anomaly detection failed", error=str(exc))
            return []


bigquery_analytics = BigQueryAnalytics()
