import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_current_user
from backend.database.session import get_async_session
from backend.models.users import User
from backend.schemas.analytics import OverviewStatsResponse
from backend.schemas.common import APIResponse
from backend.services.analytics_service import analytics_service
from backend.analytics.bigquery_client import bigquery_analytics

router = APIRouter(prefix="/analytics", tags=["Dashboard Analytics"])


@router.get("/overview", response_model=APIResponse[OverviewStatsResponse])
async def get_overview_stats(
    project_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Retrieves high-level platform statistics, active incidents, service health, and AI RCA resolution rates."""
    stats = await analytics_service.get_overview_stats(session, project_id, current_user.organization_id)
    return APIResponse(
        message="Analytics overview stats retrieved.",
        data=stats
    )


@router.post("/anomaly-model/train")
async def train_anomaly_model(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Train (or retrain) the BigQuery ML ARIMA+ anomaly detection model on the last 30 days of telemetry."""
    success = bigquery_analytics.train_anomaly_model()
    return {
        "status": "trained" if success else "skipped",
        "enabled": bigquery_analytics.enabled,
    }


@router.get("/anomalies")
async def get_anomalies(
    threshold: float = Query(default=0.95, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Detect anomalies from the trained BigQuery ML ARIMA+ model (last hour, above threshold)."""
    anomalies: List[Dict[str, Any]] = bigquery_analytics.detect_anomalies(anomaly_prob_threshold=threshold)
    return {
        "anomalies": anomalies,
        "count": len(anomalies),
        "enabled": bigquery_analytics.enabled,
    }

