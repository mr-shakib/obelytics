from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.curriculum.models import Course, CourseLessonPlanItem, Curriculum
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.obe.models import COPOMappingEntry, COPOMappingSet, CourseOutcome


def _allowed(manifest: PermissionManifestResponse, permission: str) -> bool:
    return manifest.is_super_admin or permission in manifest.permissions


async def build_read_only_obe_context(
    db: AsyncSession,
    user: User,
    manifest: PermissionManifestResponse,
    conversation_context: dict[str, Any],
) -> str:
    """Return bounded, authorized live data for the model; never accepts model-generated SQL."""
    facts: list[str] = []

    if _allowed(manifest, "curriculum.read"):
        curriculum_count = await db.scalar(
            select(func.count(Curriculum.id)).where(
                Curriculum.organization_id == user.organization_id
            )
        )
        course_count = await db.scalar(
            select(func.count(Course.id)).where(Course.organization_id == user.organization_id)
        )
        facts.append(f"Visible organization totals: {curriculum_count or 0} curricula, {course_count or 0} courses.")

    raw_course_id = conversation_context.get("course_id")
    raw_curriculum_id = conversation_context.get("curriculum_id")
    if not raw_course_id or not raw_curriculum_id or not _allowed(manifest, "curriculum.read"):
        return "\n".join(facts)

    try:
        course_id = UUID(str(raw_course_id))
        curriculum_id = UUID(str(raw_curriculum_id))
    except ValueError:
        return "\n".join(facts)

    curriculum = await db.scalar(
        select(Curriculum).where(
            Curriculum.id == curriculum_id,
            Curriculum.organization_id == user.organization_id,
        )
    )
    if curriculum is None:
        return "\n".join(facts)
    if manifest.program_ids and curriculum.program_id not in manifest.program_ids:
        return "\n".join(facts)

    course = await db.scalar(
        select(Course).where(
            Course.id == course_id,
            Course.organization_id == user.organization_id,
        )
    )
    if course is None:
        return "\n".join(facts)

    outcomes = list(
        (
            await db.scalars(
                select(CourseOutcome)
                .where(
                    CourseOutcome.organization_id == user.organization_id,
                    CourseOutcome.curriculum_id == curriculum_id,
                    CourseOutcome.course_id == course_id,
                )
                .order_by(CourseOutcome.code)
                .limit(30)
            )
        ).all()
    )
    lesson_count = await db.scalar(
        select(func.count(CourseLessonPlanItem.id)).where(
            CourseLessonPlanItem.curriculum_id == curriculum_id,
            CourseLessonPlanItem.course_id == course_id,
        )
    )
    planned_weeks = await db.scalar(
        select(func.count(func.distinct(CourseLessonPlanItem.week_number))).where(
            CourseLessonPlanItem.curriculum_id == curriculum_id,
            CourseLessonPlanItem.course_id == course_id,
        )
    )
    mapping_set = await db.scalar(
        select(COPOMappingSet).where(
            COPOMappingSet.organization_id == user.organization_id,
            COPOMappingSet.curriculum_id == curriculum_id,
            COPOMappingSet.course_id == course_id,
        )
    )
    mapping_count = 0
    if mapping_set is not None:
        mapping_count = (
            await db.scalar(
                select(func.count(COPOMappingEntry.id)).where(
                    COPOMappingEntry.mapping_set_id == mapping_set.id
                )
            )
            or 0
        )

    facts.extend(
        [
            f"Active course context: {course.code} — {course.title} ({course.course_type}, {course.credits} credits).",
            f"Curriculum: {curriculum.name}; status: {curriculum.status}.",
            f"Delivery plan: {lesson_count or 0} lessons across {planned_weeks or 0} weeks.",
            f"CO-PO mapping set: {'created' if mapping_set else 'not created'}; {mapping_count} mapping entries.",
            "Course Outcomes: "
            + ("; ".join(f"{co.code}: {co.statement}" for co in outcomes) or "none"),
        ]
    )
    return "\n".join(facts)
