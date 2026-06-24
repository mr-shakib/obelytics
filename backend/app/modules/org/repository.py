from datetime import date
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.org.models import Department, DepartmentHeadHistory, Organization, Program


class OrgRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, org_id: UUID) -> Organization | None:
        result = await self._session.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def update(self, org: Organization, data: dict) -> Organization:
        for key, value in data.items():
            if value is not None:
                setattr(org, key, value)
        self._session.add(org)
        await self._session.flush()
        await self._session.refresh(org)
        return org


class DepartmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self, organization_id: UUID) -> list[Department]:
        result = await self._session.execute(
            select(Department).where(
                and_(Department.organization_id == organization_id, Department.status == "ACTIVE")
            )
        )
        return list(result.scalars().all())

    async def get_by_id(self, dept_id: UUID, organization_id: UUID) -> Department | None:
        result = await self._session.execute(
            select(Department).where(
                and_(Department.id == dept_id, Department.organization_id == organization_id)
            )
        )
        return result.scalar_one_or_none()

    async def find_by_short_name(self, short_name: str, organization_id: UUID) -> Department | None:
        result = await self._session.execute(
            select(Department).where(
                and_(
                    Department.short_name == short_name,
                    Department.organization_id == organization_id,
                    Department.status == "ACTIVE",
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, dept: Department) -> Department:
        self._session.add(dept)
        await self._session.flush()
        await self._session.refresh(dept)
        return dept

    async def update(self, dept: Department, data: dict) -> Department:
        for key, value in data.items():
            if value is not None:
                setattr(dept, key, value)
        self._session.add(dept)
        await self._session.flush()
        await self._session.refresh(dept)
        return dept

    async def list_head_history(self, dept_id: UUID) -> list[DepartmentHeadHistory]:
        result = await self._session.execute(
            select(DepartmentHeadHistory)
            .where(DepartmentHeadHistory.department_id == dept_id)
            .order_by(desc(DepartmentHeadHistory.effective_from))
        )
        return list(result.scalars().all())

    async def close_current_head(self, dept_id: UUID, effective_to: date) -> None:
        result = await self._session.execute(
            select(DepartmentHeadHistory).where(
                and_(
                    DepartmentHeadHistory.department_id == dept_id,
                    DepartmentHeadHistory.effective_to.is_(None),
                )
            )
        )
        current = result.scalar_one_or_none()
        if current is not None:
            current.effective_to = effective_to
            self._session.add(current)
            await self._session.flush()

    async def add_head_history(self, dept_id: UUID, user_id: UUID, effective_from: date) -> DepartmentHeadHistory:
        entry = DepartmentHeadHistory(department_id=dept_id, user_id=user_id, effective_from=effective_from)
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry


class ProgramRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self, organization_id: UUID, department_id: UUID | None = None) -> list[Program]:
        stmt = select(Program).where(
            and_(Program.organization_id == organization_id, Program.status == "ACTIVE")
        )
        if department_id:
            stmt = stmt.where(Program.department_id == department_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, program_id: UUID, organization_id: UUID) -> Program | None:
        result = await self._session.execute(
            select(Program).where(
                and_(Program.id == program_id, Program.organization_id == organization_id)
            )
        )
        return result.scalar_one_or_none()

    async def find_by_acronym(self, acronym: str, organization_id: UUID) -> Program | None:
        result = await self._session.execute(
            select(Program).where(
                and_(
                    Program.acronym == acronym,
                    Program.organization_id == organization_id,
                    Program.status == "ACTIVE",
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, program: Program) -> Program:
        self._session.add(program)
        await self._session.flush()
        await self._session.refresh(program)
        return program

    async def update(self, program: Program, data: dict) -> Program:
        for key, value in data.items():
            if value is not None:
                setattr(program, key, value)
        self._session.add(program)
        await self._session.flush()
        await self._session.refresh(program)
        return program
