from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment.models import Assessment, StudentEnrollment, StudentMark
from app.modules.attainment.models import COAttainmentResult, POAttainmentResult
from app.modules.curriculum.models import Batch, Curriculum, SectionOffering
from app.modules.reporting.schemas import (
    AssessmentStatRow,
    AssessmentSummaryReport,
    COAttainmentReport,
    COAttainmentRow,
    POAttainmentRow,
    ProgramPOAttainmentReport,
    ProgramPORow,
)


class AssessmentSummaryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def generate(self, org_id: UUID, section_offering_id: UUID) -> AssessmentSummaryReport:
        # 1. Load ACTIVE enrollment count
        enroll_count = await self._session.scalar(
            select(func.count()).select_from(StudentEnrollment).where(
                and_(
                    StudentEnrollment.section_offering_id == section_offering_id,
                    StudentEnrollment.organization_id == org_id,
                    StudentEnrollment.status == "ACTIVE",
                )
            )
        )
        enroll_count = enroll_count or 0

        # 2. Load all assessments for section_offering
        assessments = (
            await self._session.execute(
                select(Assessment).where(
                    and_(
                        Assessment.section_offering_id == section_offering_id,
                        Assessment.organization_id == org_id,
                    )
                )
            )
        ).scalars().all()

        # 3. Batch-fetch all marks for these assessments
        assessment_ids = [a.id for a in assessments]
        all_marks = (
            await self._session.execute(
                select(StudentMark).where(StudentMark.assessment_id.in_(assessment_ids))
            )
        ).scalars().all()
        marks_by_assessment: dict[UUID, list[StudentMark]] = defaultdict(list)
        for m in all_marks:
            marks_by_assessment[m.assessment_id].append(m)

        # 4. Compute stats per assessment
        rows = []
        for a in assessments:
            marks = marks_by_assessment.get(a.id, [])

            marks_entered = len(marks)
            absent = sum(1 for m in marks if m.is_absent)
            scored = [
                m.marks_obtained
                for m in marks
                if not m.is_absent and m.marks_obtained is not None
            ]
            scored_count = len(scored)

            avg = (
                Decimal(str(sum(scored) / scored_count)).quantize(Decimal("0.01"))
                if scored_count > 0
                else None
            )
            max_s = max(scored) if scored else None
            min_s = min(scored) if scored else None
            threshold = Decimal(str(a.total_marks)) * Decimal("0.5")
            pass_c = sum(1 for s in scored if Decimal(str(s)) >= threshold)
            pass_rate = (
                Decimal(str(pass_c / scored_count * 100)).quantize(Decimal("0.01"))
                if scored_count > 0
                else None
            )

            rows.append(
                AssessmentStatRow(
                    assessment_id=a.id,
                    name=a.name,
                    total_marks=a.total_marks,
                    weightage_percent=a.weightage_percent,
                    status=a.status,
                    enrolled_count=enroll_count,
                    marks_entered_count=marks_entered,
                    absent_count=absent,
                    scored_count=scored_count,
                    average_score=avg,
                    max_score=max_s,
                    min_score=min_s,
                    pass_count=pass_c,
                    pass_rate=pass_rate,
                )
            )

        return AssessmentSummaryReport(
            section_offering_id=section_offering_id,
            organization_id=org_id,
            total_enrolled=enroll_count,
            assessments=rows,
        )


class COAttainmentReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def generate(self, org_id: UUID, section_offering_id: UUID) -> COAttainmentReport:
        co_results = (
            await self._session.execute(
                select(COAttainmentResult).where(
                    COAttainmentResult.section_offering_id == section_offering_id
                )
            )
        ).scalars().all()

        po_results = (
            await self._session.execute(
                select(POAttainmentResult).where(
                    POAttainmentResult.section_offering_id == section_offering_id
                )
            )
        ).scalars().all()

        return COAttainmentReport(
            section_offering_id=section_offering_id,
            co_attainments=[
                COAttainmentRow(
                    course_outcome_id=r.course_outcome_id,
                    average_attainment_pct=r.average_attainment_pct,
                    students_above_threshold=r.students_above_threshold,
                    total_students=r.total_students,
                    is_attained=r.is_attained,
                )
                for r in co_results
            ],
            po_attainments=[
                POAttainmentRow(
                    program_outcome_id=r.program_outcome_id,
                    attainment_pct=r.attainment_pct,
                    contributing_co_count=r.contributing_co_count,
                    students_above_threshold=r.students_above_threshold,
                    total_students=r.total_students,
                    is_attained=r.is_attained,
                )
                for r in po_results
            ],
        )


class ProgramPOAttainmentReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def generate(
        self, org_id: UUID, program_id: UUID, academic_term_id: UUID
    ) -> ProgramPOAttainmentReport:
        # Find all section_offerings for the program in the given academic_term
        stmt = (
            select(SectionOffering.id)
            .join(Batch, Batch.id == SectionOffering.batch_id)
            .join(Curriculum, Curriculum.id == Batch.curriculum_id)
            .where(
                and_(
                    Curriculum.program_id == program_id,
                    SectionOffering.academic_term_id == academic_term_id,
                    SectionOffering.organization_id == org_id,
                )
            )
        )
        so_ids = list((await self._session.execute(stmt)).scalars().all())

        if not so_ids:
            return ProgramPOAttainmentReport(
                program_id=program_id,
                academic_term_id=academic_term_id,
                organization_id=org_id,
                po_rows=[],
            )

        # Load all PO attainment results for those section_offerings
        po_results = (
            await self._session.execute(
                select(POAttainmentResult).where(
                    POAttainmentResult.section_offering_id.in_(so_ids)
                )
            )
        ).scalars().all()

        # Group by program_outcome_id
        grouped: dict[UUID, list] = defaultdict(list)
        for r in po_results:
            grouped[r.program_outcome_id].append(r)

        rows = []
        for po_id, entries in grouped.items():
            avg_pct = Decimal(
                str(sum(e.attainment_pct for e in entries) / len(entries))
            ).quantize(Decimal("0.01"))
            attained_count = sum(1 for e in entries if e.is_attained)
            rows.append(
                ProgramPORow(
                    program_outcome_id=po_id,
                    avg_attainment_pct=avg_pct,
                    offering_count=len(entries),
                    attained_count=attained_count,
                )
            )

        return ProgramPOAttainmentReport(
            program_id=program_id,
            academic_term_id=academic_term_id,
            organization_id=org_id,
            po_rows=rows,
        )
