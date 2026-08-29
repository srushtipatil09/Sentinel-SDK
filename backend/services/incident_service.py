import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.incidents import Incident, IncidentTimeline
from backend.repositories.incident_repository import IncidentRepository
from backend.utils.exceptions import NotFoundError


class IncidentService:
    async def list_incidents(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        service_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Incident]:
        from backend.api.dependencies import verify_project_ownership
        await verify_project_ownership(session, project_id, organization_id)

        repo = IncidentRepository(session)
        return list(await repo.list_by_project(
            project_id=project_id,
            status=status,
            severity=severity,
            service_id=service_id,
            limit=limit,
            offset=offset
        ))

    async def get_incident_details(
        self,
        session: AsyncSession,
        incident_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Incident:
        from backend.api.dependencies import verify_incident_ownership
        return await verify_incident_ownership(session, incident_id, organization_id)

    async def update_incident_status(
        self,
        session: AsyncSession,
        incident_id: uuid.UUID,
        organization_id: uuid.UUID,
        new_status: str,
        summary: Optional[str] = None
    ) -> Incident:
        from backend.api.dependencies import verify_incident_ownership
        incident = await verify_incident_ownership(session, incident_id, organization_id)

        incident.status = new_status
        if summary:
            incident.root_cause_summary = summary
        if new_status == "RESOLVED":
            incident.resolved_at = datetime.now(timezone.utc)

        timeline_event = IncidentTimeline(
            incident_id=incident.id,
            event_type="STATUS_CHANGED",
            message=f"Incident status updated to {new_status}.",
            metadata_json={"summary": summary}
        )
        session.add(timeline_event)
        await session.flush()
        return incident

    async def assign_incident(
        self,
        session: AsyncSession,
        incident_id: uuid.UUID,
        organization_id: uuid.UUID,
        assigned_to_id: uuid.UUID
    ) -> Incident:
        from backend.api.dependencies import verify_incident_ownership
        incident = await verify_incident_ownership(session, incident_id, organization_id)

        incident.assigned_to_id = assigned_to_id
        timeline_event = IncidentTimeline(
            incident_id=incident.id,
            event_type="ASSIGNED",
            message=f"Incident assigned to user {assigned_to_id}.",
            metadata_json={"assigned_to_id": str(assigned_to_id)}
        )
        session.add(timeline_event)
        await session.flush()
        return incident

    async def add_comment(
        self,
        session: AsyncSession,
        incident_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        comment_text: str
    ) -> Any:
        from backend.models.incidents import IncidentComment
        from backend.api.dependencies import verify_incident_ownership
        await verify_incident_ownership(session, incident_id, organization_id)

        comment = IncidentComment(
            incident_id=incident_id,
            user_id=user_id,
            comment=comment_text
        )
        session.add(comment)
        await session.flush()
        return comment

    async def investigate_incident(
        self,
        session: AsyncSession,
        incident_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Incident:
        from backend.api.dependencies import verify_incident_ownership
        from backend.incidents.detector import incident_detector
        from backend.repositories.telemetry_repository import (
            TelemetryExceptionRepository,
            TelemetryLogRepository,
            TelemetryTraceRepository,
        )
        from backend.repositories.project_repository import ServiceRepository

        incident = await verify_incident_ownership(session, incident_id, organization_id)
        service_repo = ServiceRepository(session)
        service = await service_repo.get_by_id(incident.service_id)
        service_name = service.name if service else "unknown-service"

        # Fetch recent telemetry logs, exceptions, traces
        log_repo = TelemetryLogRepository(session)
        exc_repo = TelemetryExceptionRepository(session)
        trace_repo = TelemetryTraceRepository(session)

        raw_logs_models = await log_repo.query_logs(
            project_id=incident.project_id,
            service_id=incident.service_id,
            limit=20
        )
        raw_exc_models = await exc_repo.query_exceptions(
            project_id=incident.project_id,
            service_id=incident.service_id,
            limit=10
        )
        raw_trace_models = await trace_repo.get_slow_spans(
            project_id=incident.project_id,
            service_id=incident.service_id,
            min_duration_ms=0.0,
            limit=20
        )

        logs = [
            {"level": l.level, "message": l.message, "timestamp": l.timestamp.isoformat() if l.timestamp else None}
            for l in raw_logs_models
        ]
        exceptions = [
            {"exception_type": e.exception_type, "message": e.message, "stacktrace": e.stacktrace, "handled": e.handled}
            for e in raw_exc_models
        ]
        traces = [
            {"operation_name": t.operation_name, "duration_ms": t.duration_ms, "status_code": t.status_code, "endpoint": t.operation_name}
            for t in raw_trace_models
        ]

        await incident_detector._trigger_ai_rca_workflow(
            session=session,
            incident=incident,
            service_name=service_name,
            logs=logs,
            exceptions=exceptions,
            traces=traces,
            metrics={"count": len(traces)},
            deployments=[]
        )

        await session.flush()
        return await verify_incident_ownership(session, incident_id, organization_id)


incident_service = IncidentService()

