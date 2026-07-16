import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.writer import write_audit_log
from app.modules.notification.writer import write_notification
from app.modules.obe.exceptions import (
    CONotEditableError,
    CONotFoundError,
    COStateError,
    MappingSetNotFoundError,
    MappingSetPublishedError,
    MappingSetValidationError,
    MissionArchivedError,
    MissionCodeConflictError,
    MissionNotFoundError,
    PEOArchivedError,
    PEOCodeConflictError,
    PEONotFoundError,
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
    PEOMissionMapping,
    PEOPOMapping,
    POKnowledgeProfile,
    POVersion,
    ProgramEducationalObjective,
    ProgramMission,
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
    PEOMissionMappingRepository,
    PEOPOMappingRepository,
    PEORepository,
    POKnowledgeProfileRepository,
    PORepository,
    POVersionRepository,
    ProgramMissionRepository,
)
from app.modules.obe.schemas import (
    COCAMappingCreate,
    COCPMappingCreate,
    COKPMappingCreate,
    COMappingValidationIssue,
    COPOMappingEntryUpsert,
    COPOMappingValidationResponse,
    CourseOutcomeCreate,
    CourseOutcomeResponse,
    CourseOutcomeUpdate,
    PEOCreate,
    PEOMappingSet,
    PEOMissionMappingSet,
    PEOUpdate,
    POVersionCreate,
    POVersionUpdate,
    ProgramMissionCreate,
    ProgramMissionUpdate,
    ProgramOutcomeCreate,
    ProgramOutcomeUpdate,
)

_CO_PUBLISHED_LOCKED = {"PUBLISHED", "LOCKED"}
_CO_TERMINAL = {"PUBLISHED", "LOCKED"}


class POVersionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = POVersionRepository(session)

    async def list_active(self, org_id: UUID) -> list[POVersion]:
        return await self._repo.list_active(org_id)

    async def list_all(self, org_id: UUID) -> list[POVersion]:
        return await self._repo.list_all(org_id)

    async def get(self, version_id: UUID, org_id: UUID) -> POVersion:
        version = await self._repo.get_by_id(version_id, org_id)
        if version is None:
            from app.modules.obe.exceptions import POVersionNotFoundError

            raise POVersionNotFoundError()
        return version

    async def get_with_count(self, version_id: UUID, org_id: UUID) -> dict:
        version = await self.get(version_id, org_id)
        count = await self._repo.count_pos(version.id)
        return {"version": version, "po_count": count}

    async def create(self, body: POVersionCreate, org_id: UUID) -> POVersion:
        existing = await self._repo.find_by_name(body.name, org_id)
        if existing:
            from app.modules.obe.exceptions import POVersionConflictError

            raise POVersionConflictError()
        obj = POVersion(
            organization_id=org_id,
            name=body.name,
            description=body.description,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def update(self, version_id: UUID, body: POVersionUpdate, org_id: UUID) -> POVersion:
        version = await self.get(version_id, org_id)
        data = body.model_dump(exclude_none=True)
        if "name" in data and data["name"] != version.name:
            existing = await self._repo.find_by_name(data["name"], org_id)
            if existing:
                from app.modules.obe.exceptions import POVersionConflictError

                raise POVersionConflictError()
        result = await self._repo.update(version, data)
        await self._session.commit()
        return result


class POService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PORepository(session)

    async def list_active(
        self, org_id: UUID, program_id: UUID | None = None, po_version_id: UUID | None = None
    ) -> list[ProgramOutcome]:
        return await self._repo.list_active(org_id, program_id, po_version_id)

    async def get(self, po_id: UUID, org_id: UUID) -> ProgramOutcome:
        po = await self._repo.get_by_id(po_id, org_id)
        if po is None:
            raise PONotFoundError()
        return po

    async def create(self, body: ProgramOutcomeCreate, org_id: UUID) -> ProgramOutcome:
        existing = await self._repo.find_by_code(body.code, org_id)
        if existing:
            raise POCodeConflictError()
        po = ProgramOutcome(
            organization_id=org_id,
            program_id=body.program_id,
            po_version_id=body.po_version_id,
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

    async def update(self, po_id: UUID, body: ProgramOutcomeUpdate, org_id: UUID) -> ProgramOutcome:
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

    async def list_by_po(self, po_id: UUID, org_id: UUID) -> list[POKnowledgeProfile]:
        po = await self._po_repo.get_by_id(po_id, org_id)
        if po is None:
            raise PONotFoundError()
        return await self._repo.list_by_po(po_id)

    async def add(self, po_id: UUID, kp_id: UUID, org_id: UUID) -> POKnowledgeProfile:
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

    @staticmethod
    def _to_response(co: CourseOutcome, bloom_level_ids: list[UUID]) -> CourseOutcomeResponse:
        response = CourseOutcomeResponse.model_validate(co)
        response.bloom_level_ids = bloom_level_ids
        return response

    async def list_by_curriculum_course(
        self, curriculum_id: UUID, course_id: UUID, org_id: UUID
    ) -> list[CourseOutcomeResponse]:
        cos = await self._repo.list_by_curriculum_course(curriculum_id, course_id)
        if not cos:
            cos = await self._repo.list_by_course_fallback(course_id, org_id)
        bloom_level_ids_by_co = await self._repo.get_bloom_level_ids_bulk([co.id for co in cos])
        return [self._to_response(co, bloom_level_ids_by_co.get(co.id, [])) for co in cos]

    async def get(self, co_id: UUID, org_id: UUID) -> CourseOutcomeResponse:
        co = await self._repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        bloom_level_ids = await self._repo.get_bloom_level_ids(co.id)
        return self._to_response(co, bloom_level_ids)

    async def create(
        self, body: CourseOutcomeCreate, org_id: UUID, created_by_user_id: UUID
    ) -> CourseOutcomeResponse:
        existing = await self._repo.find_by_code(body.curriculum_id, body.course_id, body.code)
        if existing:
            from app.modules.obe.exceptions import MappingEntryConflictError

            raise MappingEntryConflictError()
        co = CourseOutcome(
            organization_id=org_id,
            curriculum_id=body.curriculum_id,
            course_id=body.course_id,
            code=body.code,
            statement=body.statement,
            status="DRAFT",
            created_by_user_id=created_by_user_id,
        )
        result = await self._repo.create(co)
        await self._repo.set_bloom_levels(result.id, body.bloom_level_ids)
        await self._session.commit()
        return self._to_response(result, body.bloom_level_ids)

    async def update(
        self, co_id: UUID, body: CourseOutcomeUpdate, org_id: UUID
    ) -> CourseOutcomeResponse:
        co = await self._repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status != "DRAFT":
            raise CONotEditableError()
        data = body.model_dump(exclude_none=True)
        bloom_level_ids = data.pop("bloom_level_ids", None)
        result = await self._repo.update(co, data)
        if bloom_level_ids is not None:
            await self._repo.set_bloom_levels(co_id, bloom_level_ids)
        else:
            bloom_level_ids = await self._repo.get_bloom_level_ids(co_id)
        await self._session.commit()
        return self._to_response(result, bloom_level_ids)

    async def submit(self, co_id: UUID, org_id: UUID, actor_user_id: UUID) -> CourseOutcomeResponse:
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
        bloom_level_ids = await self._repo.get_bloom_level_ids(co_id)
        return self._to_response(result, bloom_level_ids)

    async def approve(
        self, co_id: UUID, org_id: UUID, actor_user_id: UUID
    ) -> CourseOutcomeResponse:
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
        bloom_level_ids = await self._repo.get_bloom_level_ids(co_id)
        return self._to_response(result, bloom_level_ids)

    async def reject(self, co_id: UUID, org_id: UUID, actor_user_id: UUID) -> CourseOutcomeResponse:
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
        bloom_level_ids = await self._repo.get_bloom_level_ids(co_id)
        return self._to_response(result, bloom_level_ids)

    async def delete(self, co_id: UUID, org_id: UUID) -> None:
        co = await self._repo.get_by_id(co_id, org_id)
        if co is None:
            raise CONotFoundError()
        if co.status in _CO_PUBLISHED_LOCKED or co.status in ("APPROVED", "SUBMITTED"):
            raise CONotEditableError()
        await self._repo.delete(co)
        await self._session.commit()

    async def publish(
        self, co_id: UUID, org_id: UUID, actor_user_id: UUID
    ) -> CourseOutcomeResponse:
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
        bloom_level_ids = await self._repo.get_bloom_level_ids(co_id)
        return self._to_response(result, bloom_level_ids)

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

    async def add(self, co_id: UUID, dm_id: UUID, org_id: UUID) -> CODeliveryMethod:
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
        self._co_repo = CORepository(session)
        self._po_repo = PORepository(session)
        self._cp_repo = COCPMappingRepository(session)
        self._ca_repo = COCAMappingRepository(session)

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

    async def list_entries(self, set_id: UUID, org_id: UUID) -> list:
        ms = await self._repo.get_by_id(set_id, org_id)
        if ms is None:
            raise MappingSetNotFoundError()
        return await self._entry_repo.list_by_set(set_id)

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
                set_id,
                e.course_outcome_id,
                e.program_outcome_id,
                e.weight,
                e.justification.strip(),
            )
            results.append(entry)
        await self._session.commit()
        return results

    async def validate(self, set_id: UUID, org_id: UUID) -> COPOMappingValidationResponse:
        ms = await self._repo.get_by_id(set_id, org_id)
        if ms is None:
            raise MappingSetNotFoundError()
        entries = await self._entry_repo.list_by_set(set_id)

        # Batch-fetch all POs
        po_ids = {e.program_outcome_id for e in entries}
        po_map: dict[UUID, ProgramOutcome] = {}
        if po_ids:
            po_result = await self._session.execute(
                select(ProgramOutcome).where(ProgramOutcome.id.in_(po_ids))
            )
            po_map = {po.id: po for po in po_result.scalars().all()}

        po_codes: dict[UUID, str] = {po_id: po.code for po_id, po in po_map.items()}

        co_to_po_numbers: dict[UUID, set[int]] = {}
        for e in entries:
            match = re.fullmatch(r"PO(\d+)", po_codes.get(e.program_outcome_id, ""))
            if not match:
                continue
            co_to_po_numbers.setdefault(e.course_outcome_id, set()).add(int(match.group(1)))

        co_ids_needing_check = set()
        for co_id, po_numbers in co_to_po_numbers.items():
            needs_cep = any(1 <= n <= 7 for n in po_numbers)
            needs_cea = 10 in po_numbers
            if needs_cep or needs_cea:
                co_ids_needing_check.add(co_id)

        # Batch-fetch CEP and CEA mappings for all COs that need checking
        cep_by_co: dict[UUID, bool] = {}
        cea_by_co: dict[UUID, bool] = {}
        if co_ids_needing_check:
            cep_result = await self._session.execute(
                select(COCPMapping.course_outcome_id).where(
                    COCPMapping.course_outcome_id.in_(co_ids_needing_check)
                )
            )
            cep_co_ids = {row[0] for row in cep_result.all()}
            cea_result = await self._session.execute(
                select(COCAMapping.course_outcome_id).where(
                    COCAMapping.course_outcome_id.in_(co_ids_needing_check)
                )
            )
            cea_co_ids = {row[0] for row in cea_result.all()}
            for co_id in co_ids_needing_check:
                cep_by_co[co_id] = co_id in cep_co_ids
                cea_by_co[co_id] = co_id in cea_co_ids

        # Batch-fetch COs for issue reporting
        co_map: dict[UUID, CourseOutcome] = {}
        if co_ids_needing_check:
            co_result = await self._session.execute(
                select(CourseOutcome).where(CourseOutcome.id.in_(co_ids_needing_check))
            )
            co_map = {co.id: co for co in co_result.scalars().all()}

        issues: list[COMappingValidationIssue] = []
        for co_id, po_numbers in co_to_po_numbers.items():
            needs_cep = any(1 <= n <= 7 for n in po_numbers)
            needs_cea = 10 in po_numbers
            if not needs_cep and not needs_cea:
                continue
            missing_cep = needs_cep and not cep_by_co.get(co_id, False)
            missing_cea = needs_cea and not cea_by_co.get(co_id, False)
            if not missing_cep and not missing_cea:
                continue
            co = co_map.get(co_id)
            issues.append(
                COMappingValidationIssue(
                    course_outcome_id=co_id,
                    course_outcome_code=co.code if co else "",
                    missing_cep=missing_cep,
                    missing_cea=missing_cea,
                )
            )

        return COPOMappingValidationResponse(is_valid=not issues, issues=issues)

    async def publish(self, set_id: UUID, org_id: UUID, user_id: UUID) -> COPOMappingSet:
        ms = await self._repo.get_by_id(set_id, org_id)
        if ms is None:
            raise MappingSetNotFoundError()
        if ms.status == "PUBLISHED":
            raise MappingSetPublishedError()
        validation = await self.validate(set_id, org_id)
        if not validation.is_valid:
            raise MappingSetValidationError(
                [issue.model_dump(mode="json") for issue in validation.issues]
            )
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

    async def create(self, body: COCPMappingCreate, org_id: UUID, user_id: UUID) -> COCPMapping:
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
            justification=body.justification.strip(),
            status="DRAFT",
            created_by_user_id=user_id,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def approve(self, mapping_id: UUID, org_id: UUID, user_id: UUID) -> COCPMapping:
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

    async def create(self, body: COCAMappingCreate, org_id: UUID, user_id: UUID) -> COCAMapping:
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
            justification=body.justification.strip(),
            status="DRAFT",
            created_by_user_id=user_id,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def approve(self, mapping_id: UUID, org_id: UUID, user_id: UUID) -> COCAMapping:
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

    async def create(self, body: COKPMappingCreate, org_id: UUID, user_id: UUID) -> COKPMapping:
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
            justification=body.justification.strip(),
            status="DRAFT",
            created_by_user_id=user_id,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def approve(self, mapping_id: UUID, org_id: UUID, user_id: UUID) -> COKPMapping:
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


class ProgramMissionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProgramMissionRepository(session)

    async def list_active(self, org_id: UUID, program_id: UUID) -> list[ProgramMission]:
        return await self._repo.list_active(org_id, program_id)

    async def get(self, mission_id: UUID, org_id: UUID) -> ProgramMission:
        obj = await self._repo.get_by_id(mission_id, org_id)
        if obj is None:
            raise MissionNotFoundError()
        return obj

    async def create(self, body: ProgramMissionCreate, org_id: UUID) -> ProgramMission:
        existing = await self._repo.find_by_code(body.code, body.program_id)
        if existing:
            raise MissionCodeConflictError()
        obj = ProgramMission(
            organization_id=org_id,
            program_id=body.program_id,
            code=body.code,
            statement=body.statement,
            order_index=body.order_index,
            status="ACTIVE",
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def update(
        self, mission_id: UUID, body: ProgramMissionUpdate, org_id: UUID
    ) -> ProgramMission:
        obj = await self._repo.get_by_id(mission_id, org_id)
        if obj is None:
            raise MissionNotFoundError()
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(obj, data)
        await self._session.commit()
        return result

    async def archive(self, mission_id: UUID, org_id: UUID) -> ProgramMission:
        obj = await self._repo.get_by_id(mission_id, org_id)
        if obj is None:
            raise MissionNotFoundError()
        if obj.status == "ARCHIVED":
            raise MissionArchivedError()
        obj.status = "ARCHIVED"
        obj.archived_at = datetime.now(timezone.utc)
        result = await self._repo.update(obj, {})
        await self._session.commit()
        return result


class PEOService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PEORepository(session)
        self._po_mapping_repo = PEOPOMappingRepository(session)
        self._mission_mapping_repo = PEOMissionMappingRepository(session)

    async def list_active(
        self, org_id: UUID, program_id: UUID
    ) -> list[ProgramEducationalObjective]:
        return await self._repo.list_active(org_id, program_id)

    async def get(self, peo_id: UUID, org_id: UUID) -> ProgramEducationalObjective:
        obj = await self._repo.get_by_id(peo_id, org_id)
        if obj is None:
            raise PEONotFoundError()
        return obj

    async def create(self, body: PEOCreate, org_id: UUID) -> ProgramEducationalObjective:
        existing = await self._repo.find_by_code(body.code, body.program_id)
        if existing:
            raise PEOCodeConflictError()
        obj = ProgramEducationalObjective(
            organization_id=org_id,
            program_id=body.program_id,
            code=body.code,
            statement=body.statement,
            order_index=body.order_index,
            status="ACTIVE",
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def update(
        self, peo_id: UUID, body: PEOUpdate, org_id: UUID
    ) -> ProgramEducationalObjective:
        obj = await self._repo.get_by_id(peo_id, org_id)
        if obj is None:
            raise PEONotFoundError()
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(obj, data)
        await self._session.commit()
        return result

    async def archive(self, peo_id: UUID, org_id: UUID) -> ProgramEducationalObjective:
        obj = await self._repo.get_by_id(peo_id, org_id)
        if obj is None:
            raise PEONotFoundError()
        if obj.status == "ARCHIVED":
            raise PEOArchivedError()
        obj.status = "ARCHIVED"
        obj.archived_at = datetime.now(timezone.utc)
        result = await self._repo.update(obj, {})
        await self._session.commit()
        return result

    async def set_po_mappings(
        self, peo_id: UUID, body: PEOMappingSet, org_id: UUID
    ) -> list[PEOPOMapping]:
        obj = await self._repo.get_by_id(peo_id, org_id)
        if obj is None:
            raise PEONotFoundError()
        results = await self._po_mapping_repo.replace_for_peo(peo_id, org_id, body.po_ids)
        await self._session.commit()
        return results

    async def get_po_mappings(self, peo_id: UUID, org_id: UUID) -> list[PEOPOMapping]:
        obj = await self._repo.get_by_id(peo_id, org_id)
        if obj is None:
            raise PEONotFoundError()
        return await self._po_mapping_repo.list_by_peo(peo_id)

    async def set_mission_mappings(
        self, peo_id: UUID, body: PEOMissionMappingSet, org_id: UUID
    ) -> list[PEOMissionMapping]:
        obj = await self._repo.get_by_id(peo_id, org_id)
        if obj is None:
            raise PEONotFoundError()
        results = await self._mission_mapping_repo.replace_for_peo(peo_id, org_id, body.mission_ids)
        await self._session.commit()
        return results

    async def get_mission_mappings(self, peo_id: UUID, org_id: UUID) -> list[PEOMissionMapping]:
        obj = await self._repo.get_by_id(peo_id, org_id)
        if obj is None:
            raise PEONotFoundError()
        return await self._mission_mapping_repo.list_by_peo(peo_id)
