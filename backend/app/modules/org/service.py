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
        self._session = session
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
        result = await self._repo.create(program)
        await self._seed_pos_from_types(result.id, organization_id)
        await self._upsert_attainment_config(
            result.id, organization_id,
            body.threshold_co_score_pct, body.threshold_student_pct,
        )
        return result

    async def _seed_pos_from_types(self, program_id: UUID, organization_id: UUID) -> None:
        from sqlalchemy import and_, select
        from app.modules.ref_data.models import POType
        from app.modules.obe.models import ProgramOutcome

        po_types_result = await self._session.execute(
            select(POType)
            .where(and_(POType.organization_id == organization_id, POType.is_active.is_(True)))
            .order_by(POType.created_at)
        )
        po_types = list(po_types_result.scalars().all())

        for i, pt in enumerate(po_types, start=1):
            statement = pt.description or pt.name
            self._session.add(ProgramOutcome(
                organization_id=organization_id,
                program_id=program_id,
                code=f"PO{i}",
                statement=statement,
                po_type=pt.name,
                order_index=i - 1,
            ))
        if po_types:
            await self._session.flush()

    async def update(self, program_id: UUID, body: ProgramUpdate, organization_id: UUID) -> Program:
        program = await self._repo.get_by_id(program_id, organization_id)
        if program is None:
            raise ProgramNotFoundError()
        data = body.model_dump(exclude_none=True)
        data.pop("threshold_co_score_pct", None)
        data.pop("threshold_student_pct", None)
        if "acronym" in data and data["acronym"] != program.acronym:
            conflict = await self._repo.find_by_acronym(data["acronym"], organization_id)
            if conflict:
                raise ProgramAcronymConflictError()
        if body.threshold_co_score_pct is not None or body.threshold_student_pct is not None:
            await self._upsert_attainment_config(
                program_id, organization_id,
                body.threshold_co_score_pct, body.threshold_student_pct,
            )
        return await self._repo.update(program, data)

    async def _upsert_attainment_config(
        self, program_id: UUID, org_id: UUID,
        co_pct: float | None, student_pct: float | None,
    ) -> None:
        from app.modules.attainment.models import AttainmentConfig
        from sqlalchemy import and_, select

        result = await self._session.execute(
            select(AttainmentConfig).where(
                and_(AttainmentConfig.organization_id == org_id, AttainmentConfig.program_id == program_id)
            )
        )
        config = result.scalar_one_or_none()
        if config is None:
            config = AttainmentConfig(
                organization_id=org_id,
                program_id=program_id,
                threshold_co_score_pct=co_pct if co_pct is not None else 50.0,
                threshold_student_pct=student_pct if student_pct is not None else 50.0,
            )
            self._session.add(config)
        else:
            if co_pct is not None:
                config.threshold_co_score_pct = co_pct
            if student_pct is not None:
                config.threshold_student_pct = student_pct
        await self._session.flush()

    async def archive(self, program_id: UUID, organization_id: UUID) -> Program:
        program = await self._repo.get_by_id(program_id, organization_id)
        if program is None:
            raise ProgramNotFoundError()
        if program.status == "ARCHIVED":
            raise ProgramArchivedError()
        program.status = "ARCHIVED"
        program.archived_at = datetime.now(timezone.utc)
        return await self._repo.update(program, {})
