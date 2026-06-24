from uuid import UUID

from sqlalchemy import and_, delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.obe.models import (
    COCAMapping,
    COCPMapping,
    CODeliveryMethod,
    COKPMapping,
    COPOMappingEntry,
    COPOMappingSet,
    CourseOutcome,
    CourseOutcomeBloomLevel,
    PEOMissionMapping,
    PEOPOMapping,
    POKnowledgeProfile,
    POVersion,
    ProgramEducationalObjective,
    ProgramMission,
    ProgramOutcome,
)


class POVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self, org_id: UUID) -> list[POVersion]:
        result = await self._session.execute(
            select(POVersion)
            .where(and_(POVersion.organization_id == org_id, POVersion.is_active.is_(True)))
            .order_by(POVersion.created_at)
        )
        return list(result.scalars().all())

    async def list_all(self, org_id: UUID) -> list[POVersion]:
        result = await self._session.execute(
            select(POVersion)
            .where(POVersion.organization_id == org_id)
            .order_by(POVersion.created_at)
        )
        return list(result.scalars().all())

    async def get_by_id(self, version_id: UUID, org_id: UUID) -> POVersion | None:
        result = await self._session.execute(
            select(POVersion).where(
                and_(POVersion.id == version_id, POVersion.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def find_by_name(self, name: str, org_id: UUID) -> POVersion | None:
        result = await self._session.execute(
            select(POVersion).where(
                and_(POVersion.name == name, POVersion.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def count_pos(self, version_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ProgramOutcome)
            .where(
                and_(
                    ProgramOutcome.po_version_id == version_id,
                    ProgramOutcome.status == "ACTIVE",
                )
            )
        )
        return result.scalar() or 0

    async def create(self, obj: POVersion) -> POVersion:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: POVersion, data: dict) -> POVersion:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class PORepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, po_id: UUID, org_id: UUID) -> ProgramOutcome | None:
        result = await self._session.execute(
            select(ProgramOutcome).where(
                and_(ProgramOutcome.id == po_id, ProgramOutcome.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_active(
        self, org_id: UUID, program_id: UUID | None = None, po_version_id: UUID | None = None
    ) -> list[ProgramOutcome]:
        stmt = (
            select(ProgramOutcome)
            .where(
                and_(ProgramOutcome.organization_id == org_id, ProgramOutcome.status == "ACTIVE")
            )
            .order_by(ProgramOutcome.order_index)
        )
        if program_id:
            stmt = stmt.where(ProgramOutcome.program_id == program_id)
        if po_version_id:
            stmt = stmt.where(ProgramOutcome.po_version_id == po_version_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_code(self, code: str, org_id: UUID) -> ProgramOutcome | None:
        result = await self._session.execute(
            select(ProgramOutcome).where(
                and_(
                    ProgramOutcome.code == code,
                    ProgramOutcome.organization_id == org_id,
                    ProgramOutcome.status == "ACTIVE",
                )
            )
        )
        return result.scalar_one_or_none()

    async def has_mapping_entries(self, po_id: UUID) -> bool:
        result = await self._session.execute(
            select(exists().where(COPOMappingEntry.program_outcome_id == po_id))
        )
        return bool(result.scalar())

    async def create(self, obj: ProgramOutcome) -> ProgramOutcome:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: ProgramOutcome, data: dict) -> ProgramOutcome:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class POKnowledgeProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_po(self, po_id: UUID) -> list[POKnowledgeProfile]:
        result = await self._session.execute(
            select(POKnowledgeProfile).where(POKnowledgeProfile.program_outcome_id == po_id)
        )
        return list(result.scalars().all())

    async def find_by_po_kp(self, po_id: UUID, kp_id: UUID) -> POKnowledgeProfile | None:
        result = await self._session.execute(
            select(POKnowledgeProfile).where(
                and_(
                    POKnowledgeProfile.program_outcome_id == po_id,
                    POKnowledgeProfile.knowledge_profile_id == kp_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: POKnowledgeProfile) -> POKnowledgeProfile:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def delete(self, obj: POKnowledgeProfile) -> None:
        await self._session.delete(obj)
        await self._session.flush()


class CORepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, co_id: UUID, org_id: UUID) -> CourseOutcome | None:
        result = await self._session.execute(
            select(CourseOutcome).where(
                and_(CourseOutcome.id == co_id, CourseOutcome.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_curriculum_course(
        self, curriculum_id: UUID, course_id: UUID
    ) -> list[CourseOutcome]:
        result = await self._session.execute(
            select(CourseOutcome).where(
                and_(
                    CourseOutcome.curriculum_id == curriculum_id,
                    CourseOutcome.course_id == course_id,
                )
            )
        )
        return list(result.scalars().all())

    async def list_by_course_fallback(self, course_id: UUID, org_id: UUID) -> list[CourseOutcome]:
        result = await self._session.execute(
            select(CourseOutcome)
            .where(
                and_(
                    CourseOutcome.course_id == course_id,
                    CourseOutcome.organization_id == org_id,
                )
            )
            .order_by(CourseOutcome.code)
        )
        seen_codes: set[str] = set()
        unique: list[CourseOutcome] = []
        for co in result.scalars().all():
            if co.code not in seen_codes:
                seen_codes.add(co.code)
                unique.append(co)
        return unique

    async def find_by_code(
        self, curriculum_id: UUID, course_id: UUID, code: str
    ) -> CourseOutcome | None:
        result = await self._session.execute(
            select(CourseOutcome).where(
                and_(
                    CourseOutcome.curriculum_id == curriculum_id,
                    CourseOutcome.course_id == course_id,
                    CourseOutcome.code == code,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: CourseOutcome) -> CourseOutcome:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: CourseOutcome, data: dict) -> CourseOutcome:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def delete(self, obj: CourseOutcome) -> None:
        await self._session.delete(obj)
        await self._session.flush()

    async def get_bloom_level_ids(self, co_id: UUID) -> list[UUID]:
        result = await self._session.execute(
            select(CourseOutcomeBloomLevel.bloom_level_id).where(
                CourseOutcomeBloomLevel.course_outcome_id == co_id
            )
        )
        return list(result.scalars().all())

    async def get_bloom_level_ids_bulk(self, co_ids: list[UUID]) -> dict[UUID, list[UUID]]:
        result_map: dict[UUID, list[UUID]] = {co_id: [] for co_id in co_ids}
        if not co_ids:
            return result_map
        result = await self._session.execute(
            select(
                CourseOutcomeBloomLevel.course_outcome_id,
                CourseOutcomeBloomLevel.bloom_level_id,
            ).where(CourseOutcomeBloomLevel.course_outcome_id.in_(co_ids))
        )
        for co_id, bloom_level_id in result.all():
            result_map[co_id].append(bloom_level_id)
        return result_map

    async def set_bloom_levels(self, co_id: UUID, bloom_level_ids: list[UUID]) -> None:
        await self._session.execute(
            delete(CourseOutcomeBloomLevel).where(
                CourseOutcomeBloomLevel.course_outcome_id == co_id
            )
        )
        for bloom_level_id in dict.fromkeys(bloom_level_ids):
            self._session.add(
                CourseOutcomeBloomLevel(course_outcome_id=co_id, bloom_level_id=bloom_level_id)
            )
        await self._session.flush()


class CODeliveryMethodRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_co(self, co_id: UUID) -> list[CODeliveryMethod]:
        result = await self._session.execute(
            select(CODeliveryMethod).where(CODeliveryMethod.course_outcome_id == co_id)
        )
        return list(result.scalars().all())

    async def find_by_co_dm(self, co_id: UUID, dm_id: UUID) -> CODeliveryMethod | None:
        result = await self._session.execute(
            select(CODeliveryMethod).where(
                and_(
                    CODeliveryMethod.course_outcome_id == co_id,
                    CODeliveryMethod.delivery_method_id == dm_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: CODeliveryMethod) -> CODeliveryMethod:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def delete(self, obj: CODeliveryMethod) -> None:
        await self._session.delete(obj)
        await self._session.flush()


class MappingSetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, set_id: UUID, org_id: UUID) -> COPOMappingSet | None:
        result = await self._session.execute(
            select(COPOMappingSet).where(
                and_(COPOMappingSet.id == set_id, COPOMappingSet.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def find_by_curriculum_course(
        self, curriculum_id: UUID, course_id: UUID
    ) -> COPOMappingSet | None:
        result = await self._session.execute(
            select(COPOMappingSet).where(
                and_(
                    COPOMappingSet.curriculum_id == curriculum_id,
                    COPOMappingSet.course_id == course_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def find_by_course_fallback(self, course_id: UUID) -> COPOMappingSet | None:
        result = await self._session.execute(
            select(COPOMappingSet)
            .where(COPOMappingSet.course_id == course_id)
            .order_by(COPOMappingSet.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, obj: COPOMappingSet) -> COPOMappingSet:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: COPOMappingSet, data: dict) -> COPOMappingSet:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class MappingEntryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_set(self, mapping_set_id: UUID) -> list[COPOMappingEntry]:
        result = await self._session.execute(
            select(COPOMappingEntry).where(COPOMappingEntry.mapping_set_id == mapping_set_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, entry_id: UUID) -> COPOMappingEntry | None:
        result = await self._session.execute(
            select(COPOMappingEntry).where(COPOMappingEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def find_by_set_co_po(
        self, set_id: UUID, co_id: UUID, po_id: UUID
    ) -> COPOMappingEntry | None:
        result = await self._session.execute(
            select(COPOMappingEntry).where(
                and_(
                    COPOMappingEntry.mapping_set_id == set_id,
                    COPOMappingEntry.course_outcome_id == co_id,
                    COPOMappingEntry.program_outcome_id == po_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, set_id: UUID, co_id: UUID, po_id: UUID, weight: int) -> COPOMappingEntry:
        existing = await self.find_by_set_co_po(set_id, co_id, po_id)
        if existing:
            existing.weight = weight
            self._session.add(existing)
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        entry = COPOMappingEntry(
            mapping_set_id=set_id,
            course_outcome_id=co_id,
            program_outcome_id=po_id,
            weight=weight,
        )
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    async def delete(self, obj: COPOMappingEntry) -> None:
        await self._session.delete(obj)
        await self._session.flush()

    async def delete_by_set(self, mapping_set_id: UUID) -> None:
        await self._session.execute(
            delete(COPOMappingEntry).where(COPOMappingEntry.mapping_set_id == mapping_set_id)
        )
        await self._session.flush()


class COCPMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_co(self, co_id: UUID) -> list[COCPMapping]:
        result = await self._session.execute(
            select(COCPMapping).where(COCPMapping.course_outcome_id == co_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, mapping_id: UUID) -> COCPMapping | None:
        result = await self._session.execute(
            select(COCPMapping).where(COCPMapping.id == mapping_id)
        )
        return result.scalar_one_or_none()

    async def find_by_co_cp(self, co_id: UUID, cp_id: UUID) -> COCPMapping | None:
        result = await self._session.execute(
            select(COCPMapping).where(
                and_(
                    COCPMapping.course_outcome_id == co_id,
                    COCPMapping.complex_problem_id == cp_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: COCPMapping) -> COCPMapping:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: COCPMapping, data: dict) -> COCPMapping:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class COCAMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_co(self, co_id: UUID) -> list[COCAMapping]:
        result = await self._session.execute(
            select(COCAMapping).where(COCAMapping.course_outcome_id == co_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, mapping_id: UUID) -> COCAMapping | None:
        result = await self._session.execute(
            select(COCAMapping).where(COCAMapping.id == mapping_id)
        )
        return result.scalar_one_or_none()

    async def find_by_co_ca(self, co_id: UUID, ca_id: UUID) -> COCAMapping | None:
        result = await self._session.execute(
            select(COCAMapping).where(
                and_(
                    COCAMapping.course_outcome_id == co_id,
                    COCAMapping.complex_activity_id == ca_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: COCAMapping) -> COCAMapping:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: COCAMapping, data: dict) -> COCAMapping:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class COKPMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_co(self, co_id: UUID) -> list[COKPMapping]:
        result = await self._session.execute(
            select(COKPMapping).where(COKPMapping.course_outcome_id == co_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, mapping_id: UUID) -> COKPMapping | None:
        result = await self._session.execute(
            select(COKPMapping).where(COKPMapping.id == mapping_id)
        )
        return result.scalar_one_or_none()

    async def find_by_co_kp(self, co_id: UUID, kp_id: UUID) -> COKPMapping | None:
        result = await self._session.execute(
            select(COKPMapping).where(
                and_(
                    COKPMapping.course_outcome_id == co_id,
                    COKPMapping.knowledge_profile_id == kp_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: COKPMapping) -> COKPMapping:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: COKPMapping, data: dict) -> COKPMapping:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class ProgramMissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, mission_id: UUID, org_id: UUID) -> ProgramMission | None:
        result = await self._session.execute(
            select(ProgramMission).where(
                and_(ProgramMission.id == mission_id, ProgramMission.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_active(self, org_id: UUID, program_id: UUID) -> list[ProgramMission]:
        result = await self._session.execute(
            select(ProgramMission)
            .where(
                and_(
                    ProgramMission.organization_id == org_id,
                    ProgramMission.program_id == program_id,
                    ProgramMission.status == "ACTIVE",
                )
            )
            .order_by(ProgramMission.order_index)
        )
        return list(result.scalars().all())

    async def find_by_code(self, code: str, program_id: UUID) -> ProgramMission | None:
        result = await self._session.execute(
            select(ProgramMission).where(
                and_(
                    ProgramMission.code == code,
                    ProgramMission.program_id == program_id,
                    ProgramMission.status == "ACTIVE",
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: ProgramMission) -> ProgramMission:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: ProgramMission, data: dict) -> ProgramMission:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class PEORepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, peo_id: UUID, org_id: UUID) -> ProgramEducationalObjective | None:
        result = await self._session.execute(
            select(ProgramEducationalObjective).where(
                and_(
                    ProgramEducationalObjective.id == peo_id,
                    ProgramEducationalObjective.organization_id == org_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_active(
        self, org_id: UUID, program_id: UUID
    ) -> list[ProgramEducationalObjective]:
        result = await self._session.execute(
            select(ProgramEducationalObjective)
            .where(
                and_(
                    ProgramEducationalObjective.organization_id == org_id,
                    ProgramEducationalObjective.program_id == program_id,
                    ProgramEducationalObjective.status == "ACTIVE",
                )
            )
            .order_by(ProgramEducationalObjective.order_index)
        )
        return list(result.scalars().all())

    async def find_by_code(self, code: str, program_id: UUID) -> ProgramEducationalObjective | None:
        result = await self._session.execute(
            select(ProgramEducationalObjective).where(
                and_(
                    ProgramEducationalObjective.code == code,
                    ProgramEducationalObjective.program_id == program_id,
                    ProgramEducationalObjective.status == "ACTIVE",
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: ProgramEducationalObjective) -> ProgramEducationalObjective:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(
        self, obj: ProgramEducationalObjective, data: dict
    ) -> ProgramEducationalObjective:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class PEOPOMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_peo(self, peo_id: UUID) -> list[PEOPOMapping]:
        result = await self._session.execute(
            select(PEOPOMapping).where(PEOPOMapping.peo_id == peo_id)
        )
        return list(result.scalars().all())

    async def list_by_program(self, program_id: UUID, org_id: UUID) -> list[PEOPOMapping]:
        result = await self._session.execute(
            select(PEOPOMapping)
            .join(
                ProgramEducationalObjective,
                PEOPOMapping.peo_id == ProgramEducationalObjective.id,
            )
            .where(
                and_(
                    ProgramEducationalObjective.program_id == program_id,
                    ProgramEducationalObjective.organization_id == org_id,
                )
            )
        )
        return list(result.scalars().all())

    async def replace_for_peo(
        self, peo_id: UUID, org_id: UUID, po_ids: list[UUID]
    ) -> list[PEOPOMapping]:
        await self._session.execute(delete(PEOPOMapping).where(PEOPOMapping.peo_id == peo_id))
        results = []
        for po_id in dict.fromkeys(po_ids):
            obj = PEOPOMapping(organization_id=org_id, peo_id=peo_id, program_outcome_id=po_id)
            self._session.add(obj)
            results.append(obj)
        await self._session.flush()
        for obj in results:
            await self._session.refresh(obj)
        return results


class PEOMissionMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_peo(self, peo_id: UUID) -> list[PEOMissionMapping]:
        result = await self._session.execute(
            select(PEOMissionMapping).where(PEOMissionMapping.peo_id == peo_id)
        )
        return list(result.scalars().all())

    async def list_by_program(self, program_id: UUID, org_id: UUID) -> list[PEOMissionMapping]:
        result = await self._session.execute(
            select(PEOMissionMapping)
            .join(
                ProgramEducationalObjective,
                PEOMissionMapping.peo_id == ProgramEducationalObjective.id,
            )
            .where(
                and_(
                    ProgramEducationalObjective.program_id == program_id,
                    ProgramEducationalObjective.organization_id == org_id,
                )
            )
        )
        return list(result.scalars().all())

    async def replace_for_peo(
        self, peo_id: UUID, org_id: UUID, mission_ids: list[UUID]
    ) -> list[PEOMissionMapping]:
        await self._session.execute(
            delete(PEOMissionMapping).where(PEOMissionMapping.peo_id == peo_id)
        )
        results = []
        for mission_id in dict.fromkeys(mission_ids):
            obj = PEOMissionMapping(organization_id=org_id, peo_id=peo_id, mission_id=mission_id)
            self._session.add(obj)
            results.append(obj)
        await self._session.flush()
        for obj in results:
            await self._session.refresh(obj)
        return results
