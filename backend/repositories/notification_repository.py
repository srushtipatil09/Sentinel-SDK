import uuid
from typing import Optional, Sequence
from sqlalchemy import or_, select
from backend.models.incidents import Incident
from backend.models.system import NotificationConfig, NotificationHistory
from backend.repositories.base import BaseRepository


class NotificationConfigRepository(BaseRepository[NotificationConfig]):
    def __init__(self, session):
        super().__init__(NotificationConfig, session)

    async def list_by_project(self, project_id: uuid.UUID) -> Sequence[NotificationConfig]:
        query = (
            select(NotificationConfig)
            .where(
                NotificationConfig.project_id == project_id,
                NotificationConfig.is_deleted == False
            )
            .order_by(NotificationConfig.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_project_and_id(
        self,
        project_id: uuid.UUID,
        config_id: uuid.UUID
    ) -> Optional[NotificationConfig]:
        query = select(NotificationConfig).where(
            NotificationConfig.id == config_id,
            NotificationConfig.project_id == project_id,
            NotificationConfig.is_deleted == False
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_active_by_project(self, project_id: uuid.UUID) -> Sequence[NotificationConfig]:
        query = select(NotificationConfig).where(
            NotificationConfig.project_id == project_id,
            NotificationConfig.is_enabled == True,
            NotificationConfig.is_deleted == False
        )
        result = await self.session.execute(query)
        return result.scalars().all()


class NotificationHistoryRepository(BaseRepository[NotificationHistory]):
    def __init__(self, session):
        super().__init__(NotificationHistory, session)

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Sequence[NotificationHistory]:
        query = (
            select(NotificationHistory)
            .outerjoin(Incident, NotificationHistory.incident_id == Incident.id)
            .where(
                or_(
                    Incident.project_id == project_id,
                    NotificationHistory.incident_id.is_(None)
                ),
                NotificationHistory.is_deleted == False
            )
            .order_by(NotificationHistory.sent_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_recent(self, limit: int = 15) -> Sequence[NotificationHistory]:
        query = (
            select(NotificationHistory)
            .where(NotificationHistory.is_deleted == False)
            .order_by(NotificationHistory.sent_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
