"""
Outcome authoring: AI drafts course outcomes, improves a teacher's CO statement, and
suggests CO-PO links.

Every suggestion is advisory. Drafts and refinements are returned to the teacher,
who saves them through the normal CO endpoints. Mapping suggestions are checked
against the program's mapping rules (app/modules/obe/mapping_rules.py) before they
are shown, and again when the teacher applies them.
"""
import hashlib
import re
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.gateway import AIGateway, BackendFactory
from app.modules.ai.providers import AIError, Completion
from app.modules.audit.writer import write_audit_log
from app.modules.authoring import outline, prompts
from app.modules.authoring.context import (
    Attribute,
    CourseContext,
    Level,
    Outcome,
    ProgramOutcomeInfo,
    load_course_context,
)
from app.modules.authoring.exceptions import (
    ApplyPermissionError,
    AuthoringModelError,
    AuthoringUnavailableError,
    MappingRuleError,
    NothingToMapError,
    SuggestionNotFoundError,
)
from app.modules.authoring.models import OutcomeSuggestion
from app.modules.authoring.quality import LevelInfo, check_statement, strip_prefix
from app.modules.authoring.schemas import (
    ApplyRequest,
    ApplyResponse,
    BloomRef,
    DecisionRequest,
    DraftedOutcome,
    DraftRequest,
    DraftResponse,
    ExistingLink,
    MappingSuggestRequest,
    MappingSuggestResponse,
    OutlineApplyRequest,
    OutlineApplyResponse,
    OutlineCurrent,
    OutlineOutcome,
    OutlinePreview,
    OutlineTopic,
    RefineRequest,
    RefineResponse,
    SuggestedAttribute,
    SuggestedLink,
)
from app.modules.curriculum.models import Course, CourseLessonPlanItem, CourseObjective
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.obe.mapping_rules import (
    MappingFacts,
    load_facts,
    natural_key,
    needs_cea,
    needs_cep,
)
from app.modules.obe.models import (
    COCAMapping,
    COCPMapping,
    COKPMapping,
    COPOMappingSet,
    CourseOutcome,
    CourseOutcomeBloomLevel,
    ProgramOutcome,
)
from app.modules.obe.repository import MappingEntryRepository, MappingSetRepository
from app.modules.ref_data.models import (
    BloomLevel,
    ComplexActivity,
    ComplexProblem,
    KnowledgeProfile,
)

FEATURE = "authoring"
MAX_STATEMENT = 1000
MAX_JUSTIFICATION = 1000

_SPACES = re.compile(r"\s+")


def _clean_text(value, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return _SPACES.sub(" ", value).strip()[:limit]


def clean_statement(value) -> str:
    """Tidy a model-written statement: one line, no "Students will be able to", a full stop."""
    text = strip_prefix(_clean_text(value, MAX_STATEMENT))
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    if text[-1].isalnum() or text[-1] in ")]\"'":
        text += "."
    return text


def _bloom_refs(levels: Iterable[Level]) -> list[BloomRef]:
    return [BloomRef(id=lvl.id, code=lvl.code, name=lvl.name) for lvl in levels]


def _level_infos(levels: Iterable[Level]) -> list[LevelInfo]:
    return [LevelInfo(code=lvl.code, name=lvl.name) for lvl in levels]


def _resolve_levels(ctx: CourseContext, codes) -> list[Level]:
    if not isinstance(codes, list):
        return []
    by_code: dict[str, Level] = {}
    for lvl in ctx.levels:
        by_code.setdefault(lvl.code.upper(), lvl)
    found: list[Level] = []
    for code in codes:
        lvl = by_code.get(str(code).strip().upper())
        if lvl and lvl not in found:
            found.append(lvl)
    return found[:2]


def _has_permission(manifest: PermissionManifestResponse, code: str) -> bool:
    return manifest.is_super_admin or code in manifest.permissions


class AuthoringService:
    def __init__(self, session: AsyncSession, user: User, backend_factory: BackendFactory) -> None:
        self.db = session
        self.user = user
        self.backend_factory = backend_factory

    # ── Model calls ───────────────────────────────────────────────────────────

    async def _gateway(self) -> AIGateway:
        gateway = await AIGateway.for_feature(
            self.db,
            feature=FEATURE,
            organization_id=self.user.organization_id,
            user_id=self.user.id,
            backend_factory=self.backend_factory,
        )
        if not gateway.available:
            raise AuthoringUnavailableError(gateway.unavailable_reason())
        return gateway

    async def _complete(
        self,
        gateway: AIGateway,
        *,
        purpose: str,
        prompt: str,
        schema: dict,
        prompt_version: str,
        temperature: float,
    ) -> Completion:
        # End the read transaction so the connection is free while the model works.
        await self.db.commit()
        try:
            return await gateway.complete_json(
                purpose=purpose, prompt=prompt, schema=schema,
                prompt_version=prompt_version, temperature=temperature,
            )
        except AIError as exc:
            gateway.record_usage(self.db)
            await self.db.commit()
            raise AuthoringModelError(str(exc)) from exc

    def _record(
        self,
        gateway: AIGateway,
        ctx: CourseContext,
        *,
        kind: str,
        request: dict,
        result: dict,
        completion: Completion,
        prompt_version: str,
    ) -> OutcomeSuggestion:
        suggestion = OutcomeSuggestion(
            organization_id=ctx.organization_id,
            curriculum_id=ctx.curriculum_id,
            course_id=ctx.course_id,
            user_id=self.user.id,
            kind=kind,
            request=request,
            result=result,
            provider=gateway.provider,
            model=completion.model[:100],
            prompt_version=prompt_version,
        )
        self.db.add(suggestion)
        gateway.record_usage(self.db)
        return suggestion

    async def _audit(self, suggestion: OutcomeSuggestion, action: str, extra: dict) -> None:
        await self.db.flush()
        write_audit_log(
            self.db,
            entity_type="course",
            entity_id=suggestion.course_id,
            action=action,
            org_id=suggestion.organization_id,
            actor_user_id=self.user.id,
            extra={
                "suggestion_id": str(suggestion.id),
                "kind": suggestion.kind,
                "provider": suggestion.provider,
                "model": suggestion.model,
                "prompt_version": suggestion.prompt_version,
                **extra,
            },
        )

    # ── Draft COs ─────────────────────────────────────────────────────────────

    async def draft(self, body: DraftRequest) -> DraftResponse:
        ctx = await load_course_context(
            self.db, self.user.organization_id, body.curriculum_id, body.course_id
        )
        gateway = await self._gateway()
        completion = await self._complete(
            gateway,
            purpose="draft_course_outcomes",
            prompt=prompts.draft_prompt(ctx, body.count, body.instruction),
            schema=prompts.draft_schema(ctx, body.count),
            prompt_version=prompts.CO_DRAFT_PROMPT_VERSION,
            temperature=0.5,
        )

        raw = completion.data.get("outcomes")
        others = [(co.code, co.statement) for co in ctx.outcomes]
        outcomes: list[DraftedOutcome] = []
        for item in raw if isinstance(raw, list) else []:
            if len(outcomes) >= body.count or not isinstance(item, dict):
                continue
            statement = clean_statement(item.get("statement"))
            if len(statement) < 10:
                continue
            levels = _resolve_levels(ctx, item.get("bloom_codes"))
            outcomes.append(DraftedOutcome(
                statement=statement,
                bloom_levels=_bloom_refs(levels),
                rationale=_clean_text(item.get("rationale"), 500),
                warnings=check_statement(statement, levels=_level_infos(levels), others=others),
            ))
            others.append((f"draft {len(outcomes)}", statement))
        if not outcomes:
            gateway.record_usage(self.db)
            await self.db.commit()
            raise AuthoringModelError("it returned no usable course outcomes")

        result = {"outcomes": [o.model_dump(mode="json") for o in outcomes]}
        suggestion = self._record(
            gateway, ctx, kind="CO_DRAFT",
            request={"count": body.count, "instruction": body.instruction},
            result=result, completion=completion,
            prompt_version=prompts.CO_DRAFT_PROMPT_VERSION,
        )
        await self._audit(suggestion, "AI_CO_DRAFTED", {"count": len(outcomes)})
        await self.db.commit()
        return DraftResponse(
            suggestion_id=suggestion.id, model=suggestion.model,
            prompt_version=suggestion.prompt_version, outcomes=outcomes,
        )

    # ── Refine a CO ───────────────────────────────────────────────────────────

    async def refine(self, body: RefineRequest) -> RefineResponse:
        ctx = await load_course_context(
            self.db, self.user.organization_id, body.curriculum_id, body.course_id
        )
        current = ctx.levels_for(body.bloom_level_ids)
        others = [(co.code, co.statement) for co in ctx.outcomes if co.id != body.course_outcome_id]
        original_warnings = check_statement(
            body.statement, levels=_level_infos(current), others=others
        )

        gateway = await self._gateway()
        completion = await self._complete(
            gateway,
            purpose="refine_course_outcome",
            prompt=prompts.refine_prompt(
                ctx, body.statement, [lvl.code for lvl in current], body.instruction,
                exclude_id=body.course_outcome_id,
            ),
            schema=prompts.refine_schema(ctx),
            prompt_version=prompts.CO_REFINE_PROMPT_VERSION,
            temperature=0.2,
        )

        statement = clean_statement(completion.data.get("statement"))
        if len(statement) < 10:
            gateway.record_usage(self.db)
            await self.db.commit()
            raise AuthoringModelError("it returned no usable statement")
        levels = _resolve_levels(ctx, completion.data.get("bloom_codes")) or [
            lvl for lvl in current if lvl in ctx.levels
        ]
        raw_changes = completion.data.get("changes")
        changes = [
            text for text in (_clean_text(c, 300) for c in (raw_changes if isinstance(raw_changes, list) else []))
            if text
        ][:8]
        response_fields = {
            "statement": statement,
            "bloom_levels": _bloom_refs(levels),
            "changes": changes,
            "warnings": check_statement(statement, levels=_level_infos(levels), others=others),
            "original_warnings": original_warnings,
        }

        suggestion = self._record(
            gateway, ctx, kind="CO_REFINE",
            request={
                "statement": body.statement,
                "bloom_level_ids": [str(i) for i in body.bloom_level_ids],
                "instruction": body.instruction,
                "course_outcome_id": str(body.course_outcome_id) if body.course_outcome_id else None,
            },
            result={
                **response_fields,
                "bloom_levels": [b.model_dump(mode="json") for b in response_fields["bloom_levels"]],
            },
            completion=completion,
            prompt_version=prompts.CO_REFINE_PROMPT_VERSION,
        )
        await self._audit(suggestion, "AI_CO_REFINED", {
            "course_outcome_id": str(body.course_outcome_id) if body.course_outcome_id else None,
        })
        await self.db.commit()
        return RefineResponse(
            suggestion_id=suggestion.id, model=suggestion.model,
            prompt_version=suggestion.prompt_version, **response_fields,
        )

    # ── CO-PO mapping suggestions ─────────────────────────────────────────────

    async def _mapping_set(self, curriculum_id: UUID, course_id: UUID) -> COPOMappingSet | None:
        """The set the mapping page shows: this curriculum's, else the course's latest."""
        repo = MappingSetRepository(self.db)
        found = await repo.find_by_curriculum_course(curriculum_id, course_id)
        return found or await repo.find_by_course_fallback(course_id)

    async def suggest_mapping(self, body: MappingSuggestRequest) -> MappingSuggestResponse:
        ctx = await load_course_context(
            self.db, self.user.organization_id, body.curriculum_id, body.course_id,
            with_attributes=True,
        )
        if not ctx.outcomes:
            raise NothingToMapError("This course has no course outcomes yet. Add COs first.")
        if not ctx.program_outcomes:
            raise NothingToMapError("No program outcomes were found for this course's program.")
        targets = ctx.outcomes
        if body.course_outcome_ids:
            wanted = set(body.course_outcome_ids)
            targets = [co for co in ctx.outcomes if co.id in wanted]
            if len(targets) != len(wanted):
                raise NothingToMapError("A chosen course outcome is not part of this course.")
        target_ids = {co.id for co in targets}

        mapping_set = await self._mapping_set(body.curriculum_id, body.course_id)
        existing: set[tuple[UUID, UUID]] = set()
        if mapping_set:
            entries = await MappingEntryRepository(self.db).list_by_set(mapping_set.id)
            existing = {(e.course_outcome_id, e.program_outcome_id) for e in entries}

        gateway = await self._gateway()
        completion = await self._complete(
            gateway,
            purpose="suggest_co_po_mapping",
            prompt=prompts.mapping_prompt(ctx, targets),
            schema=prompts.mapping_schema(ctx, targets),
            prompt_version=prompts.CO_PO_PROMPT_VERSION,
            temperature=0.0,
        )

        links = build_links(ctx, completion.data.get("mappings"), existing, targets=targets)
        suggested_pairs = {(link.course_outcome_id, link.program_outcome_id) for link in links}
        co_codes = {co.id: co.code for co in ctx.outcomes}
        po_codes = {po.id: po.code for po in ctx.program_outcomes}
        existing_not_suggested = sorted(
            (
                ExistingLink(co_code=co_codes[co_id], po_code=po_codes[po_id])
                for co_id, po_id in existing - suggested_pairs
                if co_id in target_ids and co_id in co_codes and po_id in po_codes
            ),
            key=lambda link: (natural_key(link.co_code), natural_key(link.po_code)),
        )
        pos_without_kp = [po.code for po in ctx.program_outcomes if not po.kp_ids]

        target_codes = [co.code for co in targets]
        result = {
            "course_outcome_codes": target_codes,
            "links": [link.model_dump(mode="json") for link in links],
            "pos_without_knowledge_profiles": pos_without_kp,
            "existing_not_suggested": [link.model_dump() for link in existing_not_suggested],
        }
        suggestion = self._record(
            gateway, ctx, kind="CO_PO_MAPPING",
            request={"course_outcome_ids": [str(i) for i in body.course_outcome_ids]}
            if body.course_outcome_ids else {},
            result=result, completion=completion,
            prompt_version=prompts.CO_PO_PROMPT_VERSION,
        )
        await self._audit(suggestion, "AI_CO_PO_SUGGESTED", {
            "links": len(links), "applicable": sum(link.can_apply for link in links),
            "course_outcomes": target_codes,
        })
        await self.db.commit()
        return MappingSuggestResponse(
            suggestion_id=suggestion.id, model=suggestion.model,
            prompt_version=suggestion.prompt_version, course_outcome_codes=target_codes, links=links,
            pos_without_knowledge_profiles=pos_without_kp,
            existing_not_suggested=existing_not_suggested,
        )

    async def apply_mapping(
        self, suggestion_id: UUID, body: ApplyRequest, manifest: PermissionManifestResponse
    ) -> ApplyResponse:
        suggestion = await self._suggestion(suggestion_id, kind="CO_PO_MAPPING")
        links = [SuggestedLink.model_validate(raw) for raw in suggestion.result.get("links", [])]
        items = {item.index: item for item in body.items}
        if any(index >= len(links) for index in items):
            raise NothingToMapError("A chosen link is not part of this suggestion.")

        chosen = [(links[index], item) for index, item in sorted(items.items())]
        co_ids = {link.course_outcome_id for link, _ in chosen}
        po_ids = {link.program_outcome_id for link, _ in chosen}
        await self._require_current(suggestion, co_ids, po_ids)

        mapping_set = await self._mapping_set(suggestion.curriculum_id, suggestion.course_id)
        entry_repo = MappingEntryRepository(self.db)
        existing = {
            (e.course_outcome_id, e.program_outcome_id)
            for e in (await entry_repo.list_by_set(mapping_set.id) if mapping_set else [])
        }

        def is_mapped(link: SuggestedLink) -> bool:
            return (link.course_outcome_id, link.program_outcome_id) in existing

        to_apply = [(link, item) for link, item in chosen if not is_mapped(link)]
        already = [link.index for link, _ in chosen if is_mapped(link)]

        # Everything the chosen links add to their COs, applied together.
        adds: dict[str, dict[UUID, dict[UUID, str]]] = {
            "kp": defaultdict(dict), "cep": defaultdict(dict), "cea": defaultdict(dict),
        }
        for link, _ in to_apply:
            for kind, attrs in (("kp", link.knowledge_profiles), ("cep", link.complex_problems),
                                ("cea", link.complex_activities)):
                for attr in attrs:
                    if not attr.already_mapped:
                        adds[kind][link.course_outcome_id].setdefault(attr.id, attr.justification)
        for kind, permission, label in (
            ("kp", "mapping.co_kp.manage", "knowledge profile mappings"),
            ("cep", "mapping.co_cp.manage", "complex engineering problem mappings"),
            ("cea", "mapping.co_ca.manage", "complex engineering activity mappings"),
        ):
            if any(adds[kind].values()) and not _has_permission(manifest, permission):
                raise ApplyPermissionError(label)
        await self._require_attributes(suggestion.organization_id, adds)

        facts = await load_facts(self.db, co_ids, po_ids)
        problems: list[str] = []
        for link, item in to_apply:
            co_id = link.course_outcome_id
            check = facts.check(
                co_id, link.program_outcome_id,
                added_kp_ids=adds["kp"][co_id].keys(),
                adds_cep=bool(adds["cep"][co_id]),
                adds_cea=bool(adds["cea"][co_id]),
            )
            pair = f"{link.co_code} → {link.po_code}"
            if check.missing_kp:
                needed = ", ".join(facts.required_kp_codes(link.program_outcome_id))
                problems.append(f"{pair} needs one of {needed}.")
            if check.missing_cep:
                problems.append(f"{pair} needs a complex engineering problem (CEP).")
            if check.missing_cea:
                problems.append(f"{pair} needs a complex engineering activity (CEA).")
            if not (_clean_text(item.justification, MAX_JUSTIFICATION) or link.justification):
                problems.append(f"{pair} has no justification.")
        if problems:
            raise MappingRuleError(problems)

        # Every rule holds: write the links and the mappings they need.
        if mapping_set is None:
            mapping_set = COPOMappingSet(
                organization_id=suggestion.organization_id,
                curriculum_id=suggestion.curriculum_id,
                course_id=suggestion.course_id,
                created_by_user_id=self.user.id,
            )
            self.db.add(mapping_set)
            await self.db.flush()
        counts = await self._add_attributes(suggestion.organization_id, adds)
        edited = []
        for link, item in to_apply:
            justification = _clean_text(item.justification, MAX_JUSTIFICATION) or link.justification
            weight = item.weight or link.weight
            if weight != link.weight or justification != link.justification:
                edited.append(link.index)
            await entry_repo.upsert(
                mapping_set.id, link.course_outcome_id, link.program_outcome_id, weight, justification
            )

        applied = [link.index for link, _ in to_apply]
        detail = dict(suggestion.decision_detail or {})
        detail["applied"] = sorted(set(detail.get("applied", [])) | set(applied))
        detail["edited"] = sorted(set(detail.get("edited", [])) | set(edited))
        applicable = {link.index for link in links if link.can_apply}
        if detail["edited"]:
            suggestion.decision = "EDITED"
        elif applicable and applicable <= set(detail["applied"]):
            suggestion.decision = "ACCEPTED"
        else:
            suggestion.decision = "PARTIAL"
        suggestion.decision_detail = detail
        suggestion.decided_at = datetime.now(timezone.utc)

        write_audit_log(
            self.db,
            entity_type="co_po_mapping_set",
            entity_id=mapping_set.id,
            action="AI_CO_PO_APPLIED",
            org_id=suggestion.organization_id,
            actor_user_id=self.user.id,
            extra={
                "suggestion_id": str(suggestion.id),
                "model": suggestion.model,
                "prompt_version": suggestion.prompt_version,
                "links": [f"{link.co_code}-{link.po_code}" for link, _ in to_apply],
                "edited": edited,
                **counts,
            },
        )
        await self.db.commit()
        return ApplyResponse(
            mapping_set_id=mapping_set.id,
            applied=applied,
            already_mapped=already,
            **counts,
        )

    async def _require_current(
        self, suggestion: OutcomeSuggestion, co_ids: set[UUID], po_ids: set[UUID]
    ) -> None:
        """The COs and POs a suggestion names must still exist and be in use."""
        found_cos = set((await self.db.execute(select(CourseOutcome.id).where(and_(
            CourseOutcome.id.in_(co_ids),
            CourseOutcome.organization_id == suggestion.organization_id,
            CourseOutcome.course_id == suggestion.course_id,
        )))).scalars().all())
        found_pos = set((await self.db.execute(select(ProgramOutcome.id).where(and_(
            ProgramOutcome.id.in_(po_ids),
            ProgramOutcome.organization_id == suggestion.organization_id,
            ProgramOutcome.status == "ACTIVE",
        )))).scalars().all())
        if found_cos != co_ids or found_pos != po_ids:
            raise NothingToMapError(
                "Some outcomes in this suggestion have changed or been removed. Ask for new suggestions."
            )

    async def _require_attributes(
        self, organization_id: UUID, adds: dict[str, dict[UUID, dict[UUID, str]]]
    ) -> None:
        """Knowledge profiles, CEPs and CEAs a suggestion adds must still be active."""
        for kind, model in (("kp", KnowledgeProfile), ("cep", ComplexProblem), ("cea", ComplexActivity)):
            wanted = set().union(*(attrs.keys() for attrs in adds[kind].values()))
            if not wanted:
                continue
            found = set((await self.db.execute(select(model.id).where(and_(
                model.id.in_(wanted), model.organization_id == organization_id, model.is_active.is_(True),
            )))).scalars().all())
            if found != wanted:
                raise NothingToMapError(
                    "A knowledge profile or complex attribute in this suggestion has been removed. "
                    "Ask for new suggestions."
                )

    async def _add_attributes(
        self, organization_id: UUID, adds: dict[str, dict[UUID, dict[UUID, str]]]
    ) -> dict[str, int]:
        specs = (
            ("kp", COKPMapping, COKPMapping.knowledge_profile_id, "knowledge_profile_id",
             "added_knowledge_profiles"),
            ("cep", COCPMapping, COCPMapping.complex_problem_id, "complex_problem_id",
             "added_complex_problems"),
            ("cea", COCAMapping, COCAMapping.complex_activity_id, "complex_activity_id",
             "added_complex_activities"),
        )
        counts: dict[str, int] = {}
        for kind, model, column, field_name, count_key in specs:
            wanted = adds[kind]
            counts[count_key] = 0
            if not any(wanted.values()):
                continue
            present = set((await self.db.execute(
                select(model.course_outcome_id, column).where(model.course_outcome_id.in_(wanted))
            )).all())
            for co_id, attrs in wanted.items():
                for attr_id, justification in attrs.items():
                    if (co_id, attr_id) in present:
                        continue
                    self.db.add(model(
                        organization_id=organization_id,
                        course_outcome_id=co_id,
                        justification=justification,
                        created_by_user_id=self.user.id,
                        **{field_name: attr_id},
                    ))
                    counts[count_key] += 1
        await self.db.flush()
        return counts

    # ── Course outline import ─────────────────────────────────────────────────

    async def read_outline(
        self, curriculum_id: UUID, course_id: UUID, filename: str, content_type: str, data: bytes
    ) -> OutlinePreview:
        ctx = await load_course_context(self.db, self.user.organization_id, curriculum_id, course_id)
        try:
            document = outline.document_text(data, content_type)
        except outline.OutlineUnreadableError as exc:
            raise NothingToMapError(str(exc)) from exc

        gateway = await self._gateway()
        completion = await self._complete(
            gateway,
            purpose="read_course_outline",
            prompt=outline.build_prompt(ctx, document),
            schema=outline.outline_schema([lvl.code for lvl in ctx.all_levels]),
            prompt_version=outline.OUTLINE_PROMPT_VERSION,
            temperature=0.0,
        )
        preview = _outline_preview(ctx, completion.data, document, filename)
        if not (preview.outcomes or preview.objectives or preview.topics or preview.description):
            gateway.record_usage(self.db)
            await self.db.commit()
            raise AuthoringModelError("it found no course details in this document")

        suggestion = self._record(
            gateway, ctx, kind="OUTLINE_IMPORT",
            request={
                "filename": filename[:255],
                "content_type": content_type,
                "sha256": hashlib.sha256(data).hexdigest(),
                "characters": len(document),
            },
            result=preview.model_dump(mode="json", exclude={"suggestion_id", "model", "prompt_version"}),
            completion=completion,
            prompt_version=outline.OUTLINE_PROMPT_VERSION,
        )
        await self._audit(suggestion, "AI_OUTLINE_READ", {
            "filename": filename[:255], "outcomes": len(preview.outcomes),
            "objectives": len(preview.objectives), "topics": len(preview.topics),
        })
        await self.db.commit()
        return preview.model_copy(update={
            "suggestion_id": suggestion.id, "model": suggestion.model,
            "prompt_version": suggestion.prompt_version,
        })

    async def apply_outline(
        self, suggestion_id: UUID, body: OutlineApplyRequest, manifest: PermissionManifestResponse
    ) -> OutlineApplyResponse:
        suggestion = await self._suggestion(suggestion_id, kind="OUTLINE_IMPORT")
        course_parts = body.description is not None or body.objectives is not None or body.topics is not None
        if course_parts and not _has_permission(manifest, "course.update"):
            raise ApplyPermissionError("course details")
        if body.outcomes and not _has_permission(manifest, "co.create"):
            raise ApplyPermissionError("course outcomes")
        course = (await self.db.execute(select(Course).where(and_(
            Course.id == suggestion.course_id, Course.organization_id == suggestion.organization_id,
        )))).scalar_one_or_none()
        if course is None:
            raise SuggestionNotFoundError()

        result = OutlineApplyResponse(
            description=False, objectives=0, outcomes_added=[], outcomes_skipped=[],
            syllabus=False, lesson_items=0, lesson_plan_kept=False,
        )
        if body.description is not None and body.description.strip():
            course.description = body.description.strip()
            result.description = True

        if body.objectives is not None:
            statements = [o.strip() for o in body.objectives if o.strip()]
            await self.db.execute(delete(CourseObjective).where(CourseObjective.course_id == course.id))
            self.db.add_all([
                CourseObjective(course_id=course.id, order_index=i, statement=text)
                for i, text in enumerate(statements, 1)
            ])
            result.objectives = len(statements)

        if body.outcomes:
            existing = set((await self.db.execute(select(CourseOutcome.code).where(and_(
                CourseOutcome.curriculum_id == suggestion.curriculum_id,
                CourseOutcome.course_id == course.id,
            )))).scalars().all())
            existing_upper = {code.upper() for code in existing}
            level_ids = set((await self.db.execute(select(BloomLevel.id).where(and_(
                BloomLevel.organization_id == suggestion.organization_id, BloomLevel.is_active.is_(True),
            )))).scalars().all())
            for item in body.outcomes:
                code = item.code.strip()
                if code.upper() in existing_upper:
                    result.outcomes_skipped.append(code)
                    continue
                co = CourseOutcome(
                    organization_id=suggestion.organization_id,
                    curriculum_id=suggestion.curriculum_id,
                    course_id=course.id,
                    code=code,
                    statement=item.statement.strip(),
                    created_by_user_id=self.user.id,
                )
                self.db.add(co)
                await self.db.flush()
                self.db.add_all([
                    CourseOutcomeBloomLevel(course_outcome_id=co.id, bloom_level_id=level_id)
                    for level_id in dict.fromkeys(item.bloom_level_ids) if level_id in level_ids
                ])
                existing_upper.add(code.upper())
                result.outcomes_added.append(code)

        if body.topics is not None:
            topics = [t for t in body.topics if t.topic.strip()]
            course.syllabus_content = "\n".join(f"{i}. {t.topic.strip()}" for i, t in enumerate(topics, 1))
            result.syllabus = True
            has_plan = await self.db.scalar(select(CourseLessonPlanItem.id).where(and_(
                CourseLessonPlanItem.curriculum_id == suggestion.curriculum_id,
                CourseLessonPlanItem.course_id == course.id,
            )).limit(1))
            if has_plan:
                result.lesson_plan_kept = True
            else:
                self.db.add_all([
                    CourseLessonPlanItem(
                        curriculum_id=suggestion.curriculum_id, course_id=course.id,
                        week_number=t.week or i, lesson_label=f"Lesson {i}",
                        topic=t.topic.strip(), order_index=i,
                    )
                    for i, t in enumerate(topics, 1)
                ])
                result.lesson_items = len(topics)

        parts = [name for name, value in (
            ("description", body.description), ("objectives", body.objectives),
            ("outcomes", body.outcomes), ("topics", body.topics),
        ) if value is not None]
        preview = suggestion.result or {}
        edited = (
            body.description is not None and body.description.strip() != (preview.get("description") or "")
        ) or (
            body.outcomes is not None
            and {(o.code, o.statement.strip()) for o in body.outcomes}
            - {(o["code"], o["statement"]) for o in preview.get("outcomes", [])}
        )
        suggestion.decision = "EDITED" if edited else ("ACCEPTED" if len(parts) == 4 else "PARTIAL")
        suggestion.decision_detail = {"parts": parts, **result.model_dump()}
        suggestion.decided_at = datetime.now(timezone.utc)
        write_audit_log(
            self.db,
            entity_type="course",
            entity_id=course.id,
            action="AI_OUTLINE_APPLIED",
            org_id=suggestion.organization_id,
            actor_user_id=self.user.id,
            extra={"suggestion_id": str(suggestion.id), "parts": parts, **result.model_dump()},
        )
        await self.db.commit()
        return result

    # ── Teacher's decision ────────────────────────────────────────────────────

    async def _suggestion(self, suggestion_id: UUID, kind: str | None = None) -> OutcomeSuggestion:
        suggestion = (await self.db.execute(select(OutcomeSuggestion).where(and_(
            OutcomeSuggestion.id == suggestion_id,
            OutcomeSuggestion.organization_id == self.user.organization_id,
        )))).scalar_one_or_none()
        if suggestion is None or (kind and suggestion.kind != kind):
            raise SuggestionNotFoundError()
        return suggestion

    async def record_decision(self, suggestion_id: UUID, body: DecisionRequest) -> OutcomeSuggestion:
        suggestion = await self._suggestion(suggestion_id)
        if suggestion.user_id != self.user.id:
            raise SuggestionNotFoundError()
        suggestion.decision = body.decision
        suggestion.decision_detail = body.detail
        suggestion.decided_at = datetime.now(timezone.utc)
        await self.db.commit()
        return suggestion


# ── Outline preview ───────────────────────────────────────────────────────────

def _outline_preview(ctx: CourseContext, data: dict, document: str, filename: str) -> OutlinePreview:
    lookup = outline.LevelLookup.for_context(ctx)
    existing = {co.code.upper(): co for co in ctx.outcomes}
    others = [(co.code, co.statement) for co in ctx.outcomes]

    outcomes: list[OutlineOutcome] = []
    seen: set[str] = set()
    raw_outcomes = data.get("outcomes")
    for position, item in enumerate(raw_outcomes if isinstance(raw_outcomes, list) else [], 1):
        if not isinstance(item, dict) or len(outcomes) >= 20:
            continue
        statement = clean_statement(item.get("statement"))
        if len(statement) < 10:
            continue
        code = outline.co_code(item.get("code"), position)
        if code in seen:
            continue
        seen.add(code)
        levels = lookup.resolve(item.get("bloom_codes"))
        stated = bool(item.get("bloom_stated")) and bool(levels)
        exists = code.upper() in existing
        warnings = check_statement(
            statement, levels=_level_infos(levels),
            others=[(label, text) for label, text in others if label.upper() != code.upper()],
        )
        if not outline.in_document(statement, document):
            warnings.insert(0, "Not found word for word in the document — check the wording.")
        if levels and not stated:
            warnings.append("The outline gives no Bloom level; the AI chose this one.")
        if exists:
            warnings.insert(0, f"{code} already exists in this course and will not be changed.")
        outcomes.append(OutlineOutcome(
            code=code, statement=statement, bloom_levels=_bloom_refs(levels),
            bloom_stated=stated, exists=exists, warnings=warnings,
        ))

    def texts(raw, limit: int, length: int) -> list[str]:
        items = [_clean_text(x, length) for x in (raw if isinstance(raw, list) else [])]
        return [x for x in items if x][:limit]

    topics: list[OutlineTopic] = []
    raw_topics = data.get("topics")
    for item in raw_topics if isinstance(raw_topics, list) else []:
        if not isinstance(item, dict) or len(topics) >= 40:
            continue
        topic = _clean_text(item.get("topic"), 300)
        week = item.get("week")
        week = week if isinstance(week, int) and 1 <= week <= 52 else None
        if topic:
            topics.append(OutlineTopic(week=week, topic=topic))

    warnings: list[str] = []
    code = _clean_text(data.get("course_code"), 40) or None
    if code and not outline.same_code(code, ctx.code):
        warnings.append(f"The outline is for {code}, but this course is {ctx.code}.")
    if not outcomes:
        warnings.append("No course outcomes were found in the document.")

    return OutlinePreview(
        suggestion_id=UUID(int=0), model="", prompt_version=outline.OUTLINE_PROMPT_VERSION,
        filename=filename,
        course_code=code,
        course_title=_clean_text(data.get("course_title"), 255) or None,
        description=_clean_text(data.get("description"), 3000) or None,
        objectives=texts(data.get("objectives"), 15, 400),
        outcomes=outcomes,
        topics=topics,
        warnings=warnings,
        current=OutlineCurrent(
            has_description=bool(ctx.description),
            objectives=len(ctx.objectives),
            outcome_codes=[co.code for co in ctx.outcomes],
            lesson_items=len(ctx.topics),
        ),
    )


# ── Turning the model's links into checked suggestions ────────────────────────

def _attributes(raw, by_code: dict[str, Attribute], fallback: str) -> list[tuple[Attribute, str]]:
    found: list[tuple[Attribute, str]] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        attr = by_code.get(str(item.get("code", "")).strip().upper())
        if attr and all(attr.id != a.id for a, _ in found):
            found.append((attr, _clean_text(item.get("justification"), MAX_JUSTIFICATION) or fallback))
    return found


def _existing(ids: Iterable[UUID], by_id: dict[UUID, Attribute], proposed: list[tuple[Attribute, str]]):
    reasons = {attr.id: why for attr, why in proposed}
    attrs = sorted((by_id[i] for i in ids if i in by_id), key=lambda a: natural_key(a.code))
    return [
        SuggestedAttribute(id=a.id, code=a.code, justification=reasons.get(a.id, ""), already_mapped=True)
        for a in attrs
    ]


def _added(proposed: list[tuple[Attribute, str]]) -> list[SuggestedAttribute]:
    return [
        SuggestedAttribute(id=a.id, code=a.code, justification=why, already_mapped=False)
        for a, why in proposed
    ]


def _domain_warning(ctx: CourseContext, co: Outcome, po: ProgramOutcomeInfo) -> str | None:
    if po.bloom_domain_id is None:
        return None
    co_levels = ctx.levels_for(co.bloom_level_ids)
    co_domains = {lvl.domain_id for lvl in co_levels}
    if not co_domains or po.bloom_domain_id in co_domains:
        return None
    names = {lvl.domain_id: lvl.domain_name for lvl in ctx.all_levels}
    po_domain = names.get(po.bloom_domain_id, "another")
    co_names = ", ".join(sorted({names.get(d, "?") for d in co_domains}))
    return (
        f"{po.code} is in the {po_domain} domain, but {co.code}'s Bloom levels are {co_names}."
    )


def build_links(
    ctx: CourseContext,
    raw,
    existing: set[tuple[UUID, UUID]],
    targets: list[Outcome] | None = None,
) -> list[SuggestedLink]:
    """Check the model's links against the rules; links for COs outside `targets` are dropped."""
    cos = {co.code.upper(): co for co in (ctx.outcomes if targets is None else targets)}
    pos = {po.code.upper(): po for po in ctx.program_outcomes}
    kps = {a.code.upper(): a for a in ctx.knowledge_profiles}
    ceps = {a.code.upper(): a for a in ctx.complex_problems}
    ceas = {a.code.upper(): a for a in ctx.complex_activities}
    kp_by_id = {a.id: a for a in ctx.knowledge_profiles}
    cep_by_id = {a.id: a for a in ctx.complex_problems}
    cea_by_id = {a.id: a for a in ctx.complex_activities}
    facts = MappingFacts(
        po_codes={po.id: po.code for po in ctx.program_outcomes},
        po_kp_ids={po.id: set(po.kp_ids) for po in ctx.program_outcomes},
        co_kp_ids={co.id: set(co.kp_ids) for co in ctx.outcomes},
        cos_with_cep={co.id for co in ctx.outcomes if co.cep_ids},
        cos_with_cea={co.id for co in ctx.outcomes if co.cea_ids},
        kp_codes={a.id: a.code for a in ctx.knowledge_profiles},
    )

    links: list[SuggestedLink] = []
    seen: set[tuple[UUID, UUID]] = set()
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        co = cos.get(str(item.get("co", "")).strip().upper())
        po = pos.get(str(item.get("po", "")).strip().upper())
        if co is None or po is None or (co.id, po.id) in seen:
            continue
        seen.add((co.id, po.id))

        justification = _clean_text(item.get("justification"), MAX_JUSTIFICATION)
        try:
            weight = min(3, max(1, int(item.get("weight", 2))))
        except (TypeError, ValueError):
            weight = 2
        try:
            confidence = min(1.0, max(0.0, float(item["confidence"])))
        except (KeyError, TypeError, ValueError):
            confidence = None
        fallback = justification or f"Supports {co.code}'s link to {po.code}."

        # Knowledge profiles: only the PO's required ones count, and only when the
        # CO is not already mapped to one of them.
        proposed_kp = [
            (a, why) for a, why in _attributes(item.get("knowledge_profiles"), kps, fallback)
            if a.id in po.kp_ids
        ]
        kp_list: list[SuggestedAttribute] = []
        if po.kp_ids:
            already = co.kp_ids & po.kp_ids
            kp_list = _existing(already, kp_by_id, proposed_kp) if already else _added(proposed_kp)

        cep_list: list[SuggestedAttribute] = []
        if needs_cep(po.code):
            proposed = _attributes(item.get("complex_problems"), ceps, fallback)
            cep_list = _existing(co.cep_ids, cep_by_id, proposed) if co.cep_ids else _added(proposed)

        cea_list: list[SuggestedAttribute] = []
        if needs_cea(po.code):
            proposed = _attributes(item.get("complex_activities"), ceas, fallback)
            cea_list = _existing(co.cea_ids, cea_by_id, proposed) if co.cea_ids else _added(proposed)

        check = facts.check(
            co.id, po.id,
            added_kp_ids=[a.id for a in kp_list if not a.already_mapped],
            adds_cep=any(not a.already_mapped for a in cep_list),
            adds_cea=any(not a.already_mapped for a in cea_list),
        )
        issues: list[str] = []
        if check.missing_kp:
            needed = ", ".join(facts.required_kp_codes(po.id))
            issues.append(
                f"K rule: {po.code} needs one of {needed}, and the AI named none that {co.code} uses."
            )
        if check.missing_cep:
            issues.append(
                f"CEP rule: a CO mapped to {po.code} needs a complex engineering problem, "
                "and the AI named none."
            )
        if check.missing_cea:
            issues.append(
                f"CEA rule: a CO mapped to {po.code} needs a complex engineering activity, "
                "and the AI named none."
            )
        if not justification:
            issues.append("The AI gave no justification.")
        warnings = [w for w in (_domain_warning(ctx, co, po),) if w]

        already_mapped = (co.id, po.id) in existing
        links.append(SuggestedLink(
            index=0,
            course_outcome_id=co.id,
            co_code=co.code,
            program_outcome_id=po.id,
            po_code=po.code,
            weight=weight,
            justification=justification,
            confidence=confidence,
            knowledge_profiles=kp_list,
            complex_problems=cep_list,
            complex_activities=cea_list,
            issues=issues,
            warnings=warnings,
            already_mapped=already_mapped,
            can_apply=not issues and not already_mapped,
        ))

    links.sort(key=lambda link: (natural_key(link.co_code), natural_key(link.po_code)))
    for index, link in enumerate(links):
        link.index = index
    return links
