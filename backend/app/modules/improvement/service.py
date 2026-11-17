from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.gateway import AIGateway, BackendFactory
from app.modules.ai.providers import AIError
from app.modules.audit.writer import write_audit_log
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.improvement.agent import IMPROVE_PROMPT_VERSION, run_agent
from app.modules.improvement.models import ImprovementPlan
from app.modules.improvement.schemas import PlanResponse
from app.modules.improvement.tools import PreviousPlan, SectionTools
from app.modules.integrity.service import IntegrityService
from app.modules.obe.mapping_rules import natural_key
from app.modules.obe.models import CourseOutcome

FEATURE = "improvement"


class _Error(HTTPException):
    def __init__(self, code: int, detail: str):
        super().__init__(status_code=code, detail=detail)


class ImprovementService:
    def __init__(
        self,
        session: AsyncSession,
        user: User,
        manifest: PermissionManifestResponse,
        backend_factory: BackendFactory | None = None,
    ) -> None:
        self.db = session
        self.user = user
        self.manifest = manifest
        self.backend_factory = backend_factory
        self.integrity = IntegrityService(session)

    async def run(self, offering_id: UUID) -> PlanResponse:
        offering = await self.integrity.get_offering(offering_id, self.user, self.manifest)
        evidence = await self.integrity.evidence_attainment(offering)
        if not evidence.outcomes or evidence.total_students == 0:
            raise _Error(422, "This section has no marks yet, so there is nothing to explain.")
        previous = await self._previous(offering.id, offering.course_id)
        outcomes = (await self.db.execute(select(CourseOutcome).where(and_(
            CourseOutcome.course_id == offering.course_id,
            CourseOutcome.curriculum_id == offering.curriculum_id,
        )))).scalars().all()
        outcome_lines = "\n".join(
            f"{co.code}: {co.statement}" for co in sorted(outcomes, key=lambda c: natural_key(c.code))
        )
        s = evidence.section
        course = f"{s.course_code} {s.course_title}"
        section = f"{s.section_name}, {s.term_name}"

        gateway = await AIGateway.for_feature(
            self.db, feature=FEATURE, organization_id=self.user.organization_id,
            user_id=self.user.id, backend_factory=self.backend_factory,
        )
        if not gateway.available:
            raise _Error(503, f"The improvement agent is not available: {gateway.unavailable_reason()}.")
        tools = SectionTools(self.db, offering, evidence, previous)
        await tools.co_codes()
        await self.db.commit()  # release the connection between model calls
        try:
            run = await run_agent(
                gateway, tools, course=course, section=section, outcomes=outcome_lines,
                has_previous=previous is not None,
            )
        except AIError as exc:
            gateway.record_usage(self.db)
            await self.db.commit()
            raise _Error(502, f"The AI model could not finish the plan: {exc}. Please try again.") from exc

        plan = ImprovementPlan(
            organization_id=self.user.organization_id,
            section_offering_id=offering.id,
            course_id=offering.course_id,
            summary=run.summary,
            follow_up=run.follow_up,
            diagnoses=run.diagnoses,
            steps=run.steps,
            provider=gateway.provider,
            model=run.model[:100],
            prompt_version=IMPROVE_PROMPT_VERSION,
            created_by_user_id=self.user.id,
        )
        self.db.add(plan)
        gateway.record_usage(self.db)
        await self.db.flush()
        write_audit_log(
            self.db,
            entity_type="section_offering",
            entity_id=offering.id,
            action="AI_IMPROVEMENT_PLAN",
            org_id=self.user.organization_id,
            actor_user_id=self.user.id,
            extra={
                "plan_id": str(plan.id), "model": plan.model, "prompt_version": plan.prompt_version,
                "provider": plan.provider, "steps": len(run.steps), "diagnoses": len(run.diagnoses),
                "unsupported": sum(not d["supported"] for d in run.diagnoses),
            },
        )
        await self.db.commit()
        return _response(plan)

    async def latest(self, offering_id: UUID) -> PlanResponse | None:
        offering = await self.integrity.get_offering(offering_id, self.user, self.manifest)
        plan = (await self.db.execute(
            select(ImprovementPlan).where(ImprovementPlan.section_offering_id == offering.id)
            .order_by(ImprovementPlan.created_at.desc()).limit(1)
        )).scalar_one_or_none()
        return _response(plan) if plan else None

    async def decide(self, plan_id: UUID, intervention_id: str, decision: str, note: str | None) -> PlanResponse:
        plan = (await self.db.execute(select(ImprovementPlan).where(and_(
            ImprovementPlan.id == plan_id, ImprovementPlan.organization_id == self.user.organization_id,
        )))).scalar_one_or_none()
        if plan is None:
            raise _Error(status.HTTP_404_NOT_FOUND, "Improvement plan not found")
        await self.integrity.get_offering(plan.section_offering_id, self.user, self.manifest)
        known = {i["id"] for d in plan.diagnoses for i in d.get("interventions", [])}
        if intervention_id not in known:
            raise _Error(status.HTTP_404_NOT_FOUND, "Intervention not found")
        decisions = dict(plan.decisions or {})
        decisions[intervention_id] = {
            "decision": decision, "note": (note or "").strip() or None,
            "by": str(self.user.id), "at": datetime.now(timezone.utc).isoformat(),
        }
        plan.decisions = decisions
        write_audit_log(
            self.db, entity_type="improvement_plan", entity_id=plan.id,
            action="AI_IMPROVEMENT_DECIDED", org_id=self.user.organization_id, actor_user_id=self.user.id,
            after_status=decision, extra={"intervention": intervention_id},
        )
        await self.db.commit()
        return _response(plan)

    async def _previous(self, offering_id: UUID, course_id: UUID) -> PreviousPlan | None:
        """The course's latest plan from another section, with what the teacher accepted."""
        plan = (await self.db.execute(
            select(ImprovementPlan).where(and_(
                ImprovementPlan.course_id == course_id,
                ImprovementPlan.section_offering_id != offering_id,
                ImprovementPlan.organization_id == self.user.organization_id,
            )).order_by(ImprovementPlan.created_at.desc()).limit(1)
        )).scalar_one_or_none()
        if plan is None:
            return None
        decisions = plan.decisions or {}
        then = {}
        for step in plan.steps or []:
            if step.get("tool") == "outcome_attainment" and step.get("result"):
                then = {o["co"]: o.get("reported_attained_share_pct")
                        for o in step["result"].get("outcomes", [])}
                break
        diagnoses = [{
            "co": d["co"],
            "problem": d.get("problem"),
            "accepted_interventions": [
                i["action"] for i in d.get("interventions", [])
                if decisions.get(i["id"], {}).get("decision") == "ACCEPTED"
            ],
        } for d in plan.diagnoses or []]
        return PreviousPlan(
            data={
                "made_on": plan.created_at.date().isoformat() if plan.created_at else None,
                "diagnoses": diagnoses,
                "attained_share_then_pct": then,
            },
            co_codes=[d["co"] for d in diagnoses],
        )


def _response(plan: ImprovementPlan) -> PlanResponse:
    decisions = plan.decisions or {}
    diagnoses = []
    for d in plan.diagnoses or []:
        diagnoses.append({
            **d,
            "interventions": [
                {**i, "decision": decisions.get(i["id"], {}).get("decision"),
                 "note": decisions.get(i["id"], {}).get("note")}
                for i in d.get("interventions", [])
            ],
        })
    return PlanResponse(
        id=plan.id,
        section_offering_id=plan.section_offering_id,
        summary=plan.summary,
        follow_up=plan.follow_up,
        diagnoses=diagnoses,
        steps=plan.steps or [],
        model=plan.model,
        prompt_version=plan.prompt_version,
        created_at=plan.created_at,
    )
