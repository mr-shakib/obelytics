import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis
from app.modules.iam.models import UserRoleAssignment
from app.modules.iam.repository.user_repository import UserRepository
from app.modules.iam.schemas import PermissionManifestResponse

MANIFEST_TTL_SECONDS = 300  # 5-minute cache, matches access token TTL window
SUPER_ADMIN_ROLE_NAME = "Super Admin"


class PermissionManifestBuilder:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def build_manifest(self, user_id: UUID) -> PermissionManifestResponse:
        redis = await get_redis()
        cache_key = f"auth:{user_id}:manifest"

        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return PermissionManifestResponse(**data)

        manifest = await self._load_manifest(user_id)
        await redis.setex(cache_key, MANIFEST_TTL_SECONDS, manifest.model_dump_json())
        return manifest

    async def invalidate(self, user_id: UUID) -> None:
        redis = await get_redis()
        await redis.delete(f"auth:{user_id}:manifest")

    async def _load_manifest(self, user_id: UUID) -> PermissionManifestResponse:
        repo = UserRepository(self._session)
        assignments: list[UserRoleAssignment] = await repo.get_active_role_assignments(user_id)

        permissions: set[str] = set()
        program_ids: set[UUID] = set()
        role_names: list[str] = []
        is_super_admin = False

        for assignment in assignments:
            role = assignment.role
            if role is None:
                continue
            role_names.append(role.name)
            if role.name == SUPER_ADMIN_ROLE_NAME:
                is_super_admin = True
            for perm in role.permissions:
                permissions.add(perm.code)
            if assignment.scope_type == "PROGRAM" and assignment.scope_id:
                program_ids.add(assignment.scope_id)

        return PermissionManifestResponse(
            user_id=user_id,
            permissions=sorted(permissions),
            program_ids=list(program_ids),
            role_names=role_names,
            is_super_admin=is_super_admin,
        )
