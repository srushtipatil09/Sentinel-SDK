import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.dependencies import get_current_user
from backend.database.session import get_async_session
from backend.models.users import User
from backend.schemas.common import APIResponse
from backend.schemas.notifications import (
    NotificationConfigCreate,
    NotificationConfigResponse,
    NotificationConfigUpdate,
    NotificationHistoryResponse,
    NotificationTestResponse,
)
from backend.services.notification_service import notification_service

router = APIRouter(tags=["Notifications & Alerts"])


@router.get("/projects/{project_id}/notifications/configs", response_model=APIResponse[List[NotificationConfigResponse]])
async def list_project_notification_configs(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Retrieves all notification channels configured for a project."""
    configs = await notification_service.list_configs(session, project_id, current_user.organization_id)
    return APIResponse(
        message="Notification configurations retrieved.",
        data=[NotificationConfigResponse.model_validate(c) for c in configs]
    )


@router.post(
    "/projects/{project_id}/notifications/configs",
    response_model=APIResponse[NotificationConfigResponse],
    status_code=status.HTTP_201_CREATED
)
async def create_project_notification_config(
    project_id: uuid.UUID,
    data: NotificationConfigCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Creates a new notification channel (Slack, Discord, Webhook, Email) for a project."""
    config = await notification_service.create_config(session, project_id, current_user.organization_id, data)
    return APIResponse(
        message=f"{data.channel_type.capitalize()} notification channel created successfully.",
        data=NotificationConfigResponse.model_validate(config)
    )


@router.put(
    "/projects/{project_id}/notifications/configs/{config_id}",
    response_model=APIResponse[NotificationConfigResponse]
)
async def update_project_notification_config(
    project_id: uuid.UUID,
    config_id: uuid.UUID,
    data: NotificationConfigUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Updates an existing notification channel configuration."""
    updated = await notification_service.update_config(session, project_id, current_user.organization_id, config_id, data)
    return APIResponse(
        message="Notification channel updated successfully.",
        data=NotificationConfigResponse.model_validate(updated)
    )


@router.delete(
    "/projects/{project_id}/notifications/configs/{config_id}",
    response_model=APIResponse[dict]
)
async def delete_project_notification_config(
    project_id: uuid.UUID,
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Deletes a notification channel."""
    await notification_service.delete_config(session, project_id, current_user.organization_id, config_id)
    return APIResponse(
        message="Notification channel removed successfully.",
        data={"deleted": True}
    )


@router.post(
    "/projects/{project_id}/notifications/configs/{config_id}/test",
    response_model=APIResponse[NotificationTestResponse]
)
async def test_project_notification_config(
    project_id: uuid.UUID,
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Sends a verification test alert to the target notification channel."""
    success, message = await notification_service.test_config(session, project_id, current_user.organization_id, config_id)
    return APIResponse(
        message=message,
        data=NotificationTestResponse(success=success, message=message)
    )


@router.get(
    "/projects/{project_id}/notifications/history",
    response_model=APIResponse[List[NotificationHistoryResponse]]
)
async def list_project_notification_history(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Retrieves notification delivery logs for the project."""
    history = await notification_service.list_history(
        session, project_id, current_user.organization_id, limit=limit, offset=offset
    )
    return APIResponse(
        message="Notification history retrieved.",
        data=[NotificationHistoryResponse.model_validate(h) for h in history]
    )


@router.get(
    "/notifications/recent",
    response_model=APIResponse[List[NotificationHistoryResponse]]
)
async def list_recent_notifications(
    limit: int = Query(15, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Retrieves recent alerts and notification dispatches for the active user."""
    recent = await notification_service.list_recent_alerts(session, current_user.organization_id, limit=limit)
    return APIResponse(
        message="Recent notifications retrieved.",
        data=[NotificationHistoryResponse.model_validate(h) for h in recent]
    )
