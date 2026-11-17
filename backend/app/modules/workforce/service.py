"""
Workforce readiness: read job postings into skills, then check which of a curriculum's
course outcomes develop the skills employers ask for most.

Model calls go through the AI gateway (feature "authoring": curriculum text and job
postings only, no student data). Results are stored with model and prompt version and
written to the audit log.
"""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.gateway import AIGateway, BackendFactory
from app.modules.ai.providers import AIError
from app.modules.assessment.models import Student
from app.modules.audit.writer import write_audit_log
from app.modules.authoring.context import program_outcomes_for
from app.modules.authoring.exceptions import (
    AuthoringModelError,
    AuthoringUnavailableError,
    NothingToMapError,
)
from app.modules.curriculum.exceptions import CurriculumNotFoundError
from app.modules.curriculum.models import Batch, Course, Curriculum
from app.modules.iam.models import User
from app.modules.obe.mapping_rules import natural_key
from app.modules.obe.models import COPOMappingEntry, COPOMappingSet, CourseOutcome, ProgramOutcome
from app.modules.org.models import Program
from app.modules.workforce import analysis, importing
from app.modules.workforce.models import MarketAnalysis, MarketPosting
from app.modules.workforce.schemas import (
    AnalysisResponse,
    ImportProblem,
    ImportResult,
    PostingCreate,
    PostingResponse,
    SkillEvidence,
    StudentSkill,
    StudentSkillsResponse,
    StudentSkillsSummary,
)

FEATURE = "authoring"


class ProgramNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")


class PostingNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found")


class WorkforceService:
    def __init__(self, session: AsyncSession, user: User, backend_factory: BackendFactory) -> None:
        self.db = session
        self.user = user
        self.backend_factory = backend_factory

    async def _program(self, program_id: UUID) -> Program:
        program = (await self.db.execute(select(Program).where(and_(
            Program.id == program_id, Program.organization_id == self.user.organization_id,
        )))).scalar_one_or_none()
        if program is None:
            raise ProgramNotFoundError()
        return program

    async def _gateway(self, required: bool = True) -> AIGateway | None:
        gateway = await AIGateway.for_feature(
            self.db, feature=FEATURE, organization_id=self.user.organization_id,
            user_id=self.user.id, backend_factory=self.backend_factory,
        )
        if not gateway.available:
            if required:
                raise AuthoringUnavailableError(gateway.unavailable_reason())
            return None
        return gateway

    # ── Postings ──────────────────────────────────────────────────────────────

    async def list_postings(self, program_id: UUID) -> list[MarketPosting]:
        await self._program(program_id)
        return list((await self.db.execute(
            select(MarketPosting).where(MarketPosting.program_id == program_id)
            .order_by(MarketPosting.created_at.desc())
        )).scalars().all())

    async def create_posting(self, program_id: UUID, body: PostingCreate) -> MarketPosting:
        await self._program(program_id)
        posting = MarketPosting(
            organization_id=self.user.organization_id,
            program_id=program_id,
            title=body.title.strip(),
            employer=(body.employer or "").strip() or None,
            source=(body.source or "").strip() or None,
            posted_on=body.posted_on,
            text=body.text.strip(),
            created_by_user_id=self.user.id,
        )
        self.db.add(posting)
        await self.db.flush()
        # Read the skills now when the AI is reachable; otherwise the next analysis does it.
        gateway = await self._gateway(required=False)
        if gateway is not None:
            await self.db.commit()
            try:
                await self._read_skills(gateway, posting)
            except AIError:
                pass
            gateway.record_usage(self.db)
        await self.db.commit()
        return posting

    async def delete_posting(self, posting_id: UUID) -> None:
        posting = (await self.db.execute(select(MarketPosting).where(and_(
            MarketPosting.id == posting_id, MarketPosting.organization_id == self.user.organization_id,
        )))).scalar_one_or_none()
        if posting is None:
            raise PostingNotFoundError()
        await self.db.delete(posting)
        await self.db.commit()

    # ── Importing real postings ───────────────────────────────────────────────
    # Imported postings are saved without reading their skills; the next analysis
    # reads every unread posting, so an import never makes one model call per row.

    def _imported(self, program_id: UUID, item: importing.ImportedPosting) -> MarketPosting:
        posting = MarketPosting(
            organization_id=self.user.organization_id,
            program_id=program_id,
            title=item.title,
            employer=item.employer,
            source=item.source,
            text=item.text,
            created_by_user_id=self.user.id,
        )
        self.db.add(posting)
        return posting

    async def import_urls(self, program_id: UUID, urls: list[str]) -> ImportResult:
        await self._program(program_id)
        unique = list(dict.fromkeys(u.strip() for u in urls if u.strip()))[: importing.MAX_URLS]
        existing = set((await self.db.execute(
            select(MarketPosting.source).where(and_(
                MarketPosting.program_id == program_id, MarketPosting.source.in_(unique),
            ))
        )).scalars().all())
        added: list[MarketPosting] = []
        errors: list[ImportProblem] = []
        for url in unique:
            if url in existing:
                errors.append(ImportProblem(source=url, error="Already imported."))
                continue
            try:
                item = await importing.posting_from_url(url)
            except importing.ImportFailedError as exc:
                errors.append(ImportProblem(source=url, error=str(exc)))
                continue
            added.append(self._imported(program_id, item))
        await self._finish_import(program_id, added, "urls")
        return ImportResult(added=[PostingResponse.model_validate(p) for p in added], errors=errors)

    async def import_csv(self, program_id: UUID, data: bytes) -> ImportResult:
        await self._program(program_id)
        try:
            items, skipped = importing.read_csv(data)
        except importing.ImportFailedError as exc:
            return ImportResult(added=[], errors=[ImportProblem(source="file", error=str(exc))])
        added = [self._imported(program_id, item) for item in items]
        await self._finish_import(program_id, added, "csv")
        return ImportResult(
            added=[PostingResponse.model_validate(p) for p in added],
            errors=[ImportProblem(source="file", error=message) for message in skipped],
        )

    async def _finish_import(self, program_id: UUID, added: list[MarketPosting], kind: str) -> None:
        await self.db.flush()
        if added:
            write_audit_log(
                self.db,
                entity_type="program",
                entity_id=program_id,
                action="workforce.postings.import",
                org_id=self.user.organization_id,
                actor_user_id=self.user.id,
                extra={"kind": kind, "count": len(added)},
            )
        await self.db.commit()
        for posting in added:
            await self.db.refresh(posting)

    # ── A student's verified skills ──────────────────────────────────────────

    async def student_skills(self, student_id: UUID, top_n: int = 10) -> StudentSkillsResponse:
        """The student's own published CO results set against the program's latest
        market analysis. Pure computation: no model sees the student's data."""
        from app.modules.assessment.service import MarksheetService

        empty = StudentSkillsResponse(
            analysis_date=None, posting_count=0, skills=[],
            summary=StudentSkillsSummary(verified=0, developing=0, not_yet=0, top_n=0, top_verified=0),
        )
        student = (await self.db.execute(
            select(Student).where(and_(
                Student.id == student_id, Student.organization_id == self.user.organization_id,
            ))
        )).scalar_one_or_none()
        if student is None:
            return empty
        curriculum_id = None
        if student.batch_id:
            curriculum_id = (await self.db.execute(
                select(Batch.curriculum_id).where(Batch.id == student.batch_id)
            )).scalar_one_or_none()
        query = select(MarketAnalysis).where(MarketAnalysis.organization_id == self.user.organization_id)
        if curriculum_id:
            query = query.where(MarketAnalysis.curriculum_id == curriculum_id)
        elif student.program_id:
            query = query.where(MarketAnalysis.program_id == student.program_id)
        else:
            return empty
        row = (await self.db.execute(query.order_by(MarketAnalysis.created_at.desc()).limit(1))).scalar_one_or_none()
        if row is None:
            return empty

        results = await MarksheetService(self.db).get_results_for_student(student.id, self.user.organization_id)
        return build_student_skills(row.result.get("skills", []), results, row.posting_count, row.created_at, top_n)

    async def _read_skills(self, gateway: AIGateway, posting: MarketPosting) -> None:
        completion = await gateway.complete_json(
            purpose="read_job_skills",
            prompt=analysis.SKILLS_PROMPT.format(
                max_skills=analysis.MAX_SKILLS_PER_POSTING,
                posting=analysis.posting_text(posting.title, posting.employer, posting.text),
            ),
            schema=analysis.SKILLS_SCHEMA,
            prompt_version=analysis.SKILLS_PROMPT_VERSION,
            temperature=0.0,
        )
        posting.skills = analysis.clean_skills(completion.data.get("skills"))
        posting.skills_model = completion.model[:100]
        posting.skills_prompt_version = analysis.SKILLS_PROMPT_VERSION

    # ── Analysis ──────────────────────────────────────────────────────────────

    async def analyze(self, program_id: UUID, curriculum_id: UUID) -> AnalysisResponse:
        program = await self._program(program_id)
        curriculum = (await self.db.execute(select(Curriculum).where(and_(
            Curriculum.id == curriculum_id, Curriculum.organization_id == self.user.organization_id,
            Curriculum.program_id == program.id,
        )))).scalar_one_or_none()
        if curriculum is None:
            raise CurriculumNotFoundError()
        postings = await self.list_postings(program_id)
        if not postings:
            raise NothingToMapError("Add job postings for this program first.")
        outcomes = await self._curriculum_outcomes(curriculum_id)
        if not outcomes:
            raise NothingToMapError("This curriculum has no course outcomes yet.")
        pos = await program_outcomes_for(self.db, self.user.organization_id, program.id)

        gateway = await self._gateway()
        await self.db.commit()
        try:
            for posting in postings:
                if posting.skills is None:
                    await self._read_skills(gateway, posting)
            demands = analysis.aggregate([(p.title, p.skills or []) for p in postings])
            if not demands:
                raise AIError("no skills could be read from the postings")
            courses = {
                o.course_code: {"id": o.course_id, "code": o.course_code, "title": o.course_title}
                for o in outcomes
            }
            completion = await gateway.complete_json(
                purpose="judge_skill_coverage",
                prompt=analysis.coverage_prompt(demands, len(postings), outcomes),
                schema=analysis.coverage_schema(
                    [d.name for d in demands], [o.ref for o in outcomes], sorted(courses),
                ),
                prompt_version=analysis.COVERAGE_PROMPT_VERSION,
                temperature=0.0,
            )
        except AIError as exc:
            gateway.record_usage(self.db)
            await self.db.commit()
            raise AuthoringModelError(str(exc)) from exc

        result = analysis.build_result(
            demands, completion.data.get("skills"), outcomes, courses,
            [{"code": po.code, "statement": po.statement} for po in pos], len(postings),
        )
        row = MarketAnalysis(
            organization_id=self.user.organization_id,
            program_id=program.id,
            curriculum_id=curriculum_id,
            posting_count=len(postings),
            result=result,
            provider=gateway.provider,
            model=completion.model[:100],
            prompt_version=analysis.COVERAGE_PROMPT_VERSION,
            created_by_user_id=self.user.id,
        )
        self.db.add(row)
        gateway.record_usage(self.db)
        await self.db.flush()
        write_audit_log(
            self.db,
            entity_type="curriculum",
            entity_id=curriculum_id,
            action="AI_MARKET_ANALYSIS",
            org_id=self.user.organization_id,
            actor_user_id=self.user.id,
            extra={
                "analysis_id": str(row.id), "postings": len(postings), "model": row.model,
                "prompt_version": row.prompt_version, "provider": row.provider, **result["summary"],
            },
        )
        await self.db.commit()
        return _response(row)

    async def latest(self, program_id: UUID, curriculum_id: UUID) -> AnalysisResponse | None:
        await self._program(program_id)
        row = (await self.db.execute(
            select(MarketAnalysis).where(and_(
                MarketAnalysis.program_id == program_id, MarketAnalysis.curriculum_id == curriculum_id,
            )).order_by(MarketAnalysis.created_at.desc()).limit(1)
        )).scalar_one_or_none()
        return _response(row) if row else None

    async def _curriculum_outcomes(self, curriculum_id: UUID) -> list[analysis.CourseOutcomeRow]:
        rows = (await self.db.execute(
            select(CourseOutcome, Course.code, Course.title)
            .join(Course, Course.id == CourseOutcome.course_id)
            .where(CourseOutcome.curriculum_id == curriculum_id)
        )).all()
        po_rows = (await self.db.execute(
            select(COPOMappingEntry.course_outcome_id, ProgramOutcome.code)
            .join(COPOMappingSet, COPOMappingSet.id == COPOMappingEntry.mapping_set_id)
            .join(ProgramOutcome, ProgramOutcome.id == COPOMappingEntry.program_outcome_id)
            .where(COPOMappingSet.curriculum_id == curriculum_id)
        )).all()
        pos: dict[UUID, set[str]] = {}
        for co_id, code in po_rows:
            pos.setdefault(co_id, set()).add(code)
        outcomes = [
            analysis.CourseOutcomeRow(
                ref=f"{course_code}/{co.code}", co_id=str(co.id), co_code=co.code,
                course_id=str(co.course_id), course_code=course_code, course_title=course_title,
                statement=co.statement, po_codes=sorted(pos.get(co.id, set()), key=natural_key),
            )
            for co, course_code, course_title in rows
        ]
        outcomes.sort(key=lambda o: (natural_key(o.course_code), natural_key(o.co_code)))
        return outcomes


def build_student_skills(
    skills: list[dict], results: list[dict], posting_count: int, analysed_at, top_n: int = 10,
) -> StudentSkillsResponse:
    """Match each demanded skill's covering COs with the student's own CO results."""
    mine: dict[tuple[str, str], tuple[dict, dict]] = {}
    for course in results:
        for co in course.get("co_results") or []:
            # A course taken twice keeps the better result.
            key = (course["course_code"], co["co_code"])
            if key not in mine or co["attainment_percentage"] > mine[key][1]["attainment_percentage"]:
                mine[key] = (course, co)
    out: list[StudentSkill] = []
    for skill in skills:
        evidence = []
        for ref in skill.get("outcomes") or []:
            found = mine.get((ref.get("course_code"), ref.get("co_code")))
            if not found:
                continue
            course, co = found
            evidence.append(SkillEvidence(
                course_code=course["course_code"], course_title=course.get("course_title", ""),
                co_code=co["co_code"], statement=co.get("co_statement") or ref.get("statement", ""),
                attainment_pct=round(float(co["attainment_percentage"]), 1),
                attained=bool(co.get("is_threshold_met")),
            ))
        status = (
            "verified" if any(e.attained for e in evidence)
            else "developing" if evidence else "not_yet"
        )
        out.append(StudentSkill(
            skill=skill["skill"], category=skill.get("category", "technical"),
            postings=skill.get("postings", 0), required=skill.get("required", 0),
            status=status, evidence=evidence, program_outcomes=skill.get("program_outcomes", []),
        ))
    out.sort(key=lambda s: -s.postings)
    top = out[:top_n]
    return StudentSkillsResponse(
        analysis_date=analysed_at, posting_count=posting_count, skills=out,
        summary=StudentSkillsSummary(
            verified=sum(s.status == "verified" for s in out),
            developing=sum(s.status == "developing" for s in out),
            not_yet=sum(s.status == "not_yet" for s in out),
            top_n=len(top), top_verified=sum(s.status == "verified" for s in top),
        ),
    )


def _response(row: MarketAnalysis) -> AnalysisResponse:
    return AnalysisResponse(
        id=row.id,
        program_id=row.program_id,
        curriculum_id=row.curriculum_id,
        posting_count=row.posting_count,
        skills=row.result.get("skills", []),
        summary=row.result.get("summary", {}),
        program_outcomes=row.result.get("program_outcomes", []),
        model=row.model,
        prompt_version=row.prompt_version,
        created_at=row.created_at,
    )
