from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from app.shared.repository.base import BaseRepository
from app.modules.iam.models import Role, Permission, User, UserRoleAssignment


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def find_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User)
            .options(joinedload(User.credential))
            .where(User.email == email.lower())
        )
        return result.unique().scalar_one_or_none()

    async def find_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(
            select(User)
            .options(joinedload(User.credential))
            .where(User.id == user_id)
        )
        return result.unique().scalar_one_or_none()

    async def list_by_org(self, organization_id: UUID, include_inactive: bool = False):
        stmt = select(User).where(User.organization_id == organization_id)
        if include_inactive:
            # show ACTIVE + DEACTIVATED, hide DELETED
            stmt = stmt.where(User.status != "DELETED")
        else:
            stmt = stmt.where(User.status == "ACTIVE")
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_active_faculty(self, organization_id: UUID):
        stmt = select(User).where(
            and_(
                User.organization_id == organization_id,
                User.status == "ACTIVE",
                User.faculty_type.is_not(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_active_role_assignments(self, user_id: UUID) -> list[UserRoleAssignment]:
        result = await self._session.execute(
            select(UserRoleAssignment)
            .options(
                selectinload(UserRoleAssignment.role).selectinload(Role.permissions)
            )
            .where(
                and_(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.removed_at.is_(None),
                )
            )
        )
        return list(result.scalars().all())
