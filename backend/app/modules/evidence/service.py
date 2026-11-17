"""Accreditation evidence writer: reference documents, retrieval, drafting and checking."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.gateway import AIGateway, BackendFactory
from app.modules.ai.providers import AIError
from app.modules.audit.writer import write_audit_log
from app.modules.authoring.outline import OutlineUnreadableError, document_text
from app.modules.curriculum.models import Curriculum
from app.modules.evidence import writer
from app.modules.evidence.models import EvidenceDraft, ReferenceDocument, ReferencePassage
from app.modules.evidence.records import gather_records
from app.modules.evidence.schemas import DraftRequest, DraftResponse
from app.modules.iam.models import User
from app.modules.integrity import documents
from app.modules.org.models import Program

# Program records hold class-level figures and course text only, like outcome authoring.
FEATURE = "authoring"
MAX_DOCUMENT_BYTES = 10_000_000


class _Error(HTTPException):
    def __init__(self, code: int, detail: str):
        super().__init__(status_code=code, detail=detail)


class EvidenceService:
    def __init__(self, session: AsyncSession, user: User, backend_factory: BackendFactory | None = None) -> None:
        self.db = session
        self.user = user
        self.backend_factory = backend_factory

    @property
    def org(self) -> UUID:
        return self.user.organization_id

    # ── Reference documents ─────────────────────────────────────────────────

    async def list_documents(self) -> list[ReferenceDocument]:
        return list((await self.db.execute(
            select(ReferenceDocument).where(ReferenceDocument.organization_id == self.org)
            .order_by(ReferenceDocument.created_at.desc())
        )).scalars().all())

    async def add_document(self, title: str | None, filename: str, content_type: str | None, data: bytes) -> ReferenceDocument:
        if len(data) > MAX_DOCUMENT_BYTES:
            raise _Error(413, "The file is larger than 10 MB.")
        name = (filename or "document").lower()
        if name.endswith(".txt") or (content_type or "").startswith("text/"):
            text = data.decode("utf-8", errors="replace")
        else:
            kind = documents.DOCX_TYPE if name.endswith(".docx") else documents.PDF_TYPE if name.endswith(".pdf") else content_type
            try:
                text = document_text(data, kind or "")
            except OutlineUnreadableError as exc:
                raise _Error(422, str(exc).replace("outline", "document")) from exc
        passages = writer.split_passages(text)
        if not passages:
            raise _Error(422, "No readable text was found in the document.")
        document = ReferenceDocument(
            organization_id=self.org,
            title=(title or filename or "Reference document").strip()[:255],
            filename=(filename or "document")[:255],
            sha256=hashlib.sha256(data).hexdigest(),
            passage_count=len(passages),
            created_by_user_id=self.user.id,
        )
        self.db.add(document)
        await self.db.flush()
        self.db.add_all([
            ReferencePassage(organization_id=self.org, document_id=document.id, ordinal=n,
                             heading=p.heading, text=p.text)
            for n, p in enumerate(passages)
        ])
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def delete_document(self, document_id: UUID) -> None:
        document = (await self.db.execute(select(ReferenceDocument).where(and_(
            ReferenceDocument.id == document_id, ReferenceDocument.organization_id == self.org,
        )))).scalar_one_or_none()
        if document is None:
            raise _Error(404, "Document not found")
        await self.db.execute(delete(ReferencePassage).where(ReferencePassage.document_id == document.id))
        await self.db.delete(document)
        await self.db.commit()

    async def search(self, *texts: str | None, limit: int = writer.MAX_PASSAGES) -> list[tuple[ReferencePassage, str]]:
        """Passages that best match the criterion, by full-text rank (OR over its words)."""
        terms = writer.search_terms(*texts)
        if not terms:
            return []
        query = func.to_tsquery("english", " | ".join(terms))
        rank = func.ts_rank_cd(ReferencePassage.tsv, query)
        rows = (await self.db.execute(
            select(ReferencePassage, ReferenceDocument.title)
            .join(ReferenceDocument, ReferenceDocument.id == ReferencePassage.document_id)
            .where(ReferencePassage.organization_id == self.org, ReferencePassage.tsv.op("@@")(query))
            .order_by(rank.desc(), ReferencePassage.ordinal)
            .limit(limit)
        )).all()
        return [(passage, title) for passage, title in rows]

    # ── Drafts ──────────────────────────────────────────────────────────────

    async def _program_curriculum(self, program_id: UUID, curriculum_id: UUID) -> Curriculum:
        program = (await self.db.execute(select(Program).where(and_(
            Program.id == program_id, Program.organization_id == self.org,
        )))).scalar_one_or_none()
        curriculum = (await self.db.execute(select(Curriculum).where(and_(
            Curriculum.id == curriculum_id, Curriculum.organization_id == self.org,
        )))).scalar_one_or_none()
        if program is None or curriculum is None or curriculum.program_id != program_id:
            raise _Error(404, "Program or curriculum not found")
        return curriculum

    async def draft(self, program_id: UUID, body: DraftRequest) -> DraftResponse:
        await self._program_curriculum(program_id, body.curriculum_id)
        records = await gather_records(self.db, self.org, program_id, body.curriculum_id)
        if not records:
            raise _Error(422, "This curriculum has no outcomes or results yet, so there is nothing to cite.")
        sources: dict[str, dict] = {
            f"E{n}": {"kind": r.kind, "label": r.label, "text": r.text} for n, r in enumerate(records, 1)
        }
        for n, (passage, title) in enumerate(await self.search(body.criterion_title, body.criterion_guidance), 1):
            label = f"{title}" + (f" — {passage.heading}" if passage.heading else "")
            sources[f"M{n}"] = {"kind": "manual", "label": label, "text": passage.text,
                                "document_id": str(passage.document_id)}

        gateway = await AIGateway.for_feature(
            self.db, feature=FEATURE, organization_id=self.org, user_id=self.user.id,
            backend_factory=self.backend_factory,
        )
        if not gateway.available:
            raise _Error(503, f"The evidence writer is not available: {gateway.unavailable_reason()}.")
        await self.db.commit()  # release the connection during the model call
        try:
            completion = await gateway.complete_json(
                purpose="draft_accreditation_evidence",
                prompt=writer.build_prompt(body.criterion_title, body.criterion_guidance, sources),
                schema=writer.evidence_schema(list(sources)),
                prompt_version=writer.EVIDENCE_PROMPT_VERSION,
                temperature=0.2,
            )
        except AIError as exc:
            gateway.record_usage(self.db)
            await self.db.commit()
            raise _Error(502, f"The AI model could not write the draft: {exc}. Please try again.") from exc

        sentences = writer.check_sentences(completion.data.get("sentences"), sources)
        if not sentences:
            gateway.record_usage(self.db)
            await self.db.commit()
            raise _Error(502, "The AI model returned no sentences. Please try again.")
        missing = [str(m).strip()[:300] for m in completion.data.get("missing") or [] if str(m).strip()][:10]
        draft = EvidenceDraft(
            organization_id=self.org,
            program_id=program_id,
            curriculum_id=body.curriculum_id,
            criterion_title=body.criterion_title.strip(),
            criterion_guidance=(body.criterion_guidance or "").strip() or None,
            sentences=sentences,
            missing=missing,
            sources=sources,
            provider=gateway.provider,
            model=completion.model[:100],
            prompt_version=writer.EVIDENCE_PROMPT_VERSION,
            created_by_user_id=self.user.id,
        )
        self.db.add(draft)
        gateway.record_usage(self.db)
        await self.db.flush()
        write_audit_log(
            self.db, entity_type="program", entity_id=program_id, action="AI_EVIDENCE_DRAFT",
            org_id=self.org, actor_user_id=self.user.id,
            extra={"draft_id": str(draft.id), "model": draft.model, "prompt_version": draft.prompt_version,
                   "sentences": len(sentences), "to_check": sum(s["status"] == "check" for s in sentences),
                   "sources": len(sources)},
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return _response(draft)

    async def list_drafts(self, program_id: UUID, curriculum_id: UUID) -> list[DraftResponse]:
        await self._program_curriculum(program_id, curriculum_id)
        rows = (await self.db.execute(
            select(EvidenceDraft).where(and_(
                EvidenceDraft.organization_id == self.org, EvidenceDraft.program_id == program_id,
                EvidenceDraft.curriculum_id == curriculum_id,
            )).order_by(EvidenceDraft.created_at.desc()).limit(20)
        )).scalars().all()
        return [_response(r) for r in rows]

    async def decide(self, draft_id: UUID, decision: str, edited_text: str | None) -> DraftResponse:
        draft = (await self.db.execute(select(EvidenceDraft).where(and_(
            EvidenceDraft.id == draft_id, EvidenceDraft.organization_id == self.org,
        )))).scalar_one_or_none()
        if draft is None:
            raise _Error(status.HTTP_404_NOT_FOUND, "Draft not found")
        draft.status = decision
        draft.edited_text = (edited_text or "").strip() or None
        draft.decided_by_user_id = self.user.id
        draft.decided_at = datetime.now(UTC)
        write_audit_log(
            self.db, entity_type="program", entity_id=draft.program_id, action=f"AI_EVIDENCE_{decision}",
            org_id=self.org, actor_user_id=self.user.id,
            extra={"draft_id": str(draft.id), "edited": draft.edited_text is not None},
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return _response(draft)


def _response(draft: EvidenceDraft) -> DraftResponse:
    return DraftResponse(
        id=draft.id,
        program_id=draft.program_id,
        curriculum_id=draft.curriculum_id,
        criterion_title=draft.criterion_title,
        criterion_guidance=draft.criterion_guidance,
        sentences=draft.sentences,
        missing=draft.missing or [],
        sources=draft.sources,
        status=draft.status,
        edited_text=draft.edited_text,
        model=draft.model,
        prompt_version=draft.prompt_version,
        created_at=draft.created_at,
        decided_at=draft.decided_at,
    )
