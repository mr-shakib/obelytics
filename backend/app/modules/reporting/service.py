from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import anyio
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import presigned_get_url, put_object
from app.modules.accreditation.models import (
    AccreditationCriterion,
    AccreditationCycle,
    CriterionPOMapping,
)
from app.modules.assessment.models import Assessment, StudentEnrollment, StudentMark
from app.modules.attainment.models import COAttainmentResult, POAttainmentResult
from app.modules.curriculum.models import AcademicTerm, Batch, Curriculum, SectionOffering
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.obe.models import ProgramOutcome
from app.modules.org.models import Organization, Program
from app.modules.reporting.exceptions import ReportRunNotFoundError
from app.modules.reporting.models import ReportRun
from app.modules.reporting.repository import ReportRunRepository
from app.modules.reporting.schemas import (
    AssessmentStatRow,
    AssessmentSummaryReport,
    COAttainmentReport,
    COAttainmentRow,
    POAttainmentRow,
    ProgramPOAttainmentReport,
    ProgramPORow,
    ReportDefinition,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _render_report_html(template_name: str, context: dict) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    return env.get_template(template_name).render(**context)


async def _render_report_pdf(html: str) -> bytes:
    from weasyprint import HTML

    def _render():
        return HTML(string=html).write_pdf()

    return await anyio.to_thread.run_sync(_render)


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


# ── Report Runs (async report generation) ──────────────────────────────────────

REPORT_DEFINITIONS: list[dict] = [
    {
        "id": "program_po_attainment",
        "name": "Program PO Attainment Summary",
        "description": "PO attainment across every published semester, for the programs you coordinate.",
        "permission": "report.generate",
    },
]


def list_available_definitions(manifest: PermissionManifestResponse) -> list[ReportDefinition]:
    return [
        ReportDefinition(id=d["id"], name=d["name"], description=d["description"])
        for d in REPORT_DEFINITIONS
        if manifest.is_super_admin or d["permission"] in manifest.permissions
    ]


class ReportRunService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ReportRunRepository(session)

    async def create_run(
        self,
        org_id: UUID,
        user_id: UUID,
        definition_id: str,
        definition_name: str,
        params: dict | None = None,
    ) -> ReportRun:
        run = ReportRun(
            organization_id=org_id,
            definition_id=definition_id,
            definition_name=definition_name,
            requested_by_user_id=user_id,
            status="PENDING",
            params=params or {},
        )
        result = await self._repo.create(run)
        await self._session.commit()
        return result

    async def list_runs(self, org_id: UUID, user_id: UUID) -> list[ReportRun]:
        return await self._repo.list_for_user(org_id, user_id)

    async def get_run(self, run_id: UUID, org_id: UUID, user_id: UUID) -> ReportRun:
        run = await self._repo.get_by_id(run_id, org_id)
        if run is None or run.requested_by_user_id != user_id:
            raise ReportRunNotFoundError()
        return run

    async def output_url(self, run: ReportRun) -> str | None:
        if not run.output_file_key:
            return None
        return await presigned_get_url(settings.CLOUDINARY_FOLDER_REPORTS, run.output_file_key)

    # ── worker-side execution ───────────────────────────────────────────────────

    async def execute(self, run_id: UUID) -> None:
        """Runs on the arq worker. Generates the report's PDF and stores it,
        or records the failure — never raises, so the job doesn't get retried
        into a duplicate run."""
        run = await self._repo.get_by_id(run_id)
        if run is None:
            return

        await self._repo.update(run, {"status": "RUNNING"})
        await self._session.commit()

        try:
            if run.definition_id == "program_po_attainment":
                pdf_bytes, summary = await self._generate_program_po_attainment(run)
            elif run.definition_id == "accreditation_ssr":
                pdf_bytes, summary = await self._generate_accreditation_ssr(run)
            else:
                raise ValueError(f"Unknown report definition: {run.definition_id}")

            key = f"{run.organization_id}/{run.id}.pdf"
            await put_object(settings.CLOUDINARY_FOLDER_REPORTS, key, pdf_bytes, "application/pdf")

            await self._repo.update(
                run,
                {
                    "status": "DONE",
                    "output_file_key": key,
                    "summary": summary,
                    "completed_at": datetime.now(timezone.utc),
                },
            )
        except Exception as exc:  # noqa: BLE001 — report generation failures are recorded, not raised
            await self._repo.update(
                run,
                {
                    "status": "FAILED",
                    "error": str(exc),
                    "completed_at": datetime.now(timezone.utc),
                },
            )
        await self._session.commit()

    async def _org_letterhead(self, org_id: UUID) -> tuple[Organization | None, str | None]:
        org = (
            await self._session.execute(select(Organization).where(Organization.id == org_id))
        ).scalar_one_or_none()
        logo_url = None
        if org and org.logo_file_key:
            logo_url = await presigned_get_url(settings.CLOUDINARY_FOLDER_LOGOS, org.logo_file_key)
        return org, logo_url

    async def _generate_program_po_attainment(self, run: ReportRun) -> tuple[bytes, dict]:
        org_id = run.organization_id
        raw_program_ids = (run.params or {}).get("program_ids")
        program_ids = [UUID(p) for p in raw_program_ids] if raw_program_ids else None

        prog_query = select(Program).where(
            Program.organization_id == org_id, Program.status == "ACTIVE"
        )
        if program_ids is not None:
            prog_query = prog_query.where(Program.id.in_(program_ids))
        programs = list((await self._session.execute(prog_query)).scalars().all())

        org, org_logo_url = await self._org_letterhead(org_id)

        program_blocks = []
        all_pcts: list[float] = []
        po_report_svc = ProgramPOAttainmentReportService(self._session)

        for program in programs:
            term_pairs = (
                await self._session.execute(
                    select(
                        SectionOffering.academic_term_id,
                        AcademicTerm.name,
                        AcademicTerm.year,
                        AcademicTerm.season,
                    )
                    .join(Curriculum, Curriculum.id == SectionOffering.curriculum_id)
                    .join(AcademicTerm, AcademicTerm.id == SectionOffering.academic_term_id)
                    .join(POAttainmentResult, POAttainmentResult.section_offering_id == SectionOffering.id)
                    .where(Curriculum.program_id == program.id, SectionOffering.organization_id == org_id)
                    .distinct()
                    .order_by(AcademicTerm.year.desc(), AcademicTerm.season)
                )
            ).all()

            terms_out = []
            for term_id, term_name, term_year, term_season in term_pairs:
                report = await po_report_svc.generate(org_id, program.id, term_id)
                if not report.po_rows:
                    continue
                po_ids = [r.program_outcome_id for r in report.po_rows]
                po_map = {
                    po.id: po
                    for po in (
                        await self._session.execute(select(ProgramOutcome).where(ProgramOutcome.id.in_(po_ids)))
                    ).scalars().all()
                }
                rows = []
                for r in sorted(report.po_rows, key=lambda x: (po_map.get(x.program_outcome_id).code if po_map.get(x.program_outcome_id) else "")):
                    po = po_map.get(r.program_outcome_id)
                    pct = float(r.avg_attainment_pct)
                    rows.append(
                        {
                            "code": po.code if po else str(r.program_outcome_id),
                            "statement": po.statement if po else "",
                            "avg_pct": pct,
                            "attained_count": r.attained_count,
                            "offering_count": r.offering_count,
                        }
                    )
                    all_pcts.append(pct)
                terms_out.append(
                    {"term_name": term_name, "term_year": term_year, "term_season": term_season, "rows": rows}
                )

            program_blocks.append({"title": program.title, "acronym": program.acronym, "terms": terms_out})

        html = _render_report_html(
            "program_po_attainment.html",
            {
                "title": "Program PO Attainment Summary",
                "org_name": org.name if org else "",
                "org_logo_url": org_logo_url,
                "meta": [("Programs", ", ".join(p.acronym for p in programs) or "None in scope")],
                "programs": program_blocks,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            },
        )
        pdf_bytes = await _render_report_pdf(html)

        overall_avg = round(sum(all_pcts) / len(all_pcts), 2) if all_pcts else 0.0
        summary = {"programs_covered": len(programs), "overall_avg_po_attainment_pct": overall_avg}
        return pdf_bytes, summary

    async def _generate_accreditation_ssr(self, run: ReportRun) -> tuple[bytes, dict]:
        org_id = run.organization_id
        cycle_id = UUID((run.params or {})["cycle_id"])

        cycle = (
            await self._session.execute(
                select(AccreditationCycle).where(
                    AccreditationCycle.id == cycle_id, AccreditationCycle.organization_id == org_id
                )
            )
        ).scalar_one_or_none()
        if cycle is None:
            raise ValueError("Accreditation cycle not found")

        program = (
            await self._session.execute(select(Program).where(Program.id == cycle.program_id))
        ).scalar_one_or_none()
        org, org_logo_url = await self._org_letterhead(org_id)

        criteria = list(
            (
                await self._session.execute(
                    select(AccreditationCriterion)
                    .where(AccreditationCriterion.cycle_id == cycle_id)
                    .order_by(AccreditationCriterion.order_index)
                )
            ).scalars().all()
        )

        assignee_ids = {c.assigned_to_user_id for c in criteria if c.assigned_to_user_id}
        name_map: dict[UUID, str] = {}
        if assignee_ids:
            rows = (
                await self._session.execute(select(User.id, User.full_name).where(User.id.in_(assignee_ids)))
            ).all()
            name_map = dict(rows)

        start_year = cycle.start_date.year
        end_year = cycle.end_date.year if cycle.end_date else start_year

        criteria_out = []
        all_pcts: list[float] = []
        completed = 0
        for c in criteria:
            if c.status == "COMPLETED":
                completed += 1

            mappings = list(
                (
                    await self._session.execute(
                        select(CriterionPOMapping).where(CriterionPOMapping.criterion_id == c.id)
                    )
                ).scalars().all()
            )
            po_rows = []
            if mappings:
                po_ids = [m.program_outcome_id for m in mappings]
                po_map = {
                    po.id: po
                    for po in (
                        await self._session.execute(select(ProgramOutcome).where(ProgramOutcome.id.in_(po_ids)))
                    ).scalars().all()
                }
                results = (
                    await self._session.execute(
                        select(POAttainmentResult.program_outcome_id, POAttainmentResult.attainment_pct)
                        .join(SectionOffering, SectionOffering.id == POAttainmentResult.section_offering_id)
                        .join(Curriculum, Curriculum.id == SectionOffering.curriculum_id)
                        .join(AcademicTerm, AcademicTerm.id == SectionOffering.academic_term_id)
                        .where(
                            Curriculum.program_id == cycle.program_id,
                            POAttainmentResult.program_outcome_id.in_(po_ids),
                            AcademicTerm.year >= start_year,
                            AcademicTerm.year <= end_year,
                        )
                    )
                ).all()
                by_po: dict[UUID, list[float]] = defaultdict(list)
                for po_id, pct in results:
                    by_po[po_id].append(float(pct))

                for m in mappings:
                    po = po_map.get(m.program_outcome_id)
                    values = by_po.get(m.program_outcome_id, [])
                    avg_pct = round(sum(values) / len(values), 2) if values else 0.0
                    po_rows.append(
                        {"code": po.code if po else str(m.program_outcome_id), "statement": po.statement if po else "", "avg_pct": avg_pct}
                    )
                    if values:
                        all_pcts.append(avg_pct)

            criteria_out.append(
                {
                    "code": c.code,
                    "title": c.title,
                    "description": c.description,
                    "status": c.status,
                    "assigned_to": name_map.get(c.assigned_to_user_id) if c.assigned_to_user_id else None,
                    "po_rows": po_rows,
                }
            )

        overall_avg = round(sum(all_pcts) / len(all_pcts), 2) if all_pcts else 0.0
        summary = {
            "total_criteria": len(criteria),
            "completed_criteria": completed,
            "overall_avg_pct": overall_avg,
        }

        html = _render_report_html(
            "accreditation_ssr.html",
            {
                "title": f"{cycle.name} — Self-Assessment Report",
                "org_name": org.name if org else "",
                "org_logo_url": org_logo_url,
                "meta": [
                    ("Accreditation Body", cycle.body),
                    ("Program", f"{program.title} ({program.acronym})" if program else ""),
                    ("Period", f"{cycle.start_date} – {cycle.end_date or 'present'}"),
                    ("Cycle Status", cycle.status),
                ],
                "summary": summary,
                "criteria": criteria_out,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            },
        )
        pdf_bytes = await _render_report_pdf(html)
        return pdf_bytes, summary
