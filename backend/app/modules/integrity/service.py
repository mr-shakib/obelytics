"""
Assessment integrity: read a question paper, audit each marksheet question's Bloom
level and course outcome against what the teacher declared, and record the
teacher's review of each judgment.

IntegrityService runs inside API requests: access checks, the overview, saving
wording, reviews, and *starting* jobs. IntegrityJobService runs in the background
(jobs.py) and does the model work through the AI gateway, writing its results in
one step at the end so a failed job changes nothing.
"""
import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import exists, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ai.gateway import AIGateway
from app.modules.assessment.models import MarksheetQuestion
from app.modules.audit.writer import write_audit_log
from app.modules.curriculum.models import (
    AcademicTerm,
    Batch,
    Course,
    FacultyAssignment,
    ModuleLeaderAssignment,
    Section,
    SectionOffering,
)
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.integrity import documents
from app.modules.integrity.auditing import (
    build_audit_prompt,
    co_key,
    judge,
    judge_alignment,
)
from app.modules.integrity.exceptions import (
    JobAlreadyRunningError,
    NoQuestionTextError,
    OverrideReasonRequiredError,
    PaperTooLargeError,
    PaperTooManyPagesError,
    PaperUnreadableError,
    QuestionAuditNotFoundError,
    QuestionNotInSectionError,
    SectionAccessDeniedError,
    SectionOfferingNotFoundError,
    UnsupportedPaperTypeError,
)
from app.modules.integrity.jobs import JobError, encode_paper
from app.modules.integrity.models import (
    ACTIVE_JOB_STATUSES,
    IntegrityJob,
    QuestionAudit,
    QuestionPaper,
)
from app.modules.integrity.prompts import AUDIT_PROMPT_VERSION
from app.modules.integrity.reading import read_paper
from app.modules.integrity.schemas import (
    AuditableSection,
    AuditedQuestion,
    BloomLevelRef,
    CourseOutcomeRef,
    ExtractedQuestion,
    IntegrityJobResponse,
    IntegrityOverview,
    IntegritySummary,
    QuestionAuditResponse,
    QuestionPaperResponse,
    QuestionTextItem,
)
from app.modules.obe.models import CourseOutcome
from app.modules.ref_data.models import BloomDomain, BloomLevel

# A job still "running" this long after it was queued has died with its worker.
_STALE_AFTER = timedelta(seconds=settings.INTEGRITY_JOB_TIMEOUT_SECONDS + 120)
_STALE_ERROR = "This stopped without finishing (the server restarted or timed out). Try again."


def _taught_or_led_by(user_id: UUID):
    teaches = exists().where(
        FacultyAssignment.section_offering_id == SectionOffering.id,
        FacultyAssignment.user_id == user_id,
        FacultyAssignment.removed_at.is_(None),
    )
    leads = exists().where(
        ModuleLeaderAssignment.batch_id == SectionOffering.batch_id,
        ModuleLeaderAssignment.academic_term_id == SectionOffering.academic_term_id,
        ModuleLeaderAssignment.course_id == SectionOffering.course_id,
        ModuleLeaderAssignment.user_id == user_id,
        ModuleLeaderAssignment.removed_at.is_(None),
    )
    return or_(teaches, leads)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _questions(session: AsyncSession, offering_id: UUID, exam_type: str) -> list[MarksheetQuestion]:
    result = await session.execute(
        select(MarksheetQuestion)
        .where(
            MarksheetQuestion.section_offering_id == offering_id,
            MarksheetQuestion.exam_type == exam_type,
        )
        .order_by(MarksheetQuestion.order_index, MarksheetQuestion.label)
        .execution_options(populate_existing=True)
    )
    return list(result.scalars().all())


async def _paper(session: AsyncSession, offering_id: UUID, exam_type: str) -> QuestionPaper | None:
    return (await session.execute(
        select(QuestionPaper)
        .where(QuestionPaper.section_offering_id == offering_id, QuestionPaper.exam_type == exam_type)
        .execution_options(populate_existing=True)
    )).scalar_one_or_none()


class IntegrityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Access ────────────────────────────────────────────────────────────────

    @staticmethod
    def _is_org_wide(manifest: PermissionManifestResponse) -> bool:
        return manifest.is_super_admin or "curriculum.create" in manifest.permissions

    async def get_offering(
        self, offering_id: UUID, user: User, manifest: PermissionManifestResponse
    ) -> SectionOffering:
        offering = (await self._session.execute(
            select(SectionOffering).where(
                SectionOffering.id == offering_id,
                SectionOffering.organization_id == user.organization_id,
            )
        )).scalar_one_or_none()
        if offering is None:
            raise SectionOfferingNotFoundError()
        if not self._is_org_wide(manifest):
            allowed = await self._session.scalar(
                select(SectionOffering.id).where(
                    SectionOffering.id == offering.id, _taught_or_led_by(user.id)
                )
            )
            if allowed is None:
                raise SectionAccessDeniedError()
        return offering

    def _sections_query(self):
        return (
            select(
                SectionOffering.id,
                Course.code,
                Course.title,
                Section.name,
                AcademicTerm.name,
                Batch.name,
            )
            .join(Course, Course.id == SectionOffering.course_id)
            .join(Section, Section.id == SectionOffering.section_id)
            .join(AcademicTerm, AcademicTerm.id == SectionOffering.academic_term_id)
            .join(Batch, Batch.id == SectionOffering.batch_id)
        )

    @staticmethod
    def _to_section(row) -> AuditableSection:
        return AuditableSection(
            id=row[0], course_code=row[1], course_title=row[2],
            section_name=row[3], term_name=row[4], batch_name=row[5],
        )

    async def list_sections(
        self, user: User, manifest: PermissionManifestResponse
    ) -> list[AuditableSection]:
        stmt = (
            self._sections_query()
            .where(SectionOffering.organization_id == user.organization_id)
            .order_by(AcademicTerm.start_date.desc(), Course.code, Section.name)
            .limit(500)
        )
        if not self._is_org_wide(manifest):
            stmt = stmt.where(_taught_or_led_by(user.id))
        return [self._to_section(row) for row in (await self._session.execute(stmt)).all()]

    # ── Overview ──────────────────────────────────────────────────────────────

    async def overview(self, offering: SectionOffering, exam_type: str) -> IntegrityOverview:
        session = self._session
        section_row = (await session.execute(
            self._sections_query().where(SectionOffering.id == offering.id)
        )).one()
        questions = await _questions(session, offering.id, exam_type)
        audits: dict[UUID, QuestionAudit] = {}
        if questions:
            result = await session.execute(
                select(QuestionAudit)
                .where(
                    QuestionAudit.question_id.in_([q.id for q in questions]),
                    QuestionAudit.is_current.is_(True),
                )
                .execution_options(populate_existing=True)
            )
            audits = {audit.question_id: audit for audit in result.scalars().all()}

        bloom_ids = {q.declared_bloom_level_id for q in questions}
        bloom_ids |= {a.ai_bloom_level_id for a in audits.values()}
        bloom_ids.discard(None)
        blooms: dict[UUID, BloomLevelRef] = {}
        if bloom_ids:
            rows = (await session.execute(
                select(BloomLevel).where(BloomLevel.id.in_(bloom_ids))
            )).scalars().all()
            blooms = {b.id: BloomLevelRef(id=b.id, code=b.code, name=b.name) for b in rows}

        co_ids = {q.course_outcome_id for q in questions}
        co_ids |= {a.ai_course_outcome_id for a in audits.values()}
        co_ids.discard(None)
        outcomes: dict[UUID, CourseOutcomeRef] = {}
        if co_ids:
            rows = (await session.execute(
                select(CourseOutcome).where(CourseOutcome.id.in_(co_ids))
            )).scalars().all()
            outcomes = {
                co.id: CourseOutcomeRef(id=co.id, code=co.code, statement=co.statement) for co in rows
            }

        items = []
        for question in questions:
            audit = audits.get(question.id)
            details = audit.details if audit is not None and isinstance(audit.details, dict) else {}
            items.append(AuditedQuestion(
                question_id=question.id,
                label=question.label,
                max_marks=float(question.max_marks),
                question_text=question.question_text,
                declared_bloom_level=blooms.get(question.declared_bloom_level_id),
                declared_course_outcome=outcomes.get(question.course_outcome_id),
                audit=None if audit is None else QuestionAuditResponse(
                    id=audit.id,
                    alignment=audit.alignment,
                    confidence=float(audit.confidence) if audit.confidence is not None else None,
                    raw_confidence=(
                        float(audit.raw_confidence) if audit.raw_confidence is not None else None
                    ),
                    agreement=details.get("consistency"),
                    samples=details.get("samples"),
                    rationale=audit.rationale,
                    evidence_quote=audit.evidence_quote,
                    ai_bloom_level=blooms.get(audit.ai_bloom_level_id),
                    ai_course_outcome=outcomes.get(audit.ai_course_outcome_id),
                    model=audit.model,
                    prompt_version=audit.prompt_version,
                    review_status=audit.review_status,
                    override_reason=audit.override_reason,
                    reviewed_at=audit.reviewed_at,
                    created_at=audit.created_at,
                ),
            ))

        current = [item.audit for item in items if item.audit is not None]
        summary = IntegritySummary(
            questions=len(items),
            with_text=sum(1 for item in items if item.question_text),
            audited=len(current),
            aligned=sum(1 for a in current if a.alignment == "ALIGNED"),
            partial=sum(1 for a in current if a.alignment == "PARTIAL"),
            misaligned=sum(1 for a in current if a.alignment == "MISALIGNED"),
            abstained=sum(1 for a in current if a.alignment == "ABSTAINED"),
            pending_review=sum(1 for a in current if a.review_status == "PENDING"),
        )
        paper = await _paper(session, offering.id, exam_type)
        return IntegrityOverview(
            section=self._to_section(section_row),
            exam_type=exam_type,
            paper=None if paper is None else self._paper_response(paper, questions),
            questions=items,
            summary=summary,
            job=await self._latest_job(offering.id, exam_type),
        )

    @staticmethod
    def _paper_response(
        paper: QuestionPaper, questions: list[MarksheetQuestion]
    ) -> QuestionPaperResponse:
        by_label = {documents.normalize_label(q.label): q.id for q in questions}
        response = QuestionPaperResponse.model_validate(paper)
        response.questions = [
            ExtractedQuestion(
                **item,
                matched_question_id=by_label.get(documents.normalize_label(item["label"])),
            )
            for item in paper.extracted_questions or []
        ]
        return response

    async def _latest_job(self, offering_id: UUID, exam_type: str) -> IntegrityJobResponse | None:
        job = (await self._session.execute(
            select(IntegrityJob)
            .where(IntegrityJob.section_offering_id == offering_id, IntegrityJob.exam_type == exam_type)
            .order_by(IntegrityJob.created_at.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )).scalar_one_or_none()
        if job is None:
            return None
        response = IntegrityJobResponse.model_validate(job)
        if job.status in ACTIVE_JOB_STATUSES and job.created_at < _now() - _STALE_AFTER:
            response.status, response.error = "FAILED", _STALE_ERROR
        return response

    # ── Starting jobs ─────────────────────────────────────────────────────────

    async def _new_job(self, offering: SectionOffering, exam_type: str, kind: str, user_id: UUID) -> IntegrityJob:
        # A job whose worker died never finishes; let a new one start.
        await self._session.execute(
            update(IntegrityJob)
            .where(
                IntegrityJob.section_offering_id == offering.id,
                IntegrityJob.exam_type == exam_type,
                IntegrityJob.status.in_(ACTIVE_JOB_STATUSES),
                IntegrityJob.created_at < _now() - _STALE_AFTER,
            )
            .values(status="FAILED", error=_STALE_ERROR, finished_at=_now())
        )
        active = await self._session.scalar(
            select(IntegrityJob.kind).where(
                IntegrityJob.section_offering_id == offering.id,
                IntegrityJob.exam_type == exam_type,
                IntegrityJob.status.in_(ACTIVE_JOB_STATUSES),
            )
        )
        if active is not None:
            raise JobAlreadyRunningError(active)
        job = IntegrityJob(
            organization_id=offering.organization_id,
            section_offering_id=offering.id,
            exam_type=exam_type,
            kind=kind,
            created_by_user_id=user_id,
        )
        self._session.add(job)
        try:
            await self._session.flush()
        except IntegrityError as exc:  # another request started one at the same moment
            await self._session.rollback()
            raise JobAlreadyRunningError(None) from exc
        return job

    async def start_reading(
        self,
        offering: SectionOffering,
        exam_type: str,
        filename: str | None,
        content_type: str | None,
        data: bytes,
        user_id: UUID,
    ) -> tuple[IntegrityJob, dict]:
        """Check the file and prepare its pages now (fast); the model reads them in a job."""
        content_type = documents.normalize_content_type(content_type, filename)
        if content_type not in documents.ACCEPTED_TYPES:
            raise UnsupportedPaperTypeError()
        if len(data) > settings.INTEGRITY_MAX_UPLOAD_BYTES:
            raise PaperTooLargeError(settings.INTEGRITY_MAX_UPLOAD_BYTES)
        if not data:
            raise PaperUnreadableError("The file is empty")
        try:
            prepared = await asyncio.to_thread(
                documents.prepare, data, content_type, settings.INTEGRITY_MAX_PAGES
            )
        except documents.TooManyPagesError as exc:
            raise PaperTooManyPagesError(settings.INTEGRITY_MAX_PAGES) from exc
        except documents.UnreadablePaperError as exc:
            raise PaperUnreadableError(str(exc)) from exc

        job = await self._new_job(offering, exam_type, "READ_PAPER", user_id)
        job.progress_total = len(prepared.pages)
        # Only the wording (once read) and a fingerprint are kept — never the file.
        paper = await _paper(self._session, offering.id, exam_type) or QuestionPaper(
            organization_id=offering.organization_id,
            section_offering_id=offering.id,
            exam_type=exam_type,
        )
        paper.original_filename = (filename or "question-paper")[:255]
        paper.content_type = content_type
        paper.file_size_bytes = len(data)
        paper.file_sha256 = hashlib.sha256(data).hexdigest()
        paper.page_count = prepared.page_count
        paper.extraction_method = prepared.method
        paper.uploaded_by_user_id = user_id
        paper.extraction_status = "PENDING"
        paper.extraction_error = None
        self._session.add(paper)
        await self._session.commit()
        return job, encode_paper(prepared)

    async def start_audit(self, offering: SectionOffering, exam_type: str, user_id: UUID) -> IntegrityJob:
        questions = await _questions(self._session, offering.id, exam_type)
        with_text = [q for q in questions if q.question_text]
        if not with_text:
            raise NoQuestionTextError()
        job = await self._new_job(offering, exam_type, "AUDIT", user_id)
        job.progress_total = len(with_text)
        await self._session.commit()
        return job

    async def submission_failed(self, job: IntegrityJob, error: str) -> None:
        """The job could not be handed to the worker (e.g. Redis is down)."""
        job.status = "FAILED"
        job.error = error
        job.finished_at = _now()
        if job.kind == "READ_PAPER":
            paper = await _paper(self._session, job.section_offering_id, job.exam_type)
            if paper is not None:
                paper.extraction_status = "FAILED"
                paper.extraction_error = error
        await self._session.commit()

    # ── Wording and reviews ───────────────────────────────────────────────────

    async def save_question_texts(
        self, offering: SectionOffering, exam_type: str, items: list[QuestionTextItem], user_id: UUID
    ) -> None:
        # Question wording is audit metadata, not marks, so it may be added after
        # the marksheet is locked — retrospective audits depend on that.
        ids = {item.question_id for item in items}
        result = await self._session.execute(
            select(MarksheetQuestion).where(
                MarksheetQuestion.section_offering_id == offering.id,
                MarksheetQuestion.exam_type == exam_type,
                MarksheetQuestion.id.in_(ids),
            )
        )
        questions = {q.id: q for q in result.scalars().all()}
        if len(questions) != len(ids):
            raise QuestionNotInSectionError()

        changed = []
        for item in items:
            text = (item.question_text or "").strip() or None
            question = questions[item.question_id]
            if question.question_text != text:
                question.question_text = text
                changed.append(question.id)
        if changed:
            # A judgment of the old wording no longer applies.
            await self._session.execute(
                update(QuestionAudit)
                .where(QuestionAudit.question_id.in_(changed), QuestionAudit.is_current.is_(True))
                .values(is_current=False)
            )
            write_audit_log(
                self._session,
                entity_type="section_offering",
                entity_id=offering.id,
                action="QUESTION_TEXT_UPDATED",
                org_id=offering.organization_id,
                actor_user_id=user_id,
                extra={"exam_type": exam_type, "questions": len(changed)},
            )
        await self._session.commit()

    async def review(
        self,
        audit_id: UUID,
        decision: str,
        reason: str | None,
        user: User,
        manifest: PermissionManifestResponse,
    ) -> tuple[SectionOffering, str]:
        audit = (await self._session.execute(
            select(QuestionAudit).where(
                QuestionAudit.id == audit_id,
                QuestionAudit.organization_id == user.organization_id,
            )
        )).scalar_one_or_none()
        if audit is None:
            raise QuestionAuditNotFoundError()
        question = await self._session.get(MarksheetQuestion, audit.question_id)
        offering = await self.get_offering(question.section_offering_id, user, manifest)

        reason = (reason or "").strip() or None
        before = audit.review_status
        if decision == "OVERRIDE":
            if reason is None:
                raise OverrideReasonRequiredError()
            audit.review_status = "OVERRIDDEN"
            audit.override_reason = reason
        else:
            audit.review_status = "ACCEPTED"
            audit.override_reason = None
        audit.reviewed_by_user_id = user.id
        audit.reviewed_at = _now()
        write_audit_log(
            self._session,
            entity_type="question_audit",
            entity_id=audit.id,
            action="INTEGRITY_AUDIT_REVIEWED",
            org_id=user.organization_id,
            actor_user_id=user.id,
            before_status=before,
            after_status=audit.review_status,
            extra={"reason": reason} if reason else None,
        )
        await self._session.commit()
        return offering, question.exam_type


class IntegrityJobService:
    """The model work of one job. Results are written at the end, all at once."""

    def __init__(self, session: AsyncSession, gateway: AIGateway, job: IntegrityJob) -> None:
        self._session = session
        self._gateway = gateway
        self._job = job
        # Kept as a plain value: after a rollback the job object is expired.
        self._job_id = job.id

    async def _progress(self, done: int) -> None:
        self._job.progress_done = done
        await self._session.commit()

    async def read(self, prepared: documents.PreparedPaper) -> dict:
        job = self._job
        job.progress_total = len(prepared.pages)
        await self._session.commit()

        result = await read_paper(self._gateway, prepared, self._progress)

        paper = await _paper(self._session, job.section_offering_id, job.exam_type)
        if paper is None:
            raise JobError("The question paper record was removed while it was being read")
        paper.extraction_status = "EXTRACTED"
        paper.extraction_error = None
        paper.extracted_questions = result.questions
        paper.extracted_text = "\n\n".join(f"{q['label']}. {q['text']}" for q in result.questions)
        paper.extraction_model = result.model
        paper.extraction_prompt_version = result.prompt_version
        flagged = sum(1 for q in result.questions if q.get("warning"))
        write_audit_log(
            self._session,
            entity_type="question_paper",
            entity_id=paper.id,
            action="QUESTION_PAPER_EXTRACTED",
            org_id=job.organization_id,
            actor_user_id=job.created_by_user_id,
            after_status="EXTRACTED",
            extra={
                "exam_type": job.exam_type,
                "method": paper.extraction_method,
                "pages": paper.page_count,
                "questions": len(result.questions),
                "flagged": flagged,
                "model": result.model,
                "prompt_version": result.prompt_version,
                "provider": self._gateway.provider,
            },
        )
        return {"questions": len(result.questions), "flagged": flagged}

    async def audit(self) -> dict:
        session, job = self._session, self._job
        offering = await session.get(SectionOffering, job.section_offering_id)
        if offering is None:
            raise JobError("The section was removed")
        to_audit = [q for q in await _questions(session, offering.id, job.exam_type) if q.question_text]
        if not to_audit:
            raise JobError("No question has wording to audit")

        course = await session.get(Course, offering.course_id)
        outcomes = (await session.execute(
            select(CourseOutcome)
            .where(
                CourseOutcome.course_id == offering.course_id,
                CourseOutcome.curriculum_id == offering.curriculum_id,
            )
            .order_by(CourseOutcome.code)
        )).scalars().all()
        levels = (await session.execute(
            select(BloomLevel, BloomDomain.name)
            .join(BloomDomain, BloomDomain.id == BloomLevel.bloom_domain_id)
            .where(BloomLevel.organization_id == offering.organization_id)
        )).all()
        level_codes = {level.id: level.code for level, _ in levels}
        cognitive = {
            level.code.upper(): level.id
            for level, domain in levels
            if domain.strip().lower().startswith("cognitive")
        }
        paper = await _paper(session, offering.id, job.exam_type)
        paper_items = (paper.extracted_questions if paper else None) or []
        by_label = {documents.normalize_label(item["label"]): item for item in paper_items}
        # A teacher may map a paper question to a marksheet question with another label.
        by_text = {item["text"]: item for item in paper_items}

        co_ids = {co_key(co.code): co.id for co in outcomes}
        outcome_lines = "\n".join(f"{co.code}: {co.statement}" for co in outcomes)
        work = []
        for question in to_audit:
            from_paper = (
                by_text.get(question.question_text)
                or by_label.get(documents.normalize_label(question.label))
                or {}
            )
            prompt = build_audit_prompt(
                course=f"{course.code} {course.title}",
                outcomes=outcome_lines,
                label=question.label,
                marks=f"{float(question.max_marks):g}",
                question=question.question_text,
                context=from_paper.get("context"),
                figure=from_paper.get("figure"),
            )
            work.append((question.id, question.declared_bloom_level_id, question.course_outcome_id, prompt))
        paper_id = paper.id if paper else None
        job.progress_total = len(work)
        await session.commit()  # release the connection during the model calls

        judgments = []
        for done, (question_id, declared_bloom_id, declared_co_id, prompt) in enumerate(work, 1):
            judgments.append((question_id, declared_bloom_id, declared_co_id, await judge(self._gateway, prompt)))
            await self._progress(done)

        # All judgments are in: replace the current audits in one step.
        await session.execute(
            update(QuestionAudit)
            .where(
                QuestionAudit.question_id.in_([item[0] for item in work]),
                QuestionAudit.is_current.is_(True),
            )
            .values(is_current=False)
        )
        counts: dict[str, int] = {}
        for question_id, declared_bloom_id, declared_co_id, judgment in judgments:
            ai_bloom_id = cognitive.get(judgment.bloom or "")
            ai_co_id = co_ids.get(judgment.co or "")
            alignment = judge_alignment(
                abstain=judgment.abstain,
                confidence=judgment.confidence,
                ai_bloom_code=level_codes.get(ai_bloom_id),
                declared_bloom_code=level_codes.get(declared_bloom_id),
                ai_co_id=ai_co_id,
                declared_co_id=declared_co_id,
            )
            counts[alignment] = counts.get(alignment, 0) + 1
            abstained = alignment == "ABSTAINED"
            session.add(QuestionAudit(
                organization_id=job.organization_id,
                question_id=question_id,
                question_paper_id=paper_id,
                ai_bloom_level_id=None if abstained else ai_bloom_id,
                ai_course_outcome_id=None if abstained else ai_co_id,
                alignment=alignment,
                confidence=Decimal(str(round(judgment.confidence, 3))),
                raw_confidence=Decimal(str(round(judgment.raw_confidence, 3))),
                details=judgment.details(),
                rationale=judgment.rationale,
                evidence_quote=judgment.evidence,
                model=judgment.model or "unknown",
                prompt_version=AUDIT_PROMPT_VERSION,
            ))
        write_audit_log(
            session,
            entity_type="section_offering",
            entity_id=offering.id,
            action="INTEGRITY_AUDIT_RUN",
            org_id=job.organization_id,
            actor_user_id=job.created_by_user_id,
            extra={
                "exam_type": job.exam_type,
                "questions": len(judgments),
                "model": judgments[0][3].model if judgments else None,
                "prompt_version": AUDIT_PROMPT_VERSION,
                "samples": settings.INTEGRITY_AUDIT_SAMPLES,
                "provider": self._gateway.provider,
                "alignment": counts,
            },
        )
        return {"audited": len(judgments), **{k.lower(): v for k, v in counts.items()}}

    async def fail(self, error: str) -> None:
        """Undo the job's unsaved work and record why it failed."""
        await self._session.rollback()
        job = await self._session.get(IntegrityJob, self._job_id, populate_existing=True)
        job.status = "FAILED"
        job.error = error[:2000]
        self._job = job
        if job.kind == "READ_PAPER":
            paper = await _paper(self._session, job.section_offering_id, job.exam_type)
            if paper is not None:
                paper.extraction_status = "FAILED"
                paper.extraction_error = error[:2000]
                write_audit_log(
                    self._session,
                    entity_type="question_paper",
                    entity_id=paper.id,
                    action="QUESTION_PAPER_FAILED",
                    org_id=job.organization_id,
                    actor_user_id=job.created_by_user_id,
                    after_status="FAILED",
                    extra={"exam_type": job.exam_type, "error": error[:300]},
                )
