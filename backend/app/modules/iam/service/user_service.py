from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.modules.iam.exceptions import (
    RoleNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.modules.iam.models import PasswordCredential, User, UserRoleAssignment
from app.modules.iam.repository.role_repository import RoleRepository
from app.modules.iam.repository.user_repository import UserRepository
from app.modules.iam.schemas import UserCreate, UserUpdate
from app.modules.iam.service.permission_service import PermissionManifestBuilder


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._roles = RoleRepository(session)

    async def create_user(
        self, data: UserCreate, organization_id: UUID, created_by: UUID
    ) -> User:
        existing = await self._users.find_by_email(data.email)
        if existing:
            raise UserAlreadyExistsError()

        role = await self._roles.get_by_id(data.role_id)
        if role is None:
            raise RoleNotFoundError()

        user = User(
            organization_id=organization_id,
            email=data.email.lower(),
            full_name=data.full_name,
            status="ACTIVE",
        )
        self._session.add(user)
        await self._session.flush()  # get user.id

        cred = PasswordCredential(
            user_id=user.id,
            hashed_password=hash_password(data.password),
            must_change_password=True,
        )
        self._session.add(cred)

        assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=data.role_id,
            scope_type=data.scope_type,
            scope_id=data.scope_id,
            assigned_by=created_by,
        )
        self._session.add(assignment)
        await self._session.commit()
        # Refresh to populate server-default columns (created_at, updated_at)
        await self._session.refresh(user)
        return user

    async def update_user(self, user_id: UUID, data: UserUpdate) -> User:
        user = await self._users.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        if data.full_name is not None:
            user.full_name = data.full_name
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def deactivate_user(self, user_id: UUID, by: UUID) -> None:
        user = await self._users.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        user.status = "DEACTIVATED"
        self._session.add(user)
        await self._session.commit()

        builder = PermissionManifestBuilder(self._session)
        await builder.invalidate(user_id)

    async def assign_role(
        self,
        user_id: UUID,
        role_id: UUID,
        scope_type: str,
        scope_id: UUID | None,
        assigned_by: UUID,
    ) -> UserRoleAssignment:
        user = await self._users.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        role = await self._roles.get_by_id(role_id)
        if role is None:
            raise RoleNotFoundError()

        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            scope_type=scope_type,
            scope_id=scope_id,
            assigned_by=assigned_by,
        )
        self._session.add(assignment)
        await self._session.flush()
        assignment_id = assignment.id
        await self._session.commit()

        # Re-fetch with role loaded so callers can access assignment.role.name
        result = await self._session.execute(
            select(UserRoleAssignment)
            .options(selectinload(UserRoleAssignment.role))
            .where(UserRoleAssignment.id == assignment_id)
        )
        loaded = result.scalar_one()

        builder = PermissionManifestBuilder(self._session)
        await builder.invalidate(user_id)
        return loaded

    async def remove_role(self, user_id: UUID, assignment_id: UUID) -> None:
        result = await self._session.execute(
            select(UserRoleAssignment).where(
                and_(
                    UserRoleAssignment.id == assignment_id,
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.removed_at.is_(None),
                )
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            raise HTTPException(status_code=404, detail="Role assignment not found")

        assignment.removed_at = datetime.now(timezone.utc)
        self._session.add(assignment)
        await self._session.commit()

        builder = PermissionManifestBuilder(self._session)
        await builder.invalidate(user_id)
