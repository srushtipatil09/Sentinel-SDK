import uuid
from typing import Any,List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.projects import ApiKey, Project, Service
from backend.models.users import User
from backend.repositories.project_repository import ApiKeyRepository, ProjectRepository, ServiceRepository
from backend.schemas.auth import ApiKeyCreate, ApiKeyResponse
from backend.schemas.projects import ProjectCreate
from backend.utils.exceptions import NotFoundError, ValidationException
from backend.utils.security import generate_api_key, hash_api_key, encrypt_data, decrypt_data



class ProjectService:
    async def create_project(self, session: AsyncSession, organization_id: uuid.UUID, data: ProjectCreate) -> Project:
        project_repo = ProjectRepository(session)
        slug = data.name.lower().replace(" ", "-")
        
        existing = await project_repo.get_by_org_and_slug(organization_id, slug)
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"

        project = Project(
            organization_id=organization_id,
            name=data.name,
            slug=slug,
            environment=data.environment,
            description=data.description
        )
        return await project_repo.create(project)

    async def list_projects(
        self, session: AsyncSession, organization_id: uuid.UUID, user_id: Optional[uuid.UUID] = None, role: str = "owner"
    ) -> List[Project]:
        project_repo = ProjectRepository(session)
        all_projects = list(await project_repo.find_by_organization(organization_id))

        if not user_id or role.lower() == "owner":
            return all_projects

        from sqlalchemy import select
        from backend.models.projects import ProjectMember
        stmt = select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        res = await session.execute(stmt)
        assigned_ids = set(res.scalars().all())

        if not assigned_ids:
            return all_projects

        return [p for p in all_projects if p.id in assigned_ids]

    async def create_api_key(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        data: ApiKeyCreate
    ) -> Tuple[ApiKey, str]:
        from backend.api.dependencies import verify_project_ownership
        await verify_project_ownership(session, project_id, organization_id)

        key_repo = ApiKeyRepository(session)
        existing_key = await key_repo.get_active_by_project(project_id)
        if existing_key:
            raise ValidationException("Project already has an active SDK ingestion key. Revoke or delete the existing key before generating a new one.")

        raw_key, hashed_key = generate_api_key(environment=data.environment)
        prefix = raw_key[:12]
        encrypted = encrypt_data(raw_key)

        api_key = ApiKey(
            project_id=project_id,
            name=data.name,
            key_hash=hashed_key,
            encrypted_key=encrypted,
            prefix=prefix,
            environment=data.environment,
            is_active=True
        )
        try:
            api_key = await key_repo.create(api_key)
        except Exception as exc:
            await session.rollback()
            err_str = str(exc)
            exc_type = type(exc).__name__
            if "idx_unique_active_project_api_key" in err_str or "UNIQUE constraint failed" in err_str or "IntegrityError" in exc_type:
                raise ValidationException("Project already has an active SDK ingestion key. Revoke or delete the existing key before generating a new one.")
            raise exc
        return api_key, raw_key

    async def reveal_api_key(
        self,
        session: AsyncSession,
        key_id: uuid.UUID,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        user: User
    ) -> Tuple[ApiKey, str]:
        from backend.api.dependencies import verify_api_key_ownership
        from backend.utils.logging import logger
        key = await verify_api_key_ownership(session, key_id, organization_id)

        if key.project_id != project_id:
            raise NotFoundError("API Key", key_id)

        if not key.is_active or key.is_deleted:
            raise ValidationException("Only active, non-deleted SDK API keys can be revealed.")

        if not key.encrypted_key:
            raise ValidationException("This key was created before secure key recovery was enabled. Revoke and generate a new key to enable secure viewing.")

        raw_key = decrypt_data(key.encrypted_key)

        logger.info(
            "SDK API Key revealed",
            user_id=str(user.id),
            user_email=user.email,
            project_id=str(project_id),
            key_id=str(key_id),
            action="api_key_reveal"
        )

        return key, raw_key

    async def list_api_keys(
        self, session: AsyncSession, project_id: uuid.UUID, organization_id: uuid.UUID
    ) -> List[ApiKey]:
        from backend.api.dependencies import verify_project_ownership
        await verify_project_ownership(session, project_id, organization_id)
        key_repo = ApiKeyRepository(session)
        return list(await key_repo.find_by_project(project_id))



    async def list_services(self, session: AsyncSession, project_id: uuid.UUID, organization_id: uuid.UUID) -> List[Service]:
        from backend.api.dependencies import verify_project_ownership
        await verify_project_ownership(session, project_id, organization_id)
        service_repo = ServiceRepository(session)
        return list(await service_repo.find_by_project(project_id))

    async def update_project(
        self, session: AsyncSession, project_id: uuid.UUID, organization_id: uuid.UUID, data: Any
    ) -> Project:
        from backend.api.dependencies import verify_project_ownership
        project = await verify_project_ownership(session, project_id, organization_id)

        if data.name:
            project.name = data.name
        if data.environment:
            project.environment = data.environment
        if data.description is not None:
            project.description = data.description
        if getattr(data, "logo_url", None) is not None:
            project.logo_url = data.logo_url
        if getattr(data, "settings", None) is not None:
            project.settings = data.settings

        await session.flush()
        return project

    async def delete_project(self, session: AsyncSession, project_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
        from backend.api.dependencies import verify_project_ownership
        await verify_project_ownership(session, project_id, organization_id)
        key_repo = ApiKeyRepository(session)
        await key_repo.delete_all_for_project(project_id)
        project_repo = ProjectRepository(session)
        return await project_repo.soft_delete(project_id)

    async def archive_project(self, session: AsyncSession, project_id: uuid.UUID, organization_id: uuid.UUID) -> Project:
        from datetime import datetime, timezone
        from backend.api.dependencies import verify_project_ownership
        project = await verify_project_ownership(session, project_id, organization_id)

        project.is_archived = True
        project.archived_at = datetime.now(timezone.utc)
        await session.flush()
        return project

    async def restore_project(self, session: AsyncSession, project_id: uuid.UUID, organization_id: uuid.UUID) -> Project:
        from backend.api.dependencies import verify_project_ownership
        project = await verify_project_ownership(session, project_id, organization_id)

        project.is_archived = False
        project.archived_at = None
        await session.flush()
        return project

    async def rotate_api_key(self, session: AsyncSession, key_id: uuid.UUID, organization_id: uuid.UUID) -> Tuple[ApiKey, str]:
        from backend.api.dependencies import verify_api_key_ownership
        key = await verify_api_key_ownership(session, key_id, organization_id)

        raw_key, hashed_key = generate_api_key(environment=key.environment)
        key.key_hash = hashed_key
        key.prefix = raw_key[:12]
        await session.flush()
        return key, raw_key

    async def disable_api_key(self, session: AsyncSession, key_id: uuid.UUID, organization_id: uuid.UUID) -> ApiKey:
        from backend.api.dependencies import verify_api_key_ownership
        key = await verify_api_key_ownership(session, key_id, organization_id)

        key.is_active = False
        await session.flush()
        return key

    async def delete_api_key(
        self,
        session: AsyncSession,
        key_id: uuid.UUID,
        project_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> bool:
        from backend.api.dependencies import verify_api_key_ownership
        key = await verify_api_key_ownership(session, key_id, organization_id)

        if key.project_id != project_id:
            raise NotFoundError("API Key", key_id)

        key_repo = ApiKeyRepository(session)
        success = await key_repo.delete_api_key(key_id, project_id)
        if not success:
            raise NotFoundError("API Key", key_id)
        return True






project_service = ProjectService()

