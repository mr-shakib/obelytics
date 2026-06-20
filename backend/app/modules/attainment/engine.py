"""
Attainment Engine — computes CO and PO attainment for a section offering.

Called after ResultPublication transitions to PUBLISHED status.
Does NOT call session.commit() — caller is responsible for committing.
"""
import uuid
from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment.models import (
    Assessment,
    AssessmentCOWeight,
    StudentEnrollment,
    StudentMark,
)
from app.modules.attainment.models import COAttainmentResult, POAttainmentResult
from app.modules.attainment.repository import (
    COAttainmentResultRepository,
    POAttainmentResultRepository,
)
from app.modules.curriculum.models import SectionOffering
from app.modules.obe.models import COPOMappingEntry, COPOMappingSet


class AttainmentEngine:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._co_repo = COAttainmentResultRepository(session)
        self._po_repo = POAttainmentResultRepository(session)

    async def compute_for_section_offering(
        self, section_offering_id: UUID, org_id: UUID
    ) -> None:
        """
        Full attainment computation for a section offering.
        Called after ResultPublication is PUBLISHED.
        """
        # 1. Load section offering to get course_id, curriculum_id
        so_result = await self._session.execute(
            select(SectionOffering).where(SectionOffering.id == section_offering_id)
        )
        section_offering = so_result.scalar_one_or_none()
        if section_offering is None:
            return

        curriculum_id = section_offering.curriculum_id
        course_id = section_offering.course_id

        # 2. Load attainment thresholds from the curriculum (set by the Program
        #    Coordinator), falling back to 50/50 if the curriculum is missing.
        threshold_co_score_pct, threshold_student_pct = await self._load_thresholds(curriculum_id)

        # 3. Load LOCKED assessments for this offering
        assessments_result = await self._session.execute(
            select(Assessment).where(
                and_(
                    Assessment.section_offering_id == section_offering_id,
                    Assessment.status == "LOCKED",
                )
            )
        )
        assessments = list(assessments_result.scalars().all())
        if not assessments:
            return

        assessment_ids = [a.id for a in assessments]
        assessment_map = {a.id: a for a in assessments}

        # 4. Load ACTIVE enrollments for this offering
        enrollments_result = await self._session.execute(
            select(StudentEnrollment).where(
                and_(
                    StudentEnrollment.section_offering_id == section_offering_id,
                    StudentEnrollment.status == "ACTIVE",
                )
            )
        )
        enrollments = list(enrollments_result.scalars().all())
        if not enrollments:
            return

        enrollment_ids = [e.id for e in enrollments]

        # 5. Load all CO weights for these assessments
        co_weights_result = await self._session.execute(
            select(AssessmentCOWeight).where(
                AssessmentCOWeight.assessment_id.in_(assessment_ids)
            )
        )
        co_weights = list(co_weights_result.scalars().all())

        # Build: assessment_id -> list of CO weights
        assessment_co_weights: dict[UUID, list[AssessmentCOWeight]] = defaultdict(list)
        for w in co_weights:
            assessment_co_weights[w.assessment_id].append(w)

        # Collect all CO ids that appear in weights
        all_co_ids = {w.course_outcome_id for w in co_weights}

        # 6. Load all marks for these assessments
        marks_result = await self._session.execute(
            select(StudentMark).where(
                and_(
                    StudentMark.assessment_id.in_(assessment_ids),
                    StudentMark.student_enrollment_id.in_(enrollment_ids),
                )
            )
        )
        marks = list(marks_result.scalars().all())

        # Build: (assessment_id, enrollment_id) -> StudentMark
        mark_map: dict[tuple[UUID, UUID], StudentMark] = {}
        for m in marks:
            mark_map[(m.assessment_id, m.student_enrollment_id)] = m

        # 7. Per-student CO attainment computation
        # student_co_scores[enrollment_id][co_id] = weighted score (0-100 scale)
        student_co_scores: dict[UUID, dict[UUID, Decimal]] = {
            e.id: defaultdict(Decimal) for e in enrollments
        }

        for assessment in assessments:
            weights_for_assessment = assessment_co_weights.get(assessment.id, [])
            if not weights_for_assessment:
                continue

            total_marks = Decimal(str(assessment.total_marks))
            weightage_pct = Decimal(str(assessment.weightage_percent)) / Decimal("100")

            for enrollment in enrollments:
                mark = mark_map.get((assessment.id, enrollment.id))

                if mark is None:
                    score_pct = Decimal("0")
                elif mark.is_absent:
                    score_pct = Decimal("0")
                else:
                    if total_marks > 0:
                        score_pct = Decimal(str(mark.marks_obtained)) / total_marks * Decimal("100")
                    else:
                        score_pct = Decimal("0")

                for co_weight in weights_for_assessment:
                    contribution = Decimal(str(co_weight.contribution_percent)) / Decimal("100")
                    student_co_scores[enrollment.id][co_weight.course_outcome_id] += (
                        score_pct * contribution * weightage_pct
                    )

        total_students = len(enrollments)

        # Upsert COAttainmentResult for each CO
        co_avg_attainment: dict[UUID, Decimal] = {}

        for co_id in all_co_ids:
            student_scores = [
                student_co_scores[e.id][co_id] for e in enrollments
            ]
            avg = sum(student_scores) / total_students if total_students > 0 else Decimal("0")
            above_threshold = sum(
                1 for s in student_scores if s >= threshold_co_score_pct
            )
            is_attained = (
                Decimal(str(above_threshold)) / Decimal(str(total_students)) * Decimal("100")
                >= threshold_student_pct
            ) if total_students > 0 else False

            co_avg_attainment[co_id] = avg

            co_result = COAttainmentResult(
                id=uuid.uuid4(),
                organization_id=org_id,
                section_offering_id=section_offering_id,
                course_outcome_id=co_id,
                average_attainment_pct=round(avg, 2),
                students_above_threshold=above_threshold,
                total_students=total_students,
                is_attained=is_attained,
            )
            await self._co_repo.upsert(co_result)

        # 8. Load CO-PO mappings for (curriculum_id, course_id)
        mapping_set_result = await self._session.execute(
            select(COPOMappingSet).where(
                and_(
                    COPOMappingSet.curriculum_id == curriculum_id,
                    COPOMappingSet.course_id == course_id,
                )
            )
        )
        mapping_set = mapping_set_result.scalar_one_or_none()
        if mapping_set is None:
            return

        # Load mapping entries where CO is in the computed COs
        entries_result = await self._session.execute(
            select(COPOMappingEntry).where(
                and_(
                    COPOMappingEntry.mapping_set_id == mapping_set.id,
                    COPOMappingEntry.course_outcome_id.in_(all_co_ids),
                )
            )
        )
        mapping_entries = list(entries_result.scalars().all())
        if not mapping_entries:
            return

        # 9. Group entries by PO
        po_entries: dict[UUID, list[COPOMappingEntry]] = defaultdict(list)
        for entry in mapping_entries:
            po_entries[entry.program_outcome_id].append(entry)

        for po_id, entries in po_entries.items():
            weighted_sum = Decimal("0")
            weight_sum = Decimal("0")
            contributing_count = 0

            for entry in entries:
                co_id = entry.course_outcome_id
                if co_id in co_avg_attainment:
                    w = Decimal(str(entry.weight))
                    weighted_sum += co_avg_attainment[co_id] * w
                    weight_sum += w
                    contributing_count += 1

            if weight_sum > 0:
                po_attainment = weighted_sum / weight_sum
            else:
                po_attainment = Decimal("0")

            po_is_attained = po_attainment >= threshold_co_score_pct

            po_result = POAttainmentResult(
                id=uuid.uuid4(),
                organization_id=org_id,
                section_offering_id=section_offering_id,
                program_outcome_id=po_id,
                attainment_pct=round(po_attainment, 2),
                contributing_co_count=contributing_count,
                is_attained=po_is_attained,
            )
            await self._po_repo.upsert(po_result)

    async def _load_thresholds(self, curriculum_id: UUID) -> tuple[Decimal, Decimal]:
        """Attainment thresholds (CO-score %, student %) for a curriculum, set by the
        Program Coordinator. Falls back to 50/50 if the curriculum can't be found."""
        from app.modules.curriculum.models import Curriculum

        curriculum = (await self._session.execute(
            select(Curriculum).where(Curriculum.id == curriculum_id)
        )).scalar_one_or_none()

        if curriculum is not None:
            return (
                Decimal(str(curriculum.threshold_co_score_pct)),
                Decimal(str(curriculum.threshold_student_pct)),
            )

        return Decimal("50.00"), Decimal("50.00")
