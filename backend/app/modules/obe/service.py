from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.writer import write_audit_log
from app.modules.notification.writer import write_notification
from app.modules.obe.exceptions import (
    CONotEditableError,
    CONotFoundError,
    COStateError,
    MappingSetNotFoundError,
    MappingSetPublishedError,
    POArchivedError,
    POCodeConflictError,
    POHasActiveMappingsError,
    PONotFoundError,
    SubMappingConflictError,
    SubMappingNotApprovableError,
    SubMappingNotFoundError,
)
from app.modules.obe.models import (
    COCAMapping,
    COCPMapping,
    CODeliveryMethod,
    COKPMapping,
    COPOMappingSet,
    CourseOutcome,
    POKnowledgeProfile,
    ProgramOutcome,
)
from app.modules.obe.repository import (
    COCAMappingRepository,
    COCPMappingRepository,
    CODeliveryMethodRepository,
    COKPMappingRepository,
    CORepository,
    MappingEntryRepository,
    MappingSetRepository,
    POKnowledgeProfileRepository,
    PORepository,
)
from app.modules.obe.schemas import (
    COCAMappingCreate,
    COCPMappingCreate,
    CODeliveryMethodCreate,
    COKPMappingCreate,
    COPOMappingEntryUpsert,
    COPOMappingSetCreate,
    CourseOutcomeCreate,
    CourseOutcomeUpdate,
    ProgramOutcomeCreate,
    ProgramOutcomeUpdate,
)

_CO_PUBLISHED_LOCKED = {"PUBLISHED", "LOCKED"}
_CO_TERMINAL = {"PUBLISHED", "LOCKED"}


class POService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PORepository(session)

    async def list_active(
        self, org_id: UUID, program_id: UUID | None = None
    ) -> list[ProgramOutcome]:
        return await self._repo.list_active(org_id, program_id)

    async def get(self, po_id: UUID, org_id: UUID) -> ProgramOutcome:
        po = await self._repo.get_by_id(po_id, org_id)
        if po is None:
            raise PONotFoundError()
        return po

    async def create(self, body: ProgramOutcomeCreate, org_id: UUID) -> ProgramOutcome:
        existing = await self._repo.find_by_code(body.code, body.program_id)
        if existing:
            raise POCodeConflictError()
        po = ProgramOutcome(
            organization_id=org_id,
            program_id=body.program_id,
            bloom_domain_id=body.bloom_domain_id,
            code=body.code,
            reference=body.reference,
            statement=body.statement,
            po_type=body.po_type,
            order_index=body.order_index,
            status="ACTIVE",
        )
        result = await self._repo.create(po)
        await self._session.commit()
        return result

    async def update(
        self, po_id: UUID, body: ProgramOutcomeUpdate, org_id: UUID
    ) -> ProgramOutcome:
        po = await self._repo.get_by_id(po_id, org_id)
        if po is None:
            raise PONotFoundError()
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(po, data)
        await self._session.commit()
        return result

    async def archive(self, po_id: UUID, org_id: UUID) -> ProgramOutcome:
        po = await self._repo.get_by_id(po_id, org_id)
        if po is None:
            raise PONotFoundError()
        if po.status == "ARCHIVED":
            raise POArchivedError()
        has_entries = await self._repo.has_mapping_entries(po_id)
        if has_entries:
            raise POHasActiveMappingsError()
        po.status = "ARCHIVED"
        po.archived_at = datetime.now(timezone.utc)
        result = await self._repo.update(po, {})
        await self._session.commit()
        return result


class POKnowledgeProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = POKnowledgeProfileRepository(session)
        self._po_repo = PORepository(session)

    async def list_by_po(
        self, po_id: UUID, org_id: UUID
    ) -> list[POKnowledgeProfile]:
        po = await self._po_repo.get_by_id(po_id, org_id)
        if po is None:
            raise PONotFoundError()
        return await self._repo.list_by_po(po_id)

    async def add(
        self, po_id: UUID, kp_id: UUID, org_id: UUID
    ) -> POKnowledgeProfile:
        po = await self._po_repo.get_by_id(po_id, org_id)
        if po is None:
            raise PONotFoundError()
        existing = await self._repo.find_by_po_kp(po_id, kp_id)
        if existing:
            from app.modules.obe.exceptions import SubMappingConflictError
            raise SubMappingConflictError()
        obj = POKnowledgeProfile(
            program_outcome_id=po_id,
            knowledge_profile_id=kp_id,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def remove(self, po_id: UUID, kp_id: UUID, org_id: UUID) -> None:
        po = await self._po_repo.get_by_id(po_id, org_id)
        if po is None:
            raise PONotFoundError()
        obj = await self._repo.find_by_po_kp(po_id, kp_id)
        if obj is None:
            from app.modules.obe.exceptions import SubMappingNotFoundError
            raise SubMappingNotFoundError()
        await self._repo.delete(obj)
        await self._session.commit()


class COService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CORepository(session)

    async def list_by_curriculum_course(
        self, curriculum_id: UUID, course_id: UUID, org_id: UUID
    ) -> list[CourseOutcome]:
        return await self._repo.list_by_curriculum_course(curriculum_id, course_id)

    async def get(self, co_id: UUID, org_id: UUID) -> CourseOutcome:
        co = await self._repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        return co

    async def create(
        self, body: CourseOutcomeCreate, org_id: UUID, created_by_user_id: UUID
    ) -> CourseOutcome:
        existing = await self._repo.find_by_code(body.curriculum_id, body.course_id, body.code)
        if existing:
            from app.modules.obe.exceptions import MappingEntryConflictError
            raise MappingEntryConflictError()
        co = CourseOutcome(
            organization_id=org_id,
            curriculum_id=body.curriculum_id,
            course_id=body.course_id,
            bloom_level_id=body.bloom_level_id,
            code=body.code,
            statement=body.statement,
            status="DRAFT",
            created_by_user_id=created_by_user_id,
        )
        result = await self._repo.create(co)
        await self._session.commit()
        return result

    async def update(
        self, co_id: UUID, body: CourseOutcomeUpdate, org_id: UUID
    ) -> CourseOutcome:
        co = await self._repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status != "DRAFT":
            raise CONotEditableError()
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(co, data)
        await self._session.commit()
        return result

    async def submit(self, co_id: UUID, org_id: UUID, actor_user_id: UUID) -> CourseOutcome:
        co = await self._repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status != "DRAFT":
            raise COStateError(f"Cannot submit: CO is in status '{co.status}'")
        co.status = "SUBMITTED"
        result = await self._repo.update(co, {})
        write_audit_log(
            self._session,
            entity_type="course_outcome",
            entity_id=co_id,
            action="CO_SUBMITTED",
            org_id=org_id,
            actor_user_id=actor_user_id,
            before_status="DRAFT",
            after_status="SUBMITTED",
        )
        await self._session.commit()
        return result

    async def approve(self, co_id: UUID, org_id: UUID, actor_user_id: UUID) -> CourseOutcome:
        co = await self._repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status not in ("SUBMITTED", "UNDER_REVIEW"):
            raise COStateError(f"Cannot approve: CO is in status '{co.status}'")
        before = co.status
        co.status = "APPROVED"
        result = await self._repo.update(co, {})
        write_audit_log(
            self._session,
            entity_type="course_outcome",
            entity_id=co_id,
            action="CO_APPROVED",
            org_id=org_id,
            actor_user_id=actor_user_id,
            before_status=before,
            after_status="APPROVED",
        )
        if co.created_by_user_id:
            write_notification(
                self._session,
                org_id=org_id,
                recipient_user_id=co.created_by_user_id,
                notification_type="CO_APPROVED",
                title=f"CO {co.code} has been approved",
                body="Your course outcome has been approved and is ready for publishing.",
                entity_type="course_outcome",
                entity_id=co_id,
            )
        await self._session.commit()
        return result

    async def reject(self, co_id: UUID, org_id: UUID, actor_user_id: UUID) -> CourseOutcome:
        co = await self._repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status not in ("SUBMITTED", "UNDER_REVIEW"):
            raise COStateError(f"Cannot reject: CO is in status '{co.status}'")
        before = co.status
        co.status = "DRAFT"
        result = await self._repo.update(co, {})
        write_audit_log(
            self._session,
            entity_type="course_outcome",
            entity_id=co_id,
            action="CO_REJECTED",
            org_id=org_id,
            actor_user_id=actor_user_id,
            before_status=before,
            after_status="DRAFT",
        )
        if co.created_by_user_id:
            write_notification(
                self._session,
                org_id=org_id,
                recipient_user_id=co.created_by_user_id,
                notification_type="CO_REJECTED",
                title=f"CO {co.code} has been rejected",
                body="Your course outcome was rejected and returned to DRAFT.",
                entity_type="course_outcome",
                entity_id=co_id,
            )
        await self._session.commit()
        return result

    async def publish(self, co_id: UUID, org_id: UUID, actor_user_id: UUID) -> CourseOutcome:
        co = await self._repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status != "APPROVED":
            raise COStateError(f"Cannot publish: CO is in status '{co.status}'")
        co.status = "PUBLISHED"
        result = await self._repo.update(co, {})
        write_audit_log(
            self._session,
            entity_type="course_outcome",
            entity_id=co_id,
            action="CO_PUBLISHED",
            org_id=org_id,
            actor_user_id=actor_user_id,
            before_status="APPROVED",
            after_status="PUBLISHED",
        )
        await self._session.commit()
        return result

    async def lock(self, co_id: UUID, org_id: UUID, actor_user_id: UUID) -> CourseOutcome:
        co = await self._repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status != "PUBLISHED":
            raise COStateError(f"Cannot lock: CO is in status '{co.status}'")
        co.status = "LOCKED"
        co.locked_at = datetime.now(timezone.utc)
        result = await self._repo.update(co, {})
        write_audit_log(
            self._session,
            entity_type="course_outcome",
            entity_id=co_id,
            action="CO_LOCKED",
            org_id=org_id,
            actor_user_id=actor_user_id,
            before_status="PUBLISHED",
            after_status="LOCKED",
        )
        await self._session.commit()
        return result


class CODeliveryMethodService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CODeliveryMethodRepository(session)
        self._co_repo = CORepository(session)

    async def list_by_co(self, co_id: UUID, org_id: UUID) -> list[CODeliveryMethod]:
        co = await self._co_repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        return await self._repo.list_by_co(co_id)

    async def add(
        self, co_id: UUID, dm_id: UUID, org_id: UUID
    ) -> CODeliveryMethod:
        co = await self._co_repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status in _CO_PUBLISHED_LOCKED:
            raise CONotEditableError()
        existing = await self._repo.find_by_co_dm(co_id, dm_id)
        if existing:
            raise SubMappingConflictError()
        obj = CODeliveryMethod(
            course_outcome_id=co_id,
            delivery_method_id=dm_id,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def remove(self, co_id: UUID, dm_id: UUID, org_id: UUID) -> None:
        co = await self._co_repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status in _CO_PUBLISHED_LOCKED:
            raise CONotEditableError()
        obj = await self._repo.find_by_co_dm(co_id, dm_id)
        if obj is None:
            raise SubMappingNotFoundError()
        await self._repo.delete(obj)
        await self._session.commit()


class MappingSetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MappingSetRepository(session)
        self._entry_repo = MappingEntryRepository(session)

    async def get_or_create(
        self, curriculum_id: UUID, course_id: UUID, org_id: UUID, user_id: UUID
    ) -> COPOMappingSet:
        existing = await self._repo.find_by_curriculum_course(curriculum_id, course_id)
        if existing:
            await self._session.commit()
            return existing
        obj = COPOMappingSet(
            organization_id=org_id,
            curriculum_id=curriculum_id,
            course_id=course_id,
            status="DRAFT",
            created_by_user_id=user_id,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def get(self, set_id: UUID, org_id: UUID) -> COPOMappingSet:
        ms = await self._repo.get_by_id(set_id, org_id)
        if ms is None:
            raise MappingSetNotFoundError()
        return ms

    async def upsert_entries(
        self,
        set_id: UUID,
        entries: list[COPOMappingEntryUpsert],
        org_id: UUID,
    ) -> list:
        ms = await self._repo.get_by_id(set_id, org_id)
        if ms is None:
            raise MappingSetNotFoundError()
        if ms.status == "PUBLISHED":
            raise MappingSetPublishedError()
        await self._entry_repo.delete_by_set(set_id)
        results = []
        for e in entries:
            entry = await self._entry_repo.upsert(
                set_id, e.course_outcome_id, e.program_outcome_id, e.weight
            )
            results.append(entry)
        await self._session.commit()
        return results

    async def publish(
        self, set_id: UUID, org_id: UUID, user_id: UUID
    ) -> COPOMappingSet:
        ms = await self._repo.get_by_id(set_id, org_id)
        if ms is None:
            raise MappingSetNotFoundError()
        if ms.status == "PUBLISHED":
            raise MappingSetPublishedError()
        ms.status = "PUBLISHED"
        ms.published_at = datetime.now(timezone.utc)
        result = await self._repo.update(ms, {})
        await self._session.commit()
        return result


class COCPMappingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = COCPMappingRepository(session)
        self._co_repo = CORepository(session)

    async def list_by_co(self, co_id: UUID, org_id: UUID) -> list[COCPMapping]:
        co = await self._co_repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        return await self._repo.list_by_co(co_id)

    async def create(
        self, body: COCPMappingCreate, org_id: UUID, user_id: UUID
    ) -> COCPMapping:
        co = await self._co_repo.get_by_id(body.course_outcome_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status in _CO_PUBLISHED_LOCKED:
            raise CONotEditableError()
        existing = await self._repo.find_by_co_cp(body.course_outcome_id, body.complex_problem_id)
        if existing:
            raise SubMappingConflictError()
        obj = COCPMapping(
            organization_id=org_id,
            course_outcome_id=body.course_outcome_id,
            complex_problem_id=body.complex_problem_id,
            status="DRAFT",
            created_by_user_id=user_id,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def approve(
        self, mapping_id: UUID, org_id: UUID, user_id: UUID
    ) -> COCPMapping:
        obj = await self._repo.get_by_id(mapping_id)
        if obj is None or obj.organization_id != org_id:
            raise SubMappingNotFoundError()
        co = await self._co_repo.get_by_id(obj.course_outcome_id, org_id)
        if co is None or co.status in _CO_PUBLISHED_LOCKED:
            raise SubMappingNotApprovableError()
        obj.status = "APPROVED"
        obj.approved_by_user_id = user_id
        obj.approved_at = datetime.now(timezone.utc)
        result = await self._repo.update(obj, {})
        await self._session.commit()
        return result

    async def remove(self, mapping_id: UUID, org_id: UUID) -> None:
        obj = await self._repo.get_by_id(mapping_id)
        if obj is None or obj.organization_id != org_id:
            raise SubMappingNotFoundError()
        co = await self._co_repo.get_by_id(obj.course_outcome_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status in _CO_PUBLISHED_LOCKED:
            raise CONotEditableError()
        await self._session.delete(obj)
        await self._session.commit()


class COCAMappingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = COCAMappingRepository(session)
        self._co_repo = CORepository(session)

    async def list_by_co(self, co_id: UUID, org_id: UUID) -> list[COCAMapping]:
        co = await self._co_repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        return await self._repo.list_by_co(co_id)

    async def create(
        self, body: COCAMappingCreate, org_id: UUID, user_id: UUID
    ) -> COCAMapping:
        co = await self._co_repo.get_by_id(body.course_outcome_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status in _CO_PUBLISHED_LOCKED:
            raise CONotEditableError()
        existing = await self._repo.find_by_co_ca(body.course_outcome_id, body.complex_activity_id)
        if existing:
            raise SubMappingConflictError()
        obj = COCAMapping(
            organization_id=org_id,
            course_outcome_id=body.course_outcome_id,
            complex_activity_id=body.complex_activity_id,
            status="DRAFT",
            created_by_user_id=user_id,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def approve(
        self, mapping_id: UUID, org_id: UUID, user_id: UUID
    ) -> COCAMapping:
        obj = await self._repo.get_by_id(mapping_id)
        if obj is None or obj.organization_id != org_id:
            raise SubMappingNotFoundError()
        co = await self._co_repo.get_by_id(obj.course_outcome_id, org_id)
        if co is None or co.status in _CO_PUBLISHED_LOCKED:
            raise SubMappingNotApprovableError()
        obj.status = "APPROVED"
        obj.approved_by_user_id = user_id
        obj.approved_at = datetime.now(timezone.utc)
        result = await self._repo.update(obj, {})
        await self._session.commit()
        return result

    async def remove(self, mapping_id: UUID, org_id: UUID) -> None:
        obj = await self._repo.get_by_id(mapping_id)
        if obj is None or obj.organization_id != org_id:
            raise SubMappingNotFoundError()
        co = await self._co_repo.get_by_id(obj.course_outcome_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status in _CO_PUBLISHED_LOCKED:
            raise CONotEditableError()
        await self._session.delete(obj)
        await self._session.commit()


class COKPMappingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = COKPMappingRepository(session)
        self._co_repo = CORepository(session)

    async def list_by_co(self, co_id: UUID, org_id: UUID) -> list[COKPMapping]:
        co = await self._co_repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        return await self._repo.list_by_co(co_id)

    async def create(
        self, body: COKPMappingCreate, org_id: UUID, user_id: UUID
    ) -> COKPMapping:
        co = await self._co_repo.get_by_id(body.course_outcome_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status in _CO_PUBLISHED_LOCKED:
            raise CONotEditableError()
        existing = await self._repo.find_by_co_kp(body.course_outcome_id, body.knowledge_profile_id)
        if existing:
            raise SubMappingConflictError()
        obj = COKPMapping(
            organization_id=org_id,
            course_outcome_id=body.course_outcome_id,
            knowledge_profile_id=body.knowledge_profile_id,
            status="DRAFT",
            created_by_user_id=user_id,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def approve(
        self, mapping_id: UUID, org_id: UUID, user_id: UUID
    ) -> COKPMapping:
        obj = await self._repo.get_by_id(mapping_id)
        if obj is None or obj.organization_id != org_id:
            raise SubMappingNotFoundError()
        co = await self._co_repo.get_by_id(obj.course_outcome_id, org_id)
        if co is None or co.status in _CO_PUBLISHED_LOCKED:
            raise SubMappingNotApprovableError()
        obj.status = "APPROVED"
        obj.approved_by_user_id = user_id
        obj.approved_at = datetime.now(timezone.utc)
        result = await self._repo.update(obj, {})
        await self._session.commit()
        return result

    async def remove(self, mapping_id: UUID, org_id: UUID) -> None:
        obj = await self._repo.get_by_id(mapping_id)
        if obj is None or obj.organization_id != org_id:
            raise SubMappingNotFoundError()
        co = await self._co_repo.get_by_id(obj.course_outcome_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status in _CO_PUBLISHED_LOCKED:
            raise CONotEditableError()
        await self._session.delete(obj)
        await self._session.commit()
