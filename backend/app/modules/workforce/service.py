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
from app.modules.audit.writer import write_audit_log
from app.modules.authoring.context import program_outcomes_for
from app.modules.authoring.exceptions import (
    AuthoringModelError,
    AuthoringUnavailableError,
    NothingToMapError,
)
from app.modules.curriculum.exceptions import CurriculumNotFoundError
from app.modules.curriculum.models import Course, Curriculum
from app.modules.iam.models import User
from app.modules.obe.mapping_rules import natural_key
from app.modules.obe.models import COPOMappingEntry, COPOMappingSet, CourseOutcome, ProgramOutcome
from app.modules.org.models import Program
from app.modules.workforce import analysis
from app.modules.workforce.models import MarketAnalysis, MarketPosting
from app.modules.workforce.schemas import AnalysisResponse, PostingCreate

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
