import uuid
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models.users import User, Organization
from backend.models.projects import Project, ApiKey
from backend.repositories.user_repository import UserRepository, OrganizationRepository
from backend.repositories.project_repository import ProjectRepository, ApiKeyRepository
from backend.utils.security import create_access_token, generate_api_key, hash_password
from backend.services.project_service import project_service
from backend.schemas.auth import ApiKeyCreate

import pytest_asyncio


@pytest_asyncio.fixture
async def setup_sdk_lifecycle_data(test_session: AsyncSession):
    """Sets up Org 1 (User 1, Proj 1) and Org 2 (User 2, Proj 2) with no initial API keys."""
    org_repo = OrganizationRepository(test_session)
    user_repo = UserRepository(test_session)
    proj_repo = ProjectRepository(test_session)

    uid = uuid.uuid4().hex[:8]

    # Org 1
    org_1 = await org_repo.create(Organization(name=f"Org One {uid}", slug=f"org-one-{uid}", plan="enterprise"))
    user_1 = await user_repo.create(User(
        email=f"user1-{uid}@org-one.com",
        password_hash=hash_password("Pass123!"),
        full_name="User One",
        role="owner",
        organization_id=org_1.id
    ))
    proj_1 = await proj_repo.create(Project(
        organization_id=org_1.id,
        name=f"Proj One {uid}",
        slug=f"proj-one-{uid}",
        environment="production"
    ))

    # Org 2
    org_2 = await org_repo.create(Organization(name=f"Org Two {uid}", slug=f"org-two-{uid}", plan="enterprise"))
    user_2 = await user_repo.create(User(
        email=f"user2-{uid}@org-two.com",
        password_hash=hash_password("PassTwo123!"),
        full_name="User Two",
        role="owner",
        organization_id=org_2.id
    ))
    proj_2 = await proj_repo.create(Project(
        organization_id=org_2.id,
        name=f"Proj Two {uid}",
        slug=f"proj-two-{uid}",
        environment="production"
    ))

    await test_session.commit()

    token_1 = create_access_token(subject=str(user_1.id), extra_claims={"org_id": str(org_1.id), "role": "owner"})
    token_2 = create_access_token(subject=str(user_2.id), extra_claims={"org_id": str(org_2.id), "role": "owner"})

    return {
        "org_1": org_1, "user_1": user_1, "proj_1": proj_1, "token_1": token_1,
        "org_2": org_2, "user_2": user_2, "proj_2": proj_2, "token_2": token_2
    }


@pytest.mark.asyncio
async def test_project_with_no_key_can_generate_key(async_client: AsyncClient, setup_sdk_lifecycle_data):
    """Verifies that a project with no active key can generate a new SDK API key."""
    data = setup_sdk_lifecycle_data
    headers_1 = {"Authorization": f"Bearer {data['token_1']}"}
    proj_1_id = data["proj_1"].id

    # 1. Verify list_api_keys is empty initially
    resp = await async_client.get(f"/api/v1/projects/{proj_1_id}/api-keys", headers=headers_1)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 0

    # 2. Generate SDK Key
    resp = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Primary Ingestion Key"},
        headers=headers_1
    )
    assert resp.status_code == 201
    res_data = resp.json()["data"]
    assert res_data["name"] == "Primary Ingestion Key"
    assert res_data["is_active"] is True
    assert "raw_key" in res_data
    assert res_data["raw_key"].startswith("obs_live_") or len(res_data["raw_key"]) > 10

    # 3. Verify key is returned in list endpoint
    resp = await async_client.get(f"/api/v1/projects/{proj_1_id}/api-keys", headers=headers_1)
    assert resp.status_code == 200
    keys = resp.json()["data"]
    assert len(keys) == 1
    assert keys[0]["id"] == res_data["id"]
    assert keys[0]["is_active"] is True


@pytest.mark.asyncio
async def test_cannot_generate_second_active_key(async_client: AsyncClient, setup_sdk_lifecycle_data):
    """Verifies that generating a second SDK key while an active key exists is rejected."""
    data = setup_sdk_lifecycle_data
    headers_1 = {"Authorization": f"Bearer {data['token_1']}"}
    proj_1_id = data["proj_1"].id

    # Generate first key
    resp1 = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "First Key"},
        headers=headers_1
    )
    assert resp1.status_code == 201

    # Attempt to generate second key -> must be rejected with 422/400 validation error
    resp2 = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Second Key"},
        headers=headers_1
    )
    assert resp2.status_code in (400, 422)
    assert "already has an active SDK" in resp2.json()["error"]["message"]



@pytest.mark.asyncio
async def test_active_key_authenticates_ingestion(async_client: AsyncClient, setup_sdk_lifecycle_data):
    """Verifies that the generated active key authenticates SDK ingestion requests."""
    data = setup_sdk_lifecycle_data
    headers_1 = {"Authorization": f"Bearer {data['token_1']}"}
    proj_1_id = data["proj_1"].id

    # Generate Key
    resp = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Ingest Key"},
        headers=headers_1
    )
    raw_key = resp.json()["data"]["raw_key"]

    # Post telemetry payload using generated raw key
    payload = {
        "service_name": "payment-service",
        "environment": "production",
        "logs": [{"timestamp": "2026-08-26T12:00:00Z", "level": "INFO", "message": "Telemetry ingest test"}],
        "exceptions": [],
        "traces": [],
        "metrics": [],
        "deployments": []
    }
    ingest_resp = await async_client.post("/api/v1/sdk/ingest", json=payload, headers={"X-API-Key": raw_key})
    assert ingest_resp.status_code == 202


@pytest.mark.asyncio
async def test_delete_key_allows_new_key_generation(async_client: AsyncClient, setup_sdk_lifecycle_data):
    """Verifies that revoking/deleting the active key allows a new key to be generated."""
    data = setup_sdk_lifecycle_data
    headers_1 = {"Authorization": f"Bearer {data['token_1']}"}
    proj_1_id = data["proj_1"].id

    # 1. Create initial key
    resp1 = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Initial Key"},
        headers=headers_1
    )
    key_id = resp1.json()["data"]["id"]
    old_raw_key = resp1.json()["data"]["raw_key"]

    # 2. Delete / Revoke key
    del_resp = await async_client.delete(f"/api/v1/projects/{proj_1_id}/api-keys/{key_id}", headers=headers_1)
    assert del_resp.status_code == 200

    # 3. Verify old key can no longer ingest telemetry -> 401 Unauthorized
    payload = {
        "service_name": "payment-service",
        "environment": "production",
        "logs": [{"timestamp": "2026-08-26T12:00:00Z", "level": "INFO", "message": "Test with revoked key"}],
        "exceptions": [],
        "traces": [],
        "metrics": [],
        "deployments": []
    }
    fail_ingest = await async_client.post("/api/v1/sdk/ingest", json=payload, headers={"X-API-Key": old_raw_key})
    assert fail_ingest.status_code == 401

    # 4. Generate replacement key -> success
    resp2 = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Replacement Key"},
        headers=headers_1
    )
    assert resp2.status_code == 201
    new_raw_key = resp2.json()["data"]["raw_key"]

    # 5. New key successfully ingests telemetry
    success_ingest = await async_client.post("/api/v1/sdk/ingest", json=payload, headers={"X-API-Key": new_raw_key})
    assert success_ingest.status_code == 202


@pytest.mark.asyncio
async def test_hard_delete_key_persistence_and_database_verification(async_client: AsyncClient, setup_sdk_lifecycle_data, test_session: AsyncSession):
    """Verifies that deleting an active SDK API key permanently removes the row (0 rows) from PostgreSQL DB."""
    data = setup_sdk_lifecycle_data
    headers_1 = {"Authorization": f"Bearer {data['token_1']}"}
    headers_2 = {"Authorization": f"Bearer {data['token_2']}"}
    proj_1_id = data["proj_1"].id
    proj_2_id = data["proj_2"].id
    key_repo = ApiKeyRepository(test_session)

    # 1. Create active API key
    gen_resp = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Key to Hard Delete"},
        headers=headers_1
    )
    assert gen_resp.status_code == 201
    key_id = uuid.UUID(gen_resp.json()["data"]["id"])

    # Verify DB before delete: row exists
    key_before = await key_repo.get_by_id(key_id, include_deleted=True)
    assert key_before is not None

    # 2. Delete key using DELETE endpoint
    del_resp = await async_client.delete(f"/api/v1/projects/{proj_1_id}/api-keys/{key_id}", headers=headers_1)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True

    # 3. Direct DB Check: row is PHYSICALLY DELETED (0 rows exist)
    test_session.expire_all()
    key_after = await key_repo.get_by_id(key_id, include_deleted=True)
    assert key_after is None

    # 4. List endpoint returns no active keys for project
    list_resp = await async_client.get(f"/api/v1/projects/{proj_1_id}/api-keys", headers=headers_1)
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) == 0

    # 5. Cross-org delete rejected -> 404
    gen_resp2 = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Key 2"},
        headers=headers_1
    )
    key_2_id = gen_resp2.json()["data"]["id"]

    cross_org_del = await async_client.delete(f"/api/v1/projects/{proj_1_id}/api-keys/{key_2_id}", headers=headers_2)
    assert cross_org_del.status_code == 404

    # 6. Cross-project delete rejected -> 404
    cross_proj_del = await async_client.delete(f"/api/v1/projects/{proj_2_id}/api-keys/{key_2_id}", headers=headers_1)
    assert cross_proj_del.status_code == 404

    # 7. Repeated delete of already deleted key -> 404
    repeat_del = await async_client.delete(f"/api/v1/projects/{proj_1_id}/api-keys/{key_id}", headers=headers_1)
    assert repeat_del.status_code == 404





@pytest.mark.asyncio
async def test_project_deletion_removes_all_sdk_keys(async_client: AsyncClient, setup_sdk_lifecycle_data, test_session: AsyncSession):
    """Verifies that soft-deleting a project permanently deletes all its active SDK keys from DB."""
    data = setup_sdk_lifecycle_data
    headers_1 = {"Authorization": f"Bearer {data['token_1']}"}
    proj_1_id = data["proj_1"].id
    key_repo = ApiKeyRepository(test_session)

    # Create Key
    resp = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Key to be deleted with project"},
        headers=headers_1
    )
    key_id = uuid.UUID(resp.json()["data"]["id"])
    raw_key = resp.json()["data"]["raw_key"]

    # Delete Project
    del_proj_resp = await async_client.delete(f"/api/v1/projects/{proj_1_id}", headers=headers_1)
    assert del_proj_resp.status_code == 200

    # Direct DB verification: API key row is permanently removed
    test_session.expire_all()
    key_after = await key_repo.get_by_id(key_id, include_deleted=True)
    assert key_after is None

    # Ingestion with key should fail after project deletion -> 401
    payload = {
        "service_name": "payment-service",
        "environment": "production",
        "logs": [{"timestamp": "2026-08-26T12:00:00Z", "level": "INFO", "message": "Test deleted project key"}],
        "exceptions": [],
        "traces": [],
        "metrics": [],
        "deployments": []
    }
    ingest_resp = await async_client.post("/api/v1/sdk/ingest", json=payload, headers={"X-API-Key": raw_key})
    assert ingest_resp.status_code == 401



@pytest.mark.asyncio
async def test_cross_org_key_generation_denied(async_client: AsyncClient, setup_sdk_lifecycle_data):
    """Verifies that User 2 cannot generate or view keys for User 1's project."""
    data = setup_sdk_lifecycle_data
    headers_2 = {"Authorization": f"Bearer {data['token_2']}"}
    proj_1_id = data["proj_1"].id

    # List keys -> 404
    resp = await async_client.get(f"/api/v1/projects/{proj_1_id}/api-keys", headers=headers_2)
    assert resp.status_code == 404

    # Create key -> 404
    resp = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Hacker Key"},
        headers=headers_2
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_authorized_user_can_reveal_active_key(async_client: AsyncClient, setup_sdk_lifecycle_data):
    """Verifies that an authorized project user can reveal the decrypted raw SDK key."""
    data = setup_sdk_lifecycle_data
    headers_1 = {"Authorization": f"Bearer {data['token_1']}"}
    proj_1_id = data["proj_1"].id

    # 1. Generate new key
    gen_resp = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Revealable Key"},
        headers=headers_1
    )
    assert gen_resp.status_code == 201
    key_id = gen_resp.json()["data"]["id"]
    original_raw_key = gen_resp.json()["data"]["raw_key"]

    # 2. Call reveal endpoint
    reveal_resp = await async_client.get(
        f"/api/v1/projects/{proj_1_id}/api-keys/{key_id}/reveal",
        headers=headers_1
    )
    assert reveal_resp.status_code == 200
    rev_data = reveal_resp.json()["data"]
    assert rev_data["id"] == key_id
    assert rev_data["raw_key"] == original_raw_key

    # 3. Verify revealed raw key can authenticate telemetry ingestion
    payload = {
        "service_name": "auth-service",
        "environment": "production",
        "logs": [{"timestamp": "2026-08-26T12:00:00Z", "level": "INFO", "message": "Post reveal test"}],
        "exceptions": [],
        "traces": [],
        "metrics": [],
        "deployments": []
    }
    ingest_resp = await async_client.post("/api/v1/sdk/ingest", json=payload, headers={"X-API-Key": rev_data["raw_key"]})
    assert ingest_resp.status_code == 202


@pytest.mark.asyncio
async def test_cross_org_and_cross_project_reveal_denied(async_client: AsyncClient, setup_sdk_lifecycle_data):
    """Verifies that cross-org and cross-project key reveal attempts are denied."""
    data = setup_sdk_lifecycle_data
    headers_1 = {"Authorization": f"Bearer {data['token_1']}"}
    headers_2 = {"Authorization": f"Bearer {data['token_2']}"}
    proj_1_id = data["proj_1"].id
    proj_2_id = data["proj_2"].id

    # User 1 creates key in Project 1
    gen_resp = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Proj 1 Key"},
        headers=headers_1
    )
    key_1_id = gen_resp.json()["data"]["id"]

    # User 2 (Org 2) attempts to reveal Key 1 -> 404
    resp_cross_org = await async_client.get(
        f"/api/v1/projects/{proj_1_id}/api-keys/{key_1_id}/reveal",
        headers=headers_2
    )
    assert resp_cross_org.status_code == 404

    # User 1 attempts reveal using Project 2 ID in URL -> 404
    resp_cross_proj = await async_client.get(
        f"/api/v1/projects/{proj_2_id}/api-keys/{key_1_id}/reveal",
        headers=headers_1
    )
    assert resp_cross_proj.status_code == 404


@pytest.mark.asyncio
async def test_revoked_key_reveal_denied(async_client: AsyncClient, setup_sdk_lifecycle_data):
    """Verifies that a revoked/deleted key cannot be revealed."""
    data = setup_sdk_lifecycle_data
    headers_1 = {"Authorization": f"Bearer {data['token_1']}"}
    proj_1_id = data["proj_1"].id

    gen_resp = await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Temporary Key"},
        headers=headers_1
    )
    key_id = gen_resp.json()["data"]["id"]

    # Revoke key
    await async_client.delete(f"/api/v1/projects/{proj_1_id}/api-keys/{key_id}", headers=headers_1)

    # Attempt to reveal -> 404 or 422
    reveal_resp = await async_client.get(
        f"/api/v1/projects/{proj_1_id}/api-keys/{key_id}/reveal",
        headers=headers_1
    )
    assert reveal_resp.status_code in (400, 404, 422)


@pytest.mark.asyncio
async def test_legacy_key_reveal_returns_warning(async_client: AsyncClient, setup_sdk_lifecycle_data, test_session: AsyncSession):
    """Verifies that legacy keys without encrypted_key return an unrecoverable legacy key warning."""
    data = setup_sdk_lifecycle_data
    headers_1 = {"Authorization": f"Bearer {data['token_1']}"}
    proj_1_id = data["proj_1"].id

    # Manually insert legacy ApiKey directly into DB (encrypted_key=None)
    raw_legacy, hashed_legacy = generate_api_key(environment="production")
    key_repo = ApiKeyRepository(test_session)
    legacy_key = await key_repo.create(ApiKey(
        project_id=proj_1_id,
        name="Legacy Key",
        key_hash=hashed_legacy,
        encrypted_key=None,
        prefix=raw_legacy[:12],
        environment="production",
        is_active=True
    ))
    await test_session.commit()

    # Attempt reveal -> error status with legacy key message
    reveal_resp = await async_client.get(
        f"/api/v1/projects/{proj_1_id}/api-keys/{legacy_key.id}/reveal",
        headers=headers_1
    )
    assert reveal_resp.status_code in (400, 422)
    assert "created before secure key recovery was enabled" in reveal_resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_list_api_keys_never_returns_encrypted_or_raw_key(async_client: AsyncClient, setup_sdk_lifecycle_data):
    """Verifies that GET /api/v1/projects/{project_id}/api-keys never exposes encrypted_key or raw_key."""
    data = setup_sdk_lifecycle_data
    headers_1 = {"Authorization": f"Bearer {data['token_1']}"}
    proj_1_id = data["proj_1"].id

    await async_client.post(
        f"/api/v1/projects/{proj_1_id}/api-keys",
        json={"name": "Listed Key"},
        headers=headers_1
    )

    list_resp = await async_client.get(f"/api/v1/projects/{proj_1_id}/api-keys", headers=headers_1)
    assert list_resp.status_code == 200
    keys = list_resp.json()["data"]
    assert len(keys) == 1
    key_dict = keys[0]
    assert "encrypted_key" not in key_dict
    assert key_dict.get("raw_key") is None

