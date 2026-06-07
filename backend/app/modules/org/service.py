from datetime import date, datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.org.exceptions import (
    DepartmentArchivedError,
    DepartmentNotFoundError,
    DepartmentShortNameConflictError,
    OrgNotFoundError,
    ProgramAcronymConflictError,
    ProgramArchivedError,
    ProgramNotFoundError,
)
from app.modules.org.models import Department, Program
from app.modules.org.repository import DepartmentRepository, OrgRepository, ProgramRepository
from app.modules.org.schemas import DepartmentCreate, DepartmentUpdate, OrgUpdate, ProgramCreate, ProgramUpdate


class OrgService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OrgRepository(session)

    async def get(self, org_id: UUID):
        org = await self._repo.get(org_id)
        if org is None:
            raise OrgNotFoundError()
        return org

    async def update(self, org_id: UUID, body: OrgUpdate):
        org = await self._repo.get(org_id)
        if org is None:
            raise OrgNotFoundError()
        data = body.model_dump(exclude_none=True)
        return await self._repo.update(org, data)


class DepartmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = DepartmentRepository(session)

    async def list_active(self, organization_id: UUID) -> list[Department]:
        return await self._repo.list_active(organization_id)

    async def get(self, dept_id: UUID, organization_id: UUID) -> Department:
        dept = await self._repo.get_by_id(dept_id, organization_id)
        if dept is None:
            raise DepartmentNotFoundError()
        return dept

    async def create(self, body: DepartmentCreate, organization_id: UUID) -> Department:
        existing = await self._repo.find_by_short_name(body.short_name, organization_id)
        if existing:
            raise DepartmentShortNameConflictError()
        dept = Department(
            organization_id=organization_id,
            name=body.name,
            short_name=body.short_name,
            year_established=body.year_established,
            description=body.description,
            vision=body.vision,
            mission=body.mission,
        )
        return await self._repo.create(dept)

    async def update(self, dept_id: UUID, body: DepartmentUpdate, organization_id: UUID) -> Department:
        dept = await self._repo.get_by_id(dept_id, organization_id)
        if dept is None:
            raise DepartmentNotFoundError()
        data = body.model_dump(exclude_none=True)
        if "short_name" in data and data["short_name"] != dept.short_name:
            conflict = await self._repo.find_by_short_name(data["short_name"], organization_id)
            if conflict:
                raise DepartmentShortNameConflictError()
        return await self._repo.update(dept, data)

    async def archive(self, dept_id: UUID, organization_id: UUID) -> Department:
        dept = await self._repo.get_by_id(dept_id, organization_id)
        if dept is None:
            raise DepartmentNotFoundError()
        if dept.status == "ARCHIVED":
            raise DepartmentArchivedError()
        dept.status = "ARCHIVED"
        dept.archived_at = datetime.now(timezone.utc)
        return await self._repo.update(dept, {})

    async def assign_head(self, dept_id: UUID, user_id: UUID, organization_id: UUID) -> Department:
        dept = await self._repo.get_by_id(dept_id, organization_id)
        if dept is None:
            raise DepartmentNotFoundError()
        today = date.today()
        await self._repo.close_current_head(dept_id, today)
        await self._repo.add_head_history(dept_id, user_id, today)
        return dept


class ProgramService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ProgramRepository(session)

    async def list_active(self, organization_id: UUID, department_id: UUID | None = None) -> list[Program]:
        return await self._repo.list_active(organization_id, department_id)

    async def get(self, program_id: UUID, organization_id: UUID) -> Program:
        program = await self._repo.get_by_id(program_id, organization_id)
        if program is None:
            raise ProgramNotFoundError()
        return program

    async def create(self, body: ProgramCreate, organization_id: UUID) -> Program:
        existing = await self._repo.find_by_acronym(body.acronym, organization_id)
        if existing:
            raise ProgramAcronymConflictError()
        program = Program(
            organization_id=organization_id,
            department_id=body.department_id,
            title=body.title,
            acronym=body.acronym,
            program_type=body.program_type,
            minimum_duration_semesters=body.minimum_duration_semesters,
            total_credits=body.total_credits,
            study_mode=body.study_mode,
            description=body.description,
        )
        return await self._repo.create(program)

    async def update(self, program_id: UUID, body: ProgramUpdate, organization_id: UUID) -> Program:
        program = await self._repo.get_by_id(program_id, organization_id)
        if program is None:
            raise ProgramNotFoundError()
        data = body.model_dump(exclude_none=True)
        if "acronym" in data and data["acronym"] != program.acronym:
            conflict = await self._repo.find_by_acronym(data["acronym"], organization_id)
            if conflict:
                raise ProgramAcronymConflictError()
        return await self._repo.update(program, data)

    async def archive(self, program_id: UUID, organization_id: UUID) -> Program:
        program = await self._repo.get_by_id(program_id, organization_id)
        if program is None:
            raise ProgramNotFoundError()
        if program.status == "ARCHIVED":
            raise ProgramArchivedError()
        program.status = "ARCHIVED"
        program.archived_at = datetime.now(timezone.utc)
        return await self._repo.update(program, {})
