from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.approval.exceptions import InvalidEntityType
from app.modules.approval.models import ReviewComment
from app.modules.approval.repository import ReviewCommentRepository
from app.modules.approval.schemas import InboxItem, VALID_ENTITY_TYPES
from app.modules.assessment.models import ResultPublication
from app.modules.curriculum.models import AcademicTerm, Batch, Course, Section, SectionOffering
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.obe.models import COPOMappingSet, CourseOutcome


class ReviewCommentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ReviewCommentRepository(session)

    async def add_comment(
        self,
        org_id: UUID,
        entity_type: str,
        entity_id: UUID,
        author_user_id: UUID,
        comment: str,
    ) -> ReviewComment:
        if entity_type not in VALID_ENTITY_TYPES:
            raise InvalidEntityType(
                f"Invalid entity_type '{entity_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}"
            )
        obj = ReviewComment(
            organization_id=org_id,
            entity_type=entity_type,
            entity_id=entity_id,
            author_user_id=author_user_id,
            comment=comment,
        )
        result = await self._repo.create(obj)
        await self._session.commit()
        return result

    async def list_comments(
        self, org_id: UUID, entity_type: str, entity_id: UUID
    ) -> list[ReviewComment]:
        return await self._repo.list_for_entity(org_id, entity_type, entity_id)


class ApprovalInboxService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _actionable_rp_statuses(manifest: PermissionManifestResponse | None) -> list[str]:
        """
        Result-publication statuses the viewer can still act on:
        SUBMITTED awaits a Module Leader, ML_APPROVED awaits a Program
        Coordinator. Showing a section the viewer has already approved (or
        can't approve yet) just clutters their inbox.
        """
        if manifest is None or manifest.is_super_admin:
            return ["SUBMITTED", "ML_APPROVED"]
        statuses = []
        if "result.approve.ml" in manifest.permissions:
            statuses.append("SUBMITTED")
        if "result.approve.pc" in manifest.permissions or "result.publish" in manifest.permissions:
            statuses.append("ML_APPROVED")
        # View-only inbox access (no approve permission): show everything pending
        return statuses or ["SUBMITTED", "ML_APPROVED"]

    async def get_inbox(
        self, org_id: UUID, manifest: PermissionManifestResponse | None = None
    ) -> dict:
        """
        Queries across schemas to find pending items.

        pending_result_publications: statuses awaiting the viewer's own action
        pending_course_outcomes: status = 'SUBMITTED'
        pending_co_po_mapping_sets: status = 'DRAFT' (not yet published)

        Returns dict with keys matching InboxResponse fields.
        """
        # Result publications pending review (SUBMITTED = awaiting ML, ML_APPROVED = awaiting PC)
        rp_result = await self._session.execute(
            select(
                ResultPublication,
                Course.code.label("course_code"),
                Course.title.label("course_title"),
                Batch.name.label("batch_name"),
                AcademicTerm.name.label("term_name"),
                Section.name.label("section_name"),
            )
            .join(SectionOffering, SectionOffering.id == ResultPublication.section_offering_id)
            .join(Course, Course.id == SectionOffering.course_id)
            .join(Batch, Batch.id == SectionOffering.batch_id)
            .join(AcademicTerm, AcademicTerm.id == SectionOffering.academic_term_id)
            .join(Section, Section.id == SectionOffering.section_id)
            .where(
                and_(
                    ResultPublication.organization_id == org_id,
                    ResultPublication.status.in_(self._actionable_rp_statuses(manifest)),
                )
            )
        )
        rp_items = [
            InboxItem(
                entity_type="result_publication",
                entity_id=rp.id,
                description=(
                    f"{course_code} {course_title} — {batch_name} Section {section_name} "
                    f"({term_name})"
                ),
                status=rp.status,
                submitted_at=rp.submitted_at,
                section_offering_id=rp.section_offering_id,
            )
            for rp, course_code, course_title, batch_name, term_name, section_name in rp_result.all()
        ]

        # COs pending review (SUBMITTED = awaiting approval)
        co_result = await self._session.execute(
            select(CourseOutcome).where(
                and_(
                    CourseOutcome.organization_id == org_id,
                    CourseOutcome.status == "SUBMITTED",
                )
            )
        )
        cos = co_result.scalars().all()
        co_items = [
            InboxItem(
                entity_type="course_outcome",
                entity_id=co.id,
                description=f"CO {co.code}: {co.statement[:60]}",
                status=co.status,
                submitted_at=co.created_at,  # COs don't have a dedicated submitted_at
            )
            for co in cos
        ]

        # CO-PO mapping sets not yet published (DRAFT)
        ms_result = await self._session.execute(
            select(COPOMappingSet).where(
                and_(
                    COPOMappingSet.organization_id == org_id,
                    COPOMappingSet.status == "DRAFT",
                )
            )
        )
        mapping_sets = ms_result.scalars().all()
        ms_items = [
            InboxItem(
                entity_type="co_po_mapping_set",
                entity_id=ms.id,
                description=f"CO-PO Mapping (curriculum {ms.curriculum_id}, course {ms.course_id})",
                status=ms.status,
                submitted_at=ms.created_at,
            )
            for ms in mapping_sets
        ]

        return {
            "pending_result_publications": rp_items,
            "pending_course_outcomes": co_items,
            "pending_co_po_mapping_sets": ms_items,
            "total_count": len(rp_items) + len(co_items) + len(ms_items),
        }

    async def get_counts(
        self, org_id: UUID, manifest: PermissionManifestResponse | None = None
    ) -> dict:
        """Returns counts for each category."""
        inbox = await self.get_inbox(org_id, manifest)
        return {
            "result_publications": len(inbox["pending_result_publications"]),
            "course_outcomes": len(inbox["pending_course_outcomes"]),
            "co_po_mapping_sets": len(inbox["pending_co_po_mapping_sets"]),
            "total": inbox["total_count"],
        }
