import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.curriculum.exceptions import CourseNotFoundError, CurriculumNotFoundError
from app.modules.curriculum.repository import (
    CourseAssessmentToolRepository,
    CourseCOMarksRepository,
    CourseLearningMaterialRepository,
    CourseLessonPlanRepository,
    CourseObjectiveRepository,
    CourseRepository,
    CurriculumRepository,
    ModuleLeaderAssignmentRepository,
    PrerequisiteRepository,
)
from app.core.config import settings
from app.core.storage import presigned_get_url
from app.modules.iam.repository.user_repository import UserRepository
from app.modules.obe.repository import (
    COCAMappingRepository,
    COCPMappingRepository,
    COKPMappingRepository,
    CORepository,
    MappingEntryRepository,
    MappingSetRepository,
    PORepository,
)
from app.modules.org.repository import OrgRepository
from app.modules.ref_data.repository import (
    AssessmentTypeRepository,
    BloomDomainRepository,
    BloomLevelRepository,
    ComplexActivityRepository,
    ComplexProblemRepository,
    KnowledgeProfileRepository,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"

_NUM_RE = re.compile(r"(\d+)")


def _natural_key(code: str) -> list:
    return [int(part) if part.isdigit() else part.lower() for part in _NUM_RE.split(code)]


def _fmt_marks(value: Decimal | float | int) -> str:
    f = float(value)
    if f == int(f):
        return str(int(f))
    return f"{f:g}"


class CourseOutlineService:
    def __init__(self, db: AsyncSession) -> None:
        self._course_repo = CourseRepository(db)
        self._curriculum_repo = CurriculumRepository(db)
        self._objective_repo = CourseObjectiveRepository(db)
        self._prereq_repo = PrerequisiteRepository(db)
        self._lesson_plan_repo = CourseLessonPlanRepository(db)
        self._assessment_tool_repo = CourseAssessmentToolRepository(db)
        self._co_marks_repo = CourseCOMarksRepository(db)
        self._material_repo = CourseLearningMaterialRepository(db)
        self._module_leader_repo = ModuleLeaderAssignmentRepository(db)

        self._co_repo = CORepository(db)
        self._mapping_set_repo = MappingSetRepository(db)
        self._mapping_entry_repo = MappingEntryRepository(db)
        self._co_cp_repo = COCPMappingRepository(db)
        self._co_ca_repo = COCAMappingRepository(db)
        self._co_kp_repo = COKPMappingRepository(db)
        self._po_repo = PORepository(db)

        self._bloom_domain_repo = BloomDomainRepository(db)
        self._bloom_level_repo = BloomLevelRepository(db)
        self._cp_repo = ComplexProblemRepository(db)
        self._ca_repo = ComplexActivityRepository(db)
        self._kp_repo = KnowledgeProfileRepository(db)
        self._assessment_type_repo = AssessmentTypeRepository(db)

        self._org_repo = OrgRepository(db)
        self._user_repo = UserRepository(db)

    async def build_context(self, course_id: UUID, curriculum_id: UUID, org_id: UUID) -> dict:
        course = await self._course_repo.get_by_id(course_id, org_id)
        if course is None:
            raise CourseNotFoundError()
        curriculum = await self._curriculum_repo.get_by_id(curriculum_id, org_id)
        if curriculum is None:
            raise CurriculumNotFoundError()

        # ── Basics ──────────────────────────────────────────────────────
        lesson_items = await self._lesson_plan_repo.list_by_course(curriculum_id, course_id)
        total_weeks = max((item.week_number for item in lesson_items), default=0)

        # ── Prerequisites ──────────────────────────────────────────────
        prereq_links = await self._prereq_repo.list_by_course(course_id, org_id)
        prerequisites = []
        for link in prereq_links:
            prereq_course = await self._course_repo.get_by_id(link.prerequisite_course_id, org_id)
            if prereq_course:
                prerequisites.append({"code": prereq_course.code, "title": prereq_course.title})

        # ── Objectives ─────────────────────────────────────────────────
        objectives = [o.statement for o in await self._objective_repo.list_by_course(course_id)]

        # ── Course Outcomes + Bloom levels ───────────────────────────────
        cos = await self._co_repo.list_by_curriculum_course(curriculum_id, course_id)
        co_ids = [co.id for co in cos]
        co_by_id = {co.id: co for co in cos}
        bloom_level_ids_by_co = await self._co_repo.get_bloom_level_ids_bulk(co_ids)

        # ── CO-PO mapping ──────────────────────────────────────────────
        mapping_set = await self._mapping_set_repo.find_by_curriculum_course(curriculum_id, course_id)
        co_po_weights: dict[tuple[UUID, UUID], int] = {}
        if mapping_set:
            for entry in await self._mapping_entry_repo.list_by_set(mapping_set.id):
                if entry.weight > 0:
                    co_po_weights[(entry.course_outcome_id, entry.program_outcome_id)] = entry.weight

        # ── CO-CP / CO-CA / CO-KP mappings ────────────────────────────────
        co_cp_ids: dict[UUID, set[UUID]] = {}
        co_ca_ids: dict[UUID, set[UUID]] = {}
        co_kp_ids: dict[UUID, set[UUID]] = {}
        for co in cos:
            co_cp_ids[co.id] = {m.complex_problem_id for m in await self._co_cp_repo.list_by_co(co.id)}
            co_ca_ids[co.id] = {m.complex_activity_id for m in await self._co_ca_repo.list_by_co(co.id)}
            co_kp_ids[co.id] = {m.knowledge_profile_id for m in await self._co_kp_repo.list_by_co(co.id)}

        # ── Reference data ─────────────────────────────────────────────
        bloom_domains = {d.id: d for d in await self._bloom_domain_repo.list_active(org_id)}
        bloom_levels = await self._bloom_level_repo.list_active(org_id)
        bloom_level_by_id = {b.id: b for b in bloom_levels}

        cps = {c.id: c for c in await self._cp_repo.list_active(org_id)}
        cas = {c.id: c for c in await self._ca_repo.list_active(org_id)}
        kps = {c.id: c for c in await self._kp_repo.list_active(org_id)}

        program_id = curriculum.program_id
        pos = await self._po_repo.list_active(org_id, program_id)
        po_by_id = {p.id: p for p in pos}

        # ── Referenced codes (for filtering legends) ─────────────────────
        referenced_bloom_level_ids: set[UUID] = set()
        referenced_cp_ids: set[UUID] = set()
        referenced_kp_ids: set[UUID] = set()
        for co in cos:
            referenced_bloom_level_ids.update(bloom_level_ids_by_co.get(co.id, []))
            referenced_cp_ids.update(co_cp_ids[co.id])
            referenced_kp_ids.update(co_kp_ids[co.id])

        cp_columns = sorted(
            (cps[cid] for cid in referenced_cp_ids if cid in cps),
            key=lambda c: _natural_key(c.code),
        )
        kp_columns = sorted(
            (kps[cid] for cid in referenced_kp_ids if cid in kps),
            key=lambda c: _natural_key(c.code),
        )

        # ── CO table (POs / Learning Domains / KP / EP / EA codes per CO) ─
        course_outcomes = []
        for co in cos:
            bloom_codes = [
                bloom_level_by_id[bid].code
                for bid in bloom_level_ids_by_co.get(co.id, [])
                if bid in bloom_level_by_id
            ]
            co_pos = sorted(
                (po_by_id[pid] for (cid, pid) in co_po_weights if cid == co.id and pid in po_by_id),
                key=lambda p: p.order_index,
            )
            course_outcomes.append({
                "code": co.code,
                "statement": co.statement,
                "bloom_codes": bloom_codes,
                "po_codes": [p.code for p in co_pos],
                "kp_codes": sorted(
                    (kps[kid].code for kid in co_kp_ids[co.id] if kid in kps),
                    key=_natural_key,
                ),
                "ep_codes": sorted(
                    (cps[cid].code for cid in co_cp_ids[co.id] if cid in cps),
                    key=_natural_key,
                ),
                "ea_codes": sorted(
                    (cas[cid].code for cid in co_ca_ids[co.id] if cid in cas),
                    key=_natural_key,
                ),
            })

        # ── Mapping justification tables (filtered to COs with mappings) ──
        co_po_justifications = [
            {"co_code": co["code"], "codes": co["po_codes"]} for co in course_outcomes if co["po_codes"]
        ]
        co_kp_justifications = [
            {"co_code": co["code"], "codes": co["kp_codes"]} for co in course_outcomes if co["kp_codes"]
        ]
        co_ep_justifications = [
            {"co_code": co["code"], "codes": co["ep_codes"]} for co in course_outcomes if co["ep_codes"]
        ]
        co_ea_justifications = [
            {"co_code": co["code"], "codes": co["ea_codes"]} for co in course_outcomes if co["ea_codes"]
        ]

        # ── Legend (Bloom / Knowledge Profile / CEP, filtered to referenced) ─
        bloom_legend = []
        for domain in bloom_domains.values():
            levels = sorted(
                (b for b in bloom_levels if b.bloom_domain_id == domain.id and b.id in referenced_bloom_level_ids),
                key=lambda b: b.order_index,
            )
            if levels:
                bloom_legend.append({
                    "domain_name": domain.name,
                    "levels": [{"code": b.code, "name": b.name} for b in levels],
                })

        kp_legend = [{"code": c.code, "description": c.description} for c in kp_columns]
        cp_legend = [{"code": c.code, "description": c.description} for c in cp_columns]

        # ── Assessment tools + CO-wise marks ─────────────────────────────
        assessment_tools = await self._assessment_tool_repo.list_for_course(curriculum_id, course_id)
        assessment_types = {a.id: a for a in await self._assessment_type_repo.list_active(org_id)}
        co_marks_records = await self._co_marks_repo.list_for_course(curriculum_id, course_id)

        marks_by_tool: dict[UUID, list] = defaultdict(list)
        for record in co_marks_records:
            marks_by_tool[record.assessment_type_id].append(record)

        assessment_rows = []
        grand_total = Decimal("0")
        for tool in assessment_tools:
            assessment_type = assessment_types.get(tool.assessment_type_id)
            name = assessment_type.name if assessment_type else ""
            records = marks_by_tool.get(tool.assessment_type_id, [])

            total_marks = Decimal("0")
            for record in records:
                if record.course_outcome_id is None:
                    total_marks = record.marks

            co_marks: dict[str, str] = {}
            for record in records:
                if record.course_outcome_id is not None and record.marks and record.marks > 0:
                    co = co_by_id.get(record.course_outcome_id)
                    if co:
                        co_marks[co.code] = _fmt_marks(record.marks)

            grand_total += total_marks
            assessment_rows.append({
                "name": name,
                "total_marks": _fmt_marks(total_marks),
                "co_marks": co_marks,
            })

        # ── Mapping of Assessment Tools with COs ─────────────────────────
        tool_co_mapping = [
            {"tool_name": row["name"], "co_codes": list(row["co_marks"].keys())}
            for row in assessment_rows
            if row["co_marks"]
        ]

        # ── PO Validation via Assessment ─────────────────────────────────
        po_validation = []
        for row in assessment_rows:
            if not row["co_marks"]:
                continue
            co_codes = list(row["co_marks"].keys())
            po_id_set: set[UUID] = set()
            for co in cos:
                if co.code in co_codes:
                    po_id_set.update(
                        po_id for (cid, po_id) in co_po_weights if cid == co.id
                    )
            po_codes = sorted(
                (po_by_id[pid].code for pid in po_id_set if pid in po_by_id),
                key=_natural_key,
            )
            po_validation.append({
                "assessment_type_name": row["name"],
                "co_codes": co_codes,
                "po_codes": po_codes,
            })

        # ── Lesson plan ────────────────────────────────────────────────
        item_ids = [item.id for item in lesson_items]
        cos_by_item = await self._lesson_plan_repo.list_cos_for_items(item_ids)
        lesson_plan = [
            {
                "week_number": item.week_number,
                "lesson_label": item.lesson_label,
                "topic": item.topic,
                "tla": item.tla,
                "co_codes": [
                    co_by_id[cid].code for cid in cos_by_item.get(item.id, []) if cid in co_by_id
                ],
                "assessment_strategy": item.assessment_strategy,
            }
            for item in lesson_items
        ]

        # ── Learning materials ───────────────────────────────────────────
        materials = await self._material_repo.list_by_course(course_id)
        textbooks = []
        references = []
        for material in materials:
            entry = {
                "title": material.title,
                "authors": material.authors,
                "publisher": material.publisher,
                "edition_year": material.edition_year,
            }
            if material.material_type == "TEXTBOOK":
                textbooks.append(entry)
            else:
                references.append(entry)

        # ── Module leader ────────────────────────────────────────────────
        module_leader = None
        assignments = await self._module_leader_repo.list_by_course(course_id, org_id)
        if assignments:
            user = await self._user_repo.find_by_id(assignments[0].user_id)
            if user:
                module_leader = {"full_name": user.full_name, "designation": user.designation}

        # ── Org branding ──────────────────────────────────────────────
        org = await self._org_repo.get(org_id)
        logo_url = None
        if org and org.logo_file_key:
            logo_url = await presigned_get_url(settings.MINIO_BUCKET_LOGOS, org.logo_file_key)

        return {
            "course": {
                "code": course.code,
                "title": course.title,
                "course_type": course.course_type,
                "credits": course.credits,
                "weekly_hours": course.theory_hours + course.lab_hours,
                "total_weeks": total_weeks,
                "description": course.description,
                "syllabus_content": course.syllabus_content,
            },
            "curriculum": {"name": curriculum.name, "code": curriculum.code},
            "prerequisites": prerequisites,
            "objectives": objectives,
            "course_outcomes": course_outcomes,
            "co_po_justifications": co_po_justifications,
            "co_kp_justifications": co_kp_justifications,
            "co_ep_justifications": co_ep_justifications,
            "co_ea_justifications": co_ea_justifications,
            "bloom_legend": bloom_legend,
            "cp_legend": cp_legend,
            "kp_legend": kp_legend,
            "tool_co_mapping": tool_co_mapping,
            "po_validation": po_validation,
            "lesson_plan": lesson_plan,
            "assessment_rows": assessment_rows,
            "grand_total": _fmt_marks(grand_total),
            "textbooks": textbooks,
            "references": references,
            "module_leader": module_leader,
            "org": {
                "name": org.name if org else "",
                "short_name": org.short_name if org else "",
                "logo_url": logo_url,
            },
        }


def render_course_outline_pdf(context: dict) -> bytes:
    from weasyprint import HTML

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    html = env.get_template("course_outline.html").render(**context)
    return HTML(string=html).write_pdf()
