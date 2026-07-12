from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accreditation.exceptions import (
    CycleClosed,
    CriterionNotFound,
    CycleNotFound,
    DuplicatePOMapping,
    InvalidStatusTransition,
)
from app.modules.accreditation.models import (
    AccreditationCriterion,
    AccreditationCycle,
    CriterionPOMapping,
)
from app.modules.accreditation.repository import (
    AccreditationCriterionRepository,
    AccreditationCycleRepository,
    CriterionPOMappingRepository,
)
from app.modules.accreditation.schemas import (
    AccreditationCriterionCreate,
    AccreditationCriterionUpdate,
    AccreditationCycleCreate,
    AccreditationCycleUpdate,
    CriterionPOMappingCreate,
)
from app.modules.reporting.models import ReportRun
from app.modules.reporting.service import ReportRunService


class AccreditationCycleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AccreditationCycleRepository(session)

    async def create(
        self,
        body: AccreditationCycleCreate,
        org_id: UUID,
        created_by_user_id: UUID,
    ) -> AccreditationCycle:
        obj = AccreditationCycle(
            organization_id=org_id,
            program_id=body.program_id,
            name=body.name,
            body=body.body,
            start_date=body.start_date,
            end_date=body.end_date,
            status="DRAFT",
            created_by_user_id=created_by_user_id,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def list(
        self, org_id: UUID, program_id: UUID | None = None
    ) -> list[AccreditationCycle]:
        return await self._repo.list_for_org(org_id, program_id)

    async def get(self, cycle_id: UUID, org_id: UUID) -> AccreditationCycle:
        obj = await self._repo.get_by_id(cycle_id, org_id)
        if obj is None:
            raise CycleNotFound(f"Accreditation cycle {cycle_id} not found")
        return obj

    async def update(
        self, cycle_id: UUID, org_id: UUID, body: AccreditationCycleUpdate
    ) -> AccreditationCycle:
        obj = await self.get(cycle_id, org_id)
        if obj.status != "DRAFT":
            raise InvalidStatusTransition(
                "Cycle can only be updated when in DRAFT status"
            )
        data = body.model_dump(exclude_unset=True)
        result = await self._repo.update(obj, data)
        await self._session.commit()
        return result

    async def activate(self, cycle_id: UUID, org_id: UUID) -> AccreditationCycle:
        obj = await self.get(cycle_id, org_id)
        if obj.status != "DRAFT":
            raise InvalidStatusTransition(
                f"Cannot activate cycle from status '{obj.status}'. Must be DRAFT."
            )
        result = await self._repo.update(obj, {"status": "ACTIVE"})
        await self._session.commit()
        return result

    async def close(self, cycle_id: UUID, org_id: UUID) -> AccreditationCycle:
        obj = await self.get(cycle_id, org_id)
        if obj.status != "ACTIVE":
            raise InvalidStatusTransition(
                f"Cannot close cycle from status '{obj.status}'. Must be ACTIVE."
            )
        result = await self._repo.update(obj, {"status": "CLOSED"})
        await self._session.commit()
        return result

    async def prepare_report_run(self, cycle_id: UUID, org_id: UUID, user_id: UUID) -> ReportRun:
        cycle = await self.get(cycle_id, org_id)
        report_svc = ReportRunService(self._session)
        return await report_svc.create_run(
            org_id,
            user_id,
            definition_id="accreditation_ssr",
            definition_name=f"{cycle.name} — Self-Assessment Report",
            params={"cycle_id": str(cycle.id)},
        )


class AccreditationCriterionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AccreditationCriterionRepository(session)
        self._cycle_repo = AccreditationCycleRepository(session)

    async def _load_cycle(self, cycle_id: UUID, org_id: UUID) -> AccreditationCycle:
        obj = await self._cycle_repo.get_by_id(cycle_id, org_id)
        if obj is None:
            raise CycleNotFound(f"Accreditation cycle {cycle_id} not found")
        return obj

    async def add(
        self, cycle_id: UUID, org_id: UUID, body: AccreditationCriterionCreate
    ) -> AccreditationCriterion:
        cycle = await self._load_cycle(cycle_id, org_id)
        if cycle.status == "CLOSED":
            raise CycleClosed("Cannot add criteria to a closed accreditation cycle")
        obj = AccreditationCriterion(
            cycle_id=cycle_id,
            code=body.code,
            title=body.title,
            description=body.description,
            order_index=body.order_index,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def list(
        self, cycle_id: UUID, org_id: UUID
    ) -> list[AccreditationCriterion]:
        # Verify cycle belongs to org
        await self._load_cycle(cycle_id, org_id)
        return await self._repo.list_by_cycle(cycle_id)

    async def update(
        self, criterion_id: UUID, org_id: UUID, body: AccreditationCriterionUpdate
    ) -> AccreditationCriterion:
        obj = await self._repo.get_by_id(criterion_id)
        if obj is None:
            raise CriterionNotFound(f"Criterion {criterion_id} not found")
        # Verify the cycle belongs to org
        await self._load_cycle(obj.cycle_id, org_id)
        data = body.model_dump(exclude_unset=True)
        result = await self._repo.update(obj, data)
        await self._session.commit()
        return result

    async def remove(self, criterion_id: UUID, org_id: UUID) -> None:
        obj = await self._repo.get_by_id(criterion_id)
        if obj is None:
            raise CriterionNotFound(f"Criterion {criterion_id} not found")
        await self._load_cycle(obj.cycle_id, org_id)
        await self._repo.delete(obj)
        await self._session.commit()


class CriterionPOMappingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CriterionPOMappingRepository(session)
        self._criterion_repo = AccreditationCriterionRepository(session)
        self._cycle_repo = AccreditationCycleRepository(session)

    async def _load_criterion(
        self, criterion_id: UUID, org_id: UUID
    ) -> AccreditationCriterion:
        obj = await self._criterion_repo.get_by_id(criterion_id)
        if obj is None:
            raise CriterionNotFound(f"Criterion {criterion_id} not found")
        cycle = await self._cycle_repo.get_by_id(obj.cycle_id, org_id)
        if cycle is None:
            raise CriterionNotFound(f"Criterion {criterion_id} not found in your org")
        return obj

    async def map_po(
        self, criterion_id: UUID, org_id: UUID, body: CriterionPOMappingCreate
    ) -> CriterionPOMapping:
        await self._load_criterion(criterion_id, org_id)
        existing = await self._repo.find(criterion_id, body.program_outcome_id)
        if existing is not None:
            raise DuplicatePOMapping(
                f"PO {body.program_outcome_id} is already mapped to this criterion"
            )
        obj = CriterionPOMapping(
            criterion_id=criterion_id,
            program_outcome_id=body.program_outcome_id,
            notes=body.notes,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def list(
        self, criterion_id: UUID, org_id: UUID
    ) -> list[CriterionPOMapping]:
        await self._load_criterion(criterion_id, org_id)
        return await self._repo.list_by_criterion(criterion_id)

    async def unmap_po(
        self, criterion_id: UUID, program_outcome_id: UUID, org_id: UUID
    ) -> None:
        await self._load_criterion(criterion_id, org_id)
        obj = await self._repo.find(criterion_id, program_outcome_id)
        if obj is None:
            raise CriterionNotFound(
                f"PO mapping for {program_outcome_id} not found on criterion {criterion_id}"
            )
        await self._repo.delete(obj)
        await self._session.commit()
