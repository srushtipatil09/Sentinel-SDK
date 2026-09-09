import uuid
from typing import Optional, Sequence, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.dependencies import verify_project_ownership
from backend.models.system import NotificationConfig, NotificationHistory
from backend.notifications.notifier import notification_engine
from backend.repositories.notification_repository import (
    NotificationConfigRepository,
    NotificationHistoryRepository,
)
from backend.schemas.notifications import NotificationConfigCreate, NotificationConfigUpdate
from backend.utils.exceptions import NotFoundError


class NotificationService:
    async def list_configs(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Sequence[NotificationConfig]:
        await verify_project_ownership(session, project_id, organization_id)
        repo = NotificationConfigRepository(session)
        return await repo.list_by_project(project_id)

    async def get_config(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        config_id: uuid.UUID
    ) -> NotificationConfig:
        await verify_project_ownership(session, project_id, organization_id)
        repo = NotificationConfigRepository(session)
        config = await repo.get_by_project_and_id(project_id, config_id)
        if not config:
            raise NotFoundError("NotificationConfig", config_id)
        return config

    async def create_config(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        data: NotificationConfigCreate
    ) -> NotificationConfig:
        await verify_project_ownership(session, project_id, organization_id)
        repo = NotificationConfigRepository(session)
        config = NotificationConfig(
            project_id=project_id,
            channel_type=data.channel_type.lower().strip(),
            target_url=data.target_url.strip() if data.target_url else None,
            settings_json=data.settings_json or {},
            is_enabled=data.is_enabled
        )
        created = await repo.create(config)
        return created

    async def update_config(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        config_id: uuid.UUID,
        data: NotificationConfigUpdate
    ) -> NotificationConfig:
        await verify_project_ownership(session, project_id, organization_id)
        repo = NotificationConfigRepository(session)
        config = await repo.get_by_project_and_id(project_id, config_id)
        if not config:
            raise NotFoundError("NotificationConfig", config_id)

        if data.channel_type is not None:
            config.channel_type = data.channel_type.lower().strip()
        if data.target_url is not None:
            config.target_url = data.target_url.strip() if data.target_url else None
        if data.settings_json is not None:
            config.settings_json = data.settings_json
        if data.is_enabled is not None:
            config.is_enabled = data.is_enabled

        await session.flush()
        await session.refresh(config)
        return config

    async def delete_config(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        config_id: uuid.UUID
    ) -> bool:
        await verify_project_ownership(session, project_id, organization_id)
        repo = NotificationConfigRepository(session)
        config = await repo.get_by_project_and_id(project_id, config_id)
        if not config:
            raise NotFoundError("NotificationConfig", config_id)
        config.soft_delete()
        await session.flush()
        return True

    async def test_config(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        config_id: uuid.UUID
    ) -> Tuple[bool, str]:
        await verify_project_ownership(session, project_id, organization_id)
        repo = NotificationConfigRepository(session)
        config = await repo.get_by_project_and_id(project_id, config_id)
        if not config:
            raise NotFoundError("NotificationConfig", config_id)

        success, error_msg = await notification_engine.send_test_alert(config, session=session)
        if success:
            return True, f"Test notification successfully dispatched to {config.channel_type.capitalize()}."
        return False, error_msg or f"Failed to deliver test notification to {config.channel_type.capitalize()}."

    async def list_history(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Sequence[NotificationHistory]:
        await verify_project_ownership(session, project_id, organization_id)
        repo = NotificationHistoryRepository(session)
        return await repo.list_by_project(project_id=project_id, limit=limit, offset=offset)

    async def list_recent_alerts(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        limit: int = 15
    ) -> Sequence[NotificationHistory]:
        repo = NotificationHistoryRepository(session)
        return await repo.list_recent(limit=limit)


notification_service = NotificationService()
