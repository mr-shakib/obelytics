from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.shared.repository.base import BaseRepository
from app.modules.iam.models import Permission, Role, RolePermission


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Role, session)

    async def get_by_id(self, id: UUID) -> Role | None:
        result = await self._session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == id)
        )
        return result.unique().scalar_one_or_none()

    async def find_by_name(self, name: str, organization_id: UUID) -> Role | None:
        result = await self._session.execute(
            select(Role).where(
                and_(Role.name == name, Role.organization_id == organization_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(self, organization_id: UUID) -> list[Role]:
        result = await self._session.execute(
            select(Role).where(Role.organization_id == organization_id)
        )
        return list(result.scalars().all())

    async def add_permission(self, role_id: UUID, permission_id: UUID) -> None:
        self._session.add(RolePermission(role_id=role_id, permission_id=permission_id))

    async def remove_permission(self, role_id: UUID, permission_id: UUID) -> None:
        result = await self._session.execute(
            select(RolePermission).where(
                and_(
                    RolePermission.role_id == role_id,
                    RolePermission.permission_id == permission_id,
                )
            )
        )
        rp = result.scalar_one_or_none()
        if rp:
            await self._session.delete(rp)


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Permission, session)

    async def find_by_code(self, code: str) -> Permission | None:
        result = await self._session.execute(
            select(Permission).where(Permission.code == code)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Permission]:
        result = await self._session.execute(select(Permission))
        return list(result.scalars().all())
