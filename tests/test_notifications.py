import uuid
from unittest.mock import patch, AsyncMock
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.users import User, Organization
from backend.models.projects import Project
from backend.models.system import NotificationConfig, NotificationHistory
from backend.models.incidents import Incident
from backend.repositories.user_repository import UserRepository, OrganizationRepository
from backend.repositories.project_repository import ProjectRepository
from backend.repositories.incident_repository import IncidentRepository
from backend.notifications.notifier import notification_engine
from backend.utils.security import create_access_token, hash_password


@pytest_asyncio.fixture
async def setup_notification_test_data(test_session: AsyncSession):
    """Sets up Org, User, Project, and Incident for notification testing."""
    org_repo = OrganizationRepository(test_session)
    user_repo = UserRepository(test_session)
    proj_repo = ProjectRepository(test_session)
    inc_repo = IncidentRepository(test_session)

    uid = uuid.uuid4().hex[:8]

    org = await org_repo.create(Organization(name=f"Notif Org {uid}", slug=f"notif-org-{uid}", plan="enterprise"))
    user = await user_repo.create(User(
        email=f"notif-user-{uid}@sentinel.ai",
        password_hash=hash_password("PassSecure123!"),
        full_name="Notification Tester",
        role="owner",
        organization_id=org.id
    ))
    project = await proj_repo.create(Project(
        organization_id=org.id,
        name=f"Notif Project {uid}",
        slug=f"notif-proj-{uid}",
        environment="production"
    ))
    incident = await inc_repo.create(Incident(
        project_id=project.id,
        title="Simulated DB Connection Outage",
        severity="P1",
        status="INVESTIGATING",
        service_name="payment-gateway",
        fingerprint=f"fp-notif-{uid}"
    ))

    token = create_access_token({"sub": str(user.id), "org": str(org.id)})

    return {
        "org": org,
        "user": user,
        "project": project,
        "incident": incident,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"}
    }


@pytest.mark.asyncio
async def test_notification_config_crud_endpoints(
    async_client: AsyncClient,
    setup_notification_test_data: dict
):
    """Verifies complete CRUD operations for notification channels."""
    project_id = setup_notification_test_data["project"].id
    headers = setup_notification_test_data["headers"]

    # 1. Create a Slack config
    slack_payload = {
        "channel_type": "slack",
        "target_url": "https://hooks.slack.com/services/T00/B00/X123",
        "settings_json": {"severity_filter": "P1"},
        "is_enabled": True
    }
    create_res = await async_client.post(
        f"/projects/{project_id}/notifications/configs",
        json=slack_payload,
        headers=headers
    )
    assert create_res.status_code == 201
    created_config = create_res.json()["data"]
    config_id = created_config["id"]
    assert created_config["channel_type"] == "slack"
    assert created_config["target_url"] == "https://hooks.slack.com/services/T00/B00/X123"
    assert created_config["settings_json"]["severity_filter"] == "P1"
    assert created_config["is_enabled"] is True

    # 2. List configs
    list_res = await async_client.get(
        f"/projects/{project_id}/notifications/configs",
        headers=headers
    )
    assert list_res.status_code == 200
    configs = list_res.json()["data"]
    assert len(configs) >= 1
    assert any(c["id"] == config_id for c in configs)

    # 3. Update config (disable and change severity)
    update_payload = {
        "is_enabled": False,
        "settings_json": {"severity_filter": "P0"}
    }
    update_res = await async_client.put(
        f"/projects/{project_id}/notifications/configs/{config_id}",
        json=update_payload,
        headers=headers
    )
    assert update_res.status_code == 200
    updated = update_res.json()["data"]
    assert updated["is_enabled"] is False
    assert updated["settings_json"]["severity_filter"] == "P0"

    # 4. Delete config
    delete_res = await async_client.delete(
        f"/projects/{project_id}/notifications/configs/{config_id}",
        headers=headers
    )
    assert delete_res.status_code == 200
    assert delete_res.json()["data"]["deleted"] is True

    # 5. Verify deleted from list
    list_res_after = await async_client.get(
        f"/projects/{project_id}/notifications/configs",
        headers=headers
    )
    assert not any(c["id"] == config_id for c in list_res_after.json()["data"])


@pytest.mark.asyncio
async def test_notification_channel_test_and_history(
    async_client: AsyncClient,
    setup_notification_test_data: dict
):
    """Verifies testing an alert channel endpoint and checking delivery history."""
    project_id = setup_notification_test_data["project"].id
    headers = setup_notification_test_data["headers"]

    # 1. Create a webhook channel
    create_res = await async_client.post(
        f"/projects/{project_id}/notifications/configs",
        json={
            "channel_type": "discord",
            "target_url": "https://discord.com/api/webhooks/12345/abcdef",
            "settings_json": {"severity_filter": "P2"},
            "is_enabled": True
        },
        headers=headers
    )
    assert create_res.status_code == 201
    config_id = create_res.json()["data"]["id"]

    # 2. Test notification channel with mocked HTTP call
    with patch.object(notification_engine, "_send_discord_webhook", new=AsyncMock(return_value=True)):
        test_res = await async_client.post(
            f"/projects/{project_id}/notifications/configs/{config_id}/test",
            headers=headers
        )
        assert test_res.status_code == 200
        test_data = test_res.json()["data"]
        assert test_data["success"] is True
        assert "verified successfully" in test_data["message"]

    # 3. Check delivery history for project
    hist_res = await async_client.get(
        f"/projects/{project_id}/notifications/history",
        headers=headers
    )
    assert hist_res.status_code == 200
    history = hist_res.json()["data"]
    assert len(history) >= 1
    recent_entry = history[0]
    assert recent_entry["channel_type"] == "discord"
    assert recent_entry["status"] == "SENT"

    # 4. Check recent notifications endpoint for topbar
    recent_res = await async_client.get(
        "/notifications/recent",
        headers=headers
    )
    assert recent_res.status_code == 200
    recent_list = recent_res.json()["data"]
    assert len(recent_list) >= 1


@pytest.mark.asyncio
async def test_notification_engine_severity_filtering(
    test_session: AsyncSession,
    setup_notification_test_data: dict
):
    """Verifies that NotificationEngine filters incident dispatches based on severity thresholds."""
    project = setup_notification_test_data["project"]

    # Config 1: P0 threshold only
    cfg_critical = NotificationConfig(
        project_id=project.id,
        channel_type="webhook",
        target_url="https://api.example.com/p0-alerts",
        settings_json={"severity_filter": "P0"},
        is_enabled=True
    )
    # Config 2: P2 threshold (P0, P1, P2)
    cfg_medium = NotificationConfig(
        project_id=project.id,
        channel_type="webhook",
        target_url="https://api.example.com/all-alerts",
        settings_json={"severity_filter": "P2"},
        is_enabled=True
    )
    test_session.add_all([cfg_critical, cfg_medium])
    await test_session.flush()

    # Dispatch a P2 incident alert
    with patch.object(notification_engine, "_send_generic_webhook", new=AsyncMock(return_value=True)) as mock_webhook:
        dispatched = await notification_engine.dispatch_project_incident_alert(
            session=test_session,
            project_id=project.id,
            incident_title="Database Latency Spike",
            severity="P2",
            service_name="postgres-primary"
        )
        # Should only dispatch to cfg_medium (1 call), skipping cfg_critical (which requires P0)
        assert len(dispatched) == 1
        assert dispatched[0] is True
        assert mock_webhook.call_count == 1
