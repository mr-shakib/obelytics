import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import anyio
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import presigned_get_url
from app.modules.assessment.repository import MarksheetQuestionRepository
from app.modules.curriculum.exceptions import CourseNotFoundError, CurriculumNotFoundError
from app.modules.curriculum.repository import (
    CourseAssessmentToolRepository,
    CourseBloomMarksRepository,
    CourseCOMarksRepository,
    CourseLearningMaterialRepository,
    CourseLessonPlanRepository,
    CourseObjectiveRepository,
    CourseRepository,
    CurriculumRepository,
    ModuleLeaderAssignmentRepository,
    PrerequisiteRepository,
    SectionOfferingRepository,
)
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
from app.modules.org.repository import DepartmentRepository, OrgRepository, ProgramRepository
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
_LESSON_RE = re.compile(r"^lesson\s*", re.IGNORECASE)
_KP_SHORT_LABELS = {
    "K1": "Natural Sciences",
    "K2": "Mathematics",
    "K3": "Engineering Fundamentals",
    "K4": "Specialist Knowledge",
    "K5": "Engineering Design",
    "K6": "Engineering Practice",
    "K7": "Engineering in Society",
    "K8": "Ethics",
    "K9": "Research Literature",
}
_EP_SHORT_LABELS = {
    "CEP1": "Depth of Knowledge Required",
    "CEP2": "Range of Conflicting Requirements",
    "CEP3": "Depth of Analysis Required",
    "CEP4": "Familiarity of Issues",
    "CEP5": "Extent of Applicable Codes",
    "CEP6": "Extent of Stakeholder Involvement",
    "CEP7": "Interdependence",
}


def _natural_key(code: str) -> list:
    return [int(part) if part.isdigit() else part.lower() for part in _NUM_RE.split(code)]


def _fmt_marks(value: Decimal | float | int) -> str:
    f = float(value)
    if f == int(f):
        return str(int(f))
    return f"{f:g}"


def _fmt_tool_marks(value: Decimal | float | int) -> str:
    formatted = _fmt_marks(value)
    return formatted.zfill(2) if formatted.isdigit() and 0 < int(formatted) < 10 else formatted


def _format_lesson_label(label: str | None, fallback_number: int) -> str:
    cleaned = (label or "").strip()
    if not cleaned:
        return f"Lesson {fallback_number}"
    if cleaned.isdigit():
        return f"Lesson {cleaned}"
    return cleaned


def _lesson_reference(display_label: str) -> str:
    reference = _LESSON_RE.sub("", display_label, count=1).strip()
    return reference or display_label


def _format_hours_label(hours: int) -> str | None:
    if hours <= 0:
        return None
    suffix = "Hour" if hours == 1 else "Hours"
    return f"{hours} {suffix}"


def _format_ep_code(code: str) -> str:
    if re.match(r"^CEP", code, flags=re.IGNORECASE):
        return code.upper()
    return re.sub(r"^CP", "CEP", code, flags=re.IGNORECASE).upper()


def _format_kp_description(code: str, description: str) -> str:
    return _KP_SHORT_LABELS.get(code.upper(), description)


def _format_ep_description(code: str, description: str) -> str:
    return _EP_SHORT_LABELS.get(_format_ep_code(code).upper(), description)


def _format_assessment_tool_name(name: str) -> str:
    normalized = name.lower()
    if "mid" in normalized:
        return "Midterm"
    if "final" in normalized:
        return "Final"
    return name


class CourseOutlineService:
    def __init__(self, db: AsyncSession) -> None:
        self._course_repo = CourseRepository(db)
        self._curriculum_repo = CurriculumRepository(db)
        self._objective_repo = CourseObjectiveRepository(db)
        self._prereq_repo = PrerequisiteRepository(db)
        self._lesson_plan_repo = CourseLessonPlanRepository(db)
        self._assessment_tool_repo = CourseAssessmentToolRepository(db)
        self._co_marks_repo = CourseCOMarksRepository(db)
        self._bloom_marks_repo = CourseBloomMarksRepository(db)
        self._material_repo = CourseLearningMaterialRepository(db)
        self._module_leader_repo = ModuleLeaderAssignmentRepository(db)
        self._section_offering_repo = SectionOfferingRepository(db)
        self._marksheet_question_repo = MarksheetQuestionRepository(db)

        self._co_repo = CORepository(db)
        self._mapping_set_repo = MappingSetRepository(db)
        self._mapping_entry_repo = MappingEntryRepository(db)
        self._co_cp_repo = COCPMappingRepository(db)
        self._co_ca_repo = COCAMappingRepository(db)
        self._co_kp_repo = COKPMappingRepository(db)
        self._po_repo = PORepository(db)
        self._program_repo = ProgramRepository(db)
        self._department_repo = DepartmentRepository(db)

        self._bloom_domain_repo = BloomDomainRepository(db)
        self._bloom_level_repo = BloomLevelRepository(db)
        self._cp_repo = ComplexProblemRepository(db)
        self._ca_repo = ComplexActivityRepository(db)
        self._kp_repo = KnowledgeProfileRepository(db)
        self._assessment_type_repo = AssessmentTypeRepository(db)

        self._org_repo = OrgRepository(db)
        self._user_repo = UserRepository(db)

    async def build_context(
        self,
        course_id: UUID,
        curriculum_id: UUID,
        org_id: UUID,
        excluded_tool_ids: list[UUID] | None = None,
    ) -> dict:
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
        co_po_justification_by_pair: dict[tuple[UUID, UUID], str] = {}
        if mapping_set:
            for entry in await self._mapping_entry_repo.list_by_set(mapping_set.id):
                if entry.weight > 0:
                    co_po_weights[(entry.course_outcome_id, entry.program_outcome_id)] = entry.weight
                    co_po_justification_by_pair[
                        (entry.course_outcome_id, entry.program_outcome_id)
                    ] = entry.justification

        # ── CO-CP / CO-CA / CO-KP mappings ────────────────────────────────
        co_cp_ids: dict[UUID, set[UUID]] = {}
        co_ca_ids: dict[UUID, set[UUID]] = {}
        co_kp_ids: dict[UUID, set[UUID]] = {}
        co_cp_justification_by_pair: dict[tuple[UUID, UUID], str] = {}
        co_kp_justification_by_pair: dict[tuple[UUID, UUID], str] = {}
        for co in cos:
            co_cp_mappings = await self._co_cp_repo.list_by_co(co.id)
            co_kp_mappings = await self._co_kp_repo.list_by_co(co.id)
            co_cp_ids[co.id] = {m.complex_problem_id for m in co_cp_mappings}
            co_ca_ids[co.id] = {m.complex_activity_id for m in await self._co_ca_repo.list_by_co(co.id)}
            co_kp_ids[co.id] = {m.knowledge_profile_id for m in co_kp_mappings}
            co_cp_justification_by_pair.update(
                {(co.id, m.complex_problem_id): m.justification for m in co_cp_mappings}
            )
            co_kp_justification_by_pair.update(
                {(co.id, m.knowledge_profile_id): m.justification for m in co_kp_mappings}
            )

        # ── Reference data ─────────────────────────────────────────────
        bloom_domains = {d.id: d for d in await self._bloom_domain_repo.list_active(org_id)}
        bloom_levels = await self._bloom_level_repo.list_active(org_id)
        bloom_level_by_id = {b.id: b for b in bloom_levels}

        cps = {c.id: c for c in await self._cp_repo.list_active(org_id)}
        # Complex Engineering Activities (EA) are hidden in the course outline PDF for now.
        # cas = {c.id: c for c in await self._ca_repo.list_active(org_id)}
        kps = {c.id: c for c in await self._kp_repo.list_active(org_id)}

        pos = await self._po_repo.list_active(org_id)
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
                    (_format_ep_code(cps[cid].code) for cid in co_cp_ids[co.id] if cid in cps),
                    key=_natural_key,
                ),
                # Complex Engineering Activities (EA) are intentionally hidden in the
                # course outline PDF for now.
                # "ea_codes": sorted(
                #     (cas[cid].code for cid in co_ca_ids[co.id] if cid in cas),
                #     key=_natural_key,
                # ),
            })

        # ── Mapping justification tables (filtered to COs with mappings) ──
        co_po_justifications = []
        co_kp_justifications = []
        co_ep_justifications = []
        for co in cos:
            po_rows = []
            for (co_id, po_id), justification in co_po_justification_by_pair.items():
                if co_id == co.id and po_id in po_by_id:
                    po_rows.append({
                        "code": po_by_id[po_id].code,
                        "justification": justification,
                    })
            if po_rows:
                co_po_justifications.append({
                    "co_code": co.code,
                    "codes": [row["code"] for row in po_rows],
                    "justifications": sorted(po_rows, key=lambda row: _natural_key(row["code"])),
                })

            kp_rows = []
            for kp_id in co_kp_ids[co.id]:
                if kp_id in kps:
                    kp_rows.append({
                        "code": kps[kp_id].code,
                        "justification": co_kp_justification_by_pair.get((co.id, kp_id), ""),
                    })
            if kp_rows:
                co_kp_justifications.append({
                    "co_code": co.code,
                    "codes": [row["code"] for row in kp_rows],
                    "justifications": sorted(kp_rows, key=lambda row: _natural_key(row["code"])),
                })

            ep_rows = []
            for cp_id in co_cp_ids[co.id]:
                if cp_id in cps:
                    ep_rows.append({
                        "code": _format_ep_code(cps[cp_id].code),
                        "justification": co_cp_justification_by_pair.get((co.id, cp_id), ""),
                    })
            if ep_rows:
                co_ep_justifications.append({
                    "co_code": co.code,
                    "codes": [row["code"] for row in ep_rows],
                    "justifications": sorted(ep_rows, key=lambda row: _natural_key(row["code"])),
                })
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

        kp_legend = [
            {"code": c.code, "description": _format_kp_description(c.code, c.description)}
            for c in kp_columns
        ]
        cp_legend = [
            {
                "code": _format_ep_code(c.code),
                "description": _format_ep_description(c.code, c.description),
            }
            for c in cp_columns
        ]

        # ── Assessment tools + CO-wise marks ─────────────────────────────
        assessment_tools = await self._assessment_tool_repo.list_for_course(curriculum_id, course_id)
        if excluded_tool_ids:
            excluded_set = set(excluded_tool_ids)
            assessment_tools = [t for t in assessment_tools if t.id not in excluded_set]
        assessment_types = {a.id: a for a in await self._assessment_type_repo.list_active(org_id)}
        co_marks_records = await self._co_marks_repo.list_for_course(curriculum_id, course_id)
        section_offerings = await self._section_offering_repo.list_all(org_id, course_id=course_id)

        exam_co_marks_by_type: dict[str, dict[UUID, Decimal]] = {}
        exam_assessment_tools_by_type: dict[str, str] = {}
        for exam_type in ("MID", "FINAL"):
            for offering in section_offerings:
                questions = await self._marksheet_question_repo.list_by_offering(offering.id, exam_type)
                mapped_questions = [q for q in questions if q.course_outcome_id is not None]
                if not mapped_questions:
                    continue
                co_marks: dict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
                for question in mapped_questions:
                    co_marks[question.course_outcome_id] += question.max_marks
                exam_co_marks_by_type[exam_type] = dict(co_marks)
                exam_assessment_tools_by_type[exam_type] = ", ".join(
                    dict.fromkeys(q.label.strip() for q in questions if q.label.strip())
                )
                break

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

            exam_type = None
            normalized_name = name.lower()
            if "mid" in normalized_name:
                exam_type = "MID"
            elif "final" in normalized_name:
                exam_type = "FINAL"

            if exam_type and not co_marks and exam_type in exam_co_marks_by_type:
                for co_id, marks in exam_co_marks_by_type[exam_type].items():
                    co = co_by_id.get(co_id)
                    if co and marks > 0:
                        co_marks[co.code] = _fmt_marks(marks)
                if total_marks == 0:
                    total_marks = sum(exam_co_marks_by_type[exam_type].values(), Decimal("0"))

            grand_total += total_marks
            assessment_rows.append({
                "name": name,
                "total_marks": _fmt_marks(total_marks),
                "display_total_marks": _fmt_tool_marks(total_marks),
                "co_marks": co_marks,
            })

        assessment_co_codes = sorted((co.code for co in cos), key=_natural_key)
        assessment_co_totals = {
            co_code: _fmt_marks(
                sum(
                    Decimal(str(row["co_marks"].get(co_code, "0")))
                    for row in assessment_rows
                    if row["co_marks"].get(co_code)
                )
            )
            for co_code in assessment_co_codes
        }
        assessment_matrix_rows = [
            {
                **row,
                "is_applicable": bool(row["co_marks"]),
                "co_marks_ordered": [row["co_marks"].get(co_code, "") for co_code in assessment_co_codes],
            }
            for row in assessment_rows
        ]

        bloom_marks = await self._bloom_marks_repo.list_for_course(curriculum_id, course_id)
        bloom_domain_by_id = bloom_domains
        cognitive_domain_ids = {
            domain_id
            for domain_id, domain in bloom_domain_by_id.items()
            if domain.name.lower() == "cognitive"
        }
        cognitive_bloom_levels = [
            level
            for level in bloom_levels
            if not cognitive_domain_ids or level.bloom_domain_id in cognitive_domain_ids
        ]
        cognitive_bloom_levels = sorted(cognitive_bloom_levels, key=lambda level: level.order_index)

        bloom_marks_by_component_tool_level: dict[tuple[str, UUID, UUID], Decimal] = {}
        for mark in bloom_marks:
            bloom_marks_by_component_tool_level[
                (mark.component, mark.assessment_type_id, mark.bloom_level_id)
            ] = mark.marks

        cie_tools = [
            {
                "id": tool.assessment_type_id,
                "name": assessment_types[tool.assessment_type_id].name,
                "total": _fmt_marks(
                    next(
                        (
                            Decimal(str(row["total_marks"]))
                            for row in assessment_rows
                            if row["name"] == assessment_types[tool.assessment_type_id].name
                        ),
                        Decimal("0"),
                    )
                )
            }
            for tool in assessment_tools
            if tool.assessment_type_id in assessment_types
            and assessment_types[tool.assessment_type_id].is_sessional
        ]
        for tool in cie_tools:
            tool["display_total"] = _fmt_tool_marks(Decimal(str(tool["total"])))
        cie_total = _fmt_marks(sum(Decimal(str(tool["total"])) for tool in cie_tools))
        cie_bloom_rows = []
        for level in cognitive_bloom_levels:
            marks = [
                _fmt_marks(bloom_marks_by_component_tool_level.get(("CIE", tool["id"], level.id), 0))
                if bloom_marks_by_component_tool_level.get(("CIE", tool["id"], level.id), 0)
                else ""
                for tool in cie_tools
            ]
            cie_bloom_rows.append({"name": level.name, "marks": marks})

        see_marks_by_level: dict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        for mark in bloom_marks:
            if mark.component == "SEE":
                see_marks_by_level[mark.bloom_level_id] += mark.marks
        see_total = _fmt_marks(sum(see_marks_by_level.values()))
        see_bloom_rows = [
            {
                "name": level.name,
                "marks": _fmt_marks(see_marks_by_level[level.id]) if see_marks_by_level[level.id] else "",
            }
            for level in cognitive_bloom_levels
        ]

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
                "assessment_tool_name": _format_assessment_tool_name(row["name"]),
                "co_codes": co_codes,
                "po_codes": po_codes,
                "assessment_tools": (
                    exam_assessment_tools_by_type.get("MID", "")
                    if "mid" in row["name"].lower()
                    else exam_assessment_tools_by_type.get("FINAL", "")
                    if "final" in row["name"].lower()
                    else ""
                ),
            })

        # ── Lesson plan ────────────────────────────────────────────────
        weekly_hours = course.theory_hours + course.lab_hours
        item_ids = [item.id for item in lesson_items]
        cos_by_item = await self._lesson_plan_repo.list_cos_for_items(item_ids)
        pos_by_item = await self._lesson_plan_repo.list_pos_for_items(item_ids)
        lesson_plan = []
        lesson_plan_by_week: dict[int, dict] = {}
        lesson_counts_by_week: dict[int, int] = defaultdict(int)
        for item in lesson_items:
            lesson_counts_by_week[item.week_number] += 1
            display_lesson_label = _format_lesson_label(
                item.lesson_label,
                lesson_counts_by_week[item.week_number],
            )
            entry = {
                "week_number": item.week_number,
                "lesson_label": item.lesson_label,
                "display_lesson_label": display_lesson_label,
                "lesson_reference": _lesson_reference(display_lesson_label),
                "topic": item.topic,
                "tla": item.tla,
                "co_codes": [
                    co_by_id[cid].code for cid in cos_by_item.get(item.id, []) if cid in co_by_id
                ],
                "po_codes": [
                    po_by_id[pid].code for pid in pos_by_item.get(item.id, []) if pid in po_by_id
                ],
                "assessment_strategy": item.assessment_strategy,
            }
            lesson_plan.append(entry)

            week_group = lesson_plan_by_week.setdefault(
                item.week_number,
                {
                    "week_number": item.week_number,
                    "lesson_references": [],
                    "lessons": [],
                    "co_codes": [],
                    "po_codes": [],
                    "tlas": [],
                    "assessment_strategies": [],
                    "hours_label": _format_hours_label(weekly_hours),
                },
            )
            week_group["lesson_references"].append(entry["lesson_reference"])
            week_group["lessons"].append(entry)
            week_group["co_codes"].extend(entry["co_codes"])
            week_group["po_codes"].extend(entry["po_codes"])
            if item.tla:
                week_group["tlas"].append(item.tla)
            if item.assessment_strategy:
                week_group["assessment_strategies"].append(item.assessment_strategy)

        lesson_plan_weeks = []
        for group in lesson_plan_by_week.values():
            group["lesson_summary"] = f"Lesson {' & '.join(group['lesson_references'])}"
            group["co_codes"] = sorted(set(group["co_codes"]), key=_natural_key)
            group["po_codes"] = sorted(set(group["po_codes"]), key=_natural_key)
            group["tla"] = "; ".join(dict.fromkeys(group.pop("tlas")))
            group["assessment_strategy"] = "; ".join(
                dict.fromkeys(group.pop("assessment_strategies"))
            )
            lesson_plan_weeks.append(group)

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
        department = None
        department_logo_url = None
        if curriculum.program_id:
            program = await self._program_repo.get_by_id(curriculum.program_id, org_id)
            if program:
                department = await self._department_repo.get_by_id(program.department_id, org_id)
                if department and department.logo_file_key:
                    department_logo_url = await presigned_get_url(
                        settings.MINIO_BUCKET_LOGOS,
                        department.logo_file_key,
                    )

        return {
            "course": {
                "code": course.code,
                "title": course.title,
                "course_type": course.course_type,
                "credits": course.credits,
                "weekly_hours": weekly_hours,
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
            "bloom_legend": bloom_legend,
            "cp_legend": cp_legend,
            "kp_legend": kp_legend,
            "tool_co_mapping": tool_co_mapping,
            "po_validation": po_validation,
            "lesson_plan": lesson_plan,
            "lesson_plan_weeks": lesson_plan_weeks,
            "assessment_rows": assessment_rows,
            "assessment_co_codes": assessment_co_codes,
            "assessment_co_totals": assessment_co_totals,
            "assessment_matrix_rows": assessment_matrix_rows,
            "cie_tools": cie_tools,
            "cie_total": cie_total,
            "cie_bloom_rows": cie_bloom_rows,
            "see_total": see_total,
            "see_bloom_rows": see_bloom_rows,
            "grand_total": _fmt_marks(grand_total),
            "textbooks": textbooks,
            "references": references,
            "module_leader": module_leader,
            "org": {
                "name": org.name if org else "",
                "short_name": org.short_name if org else "",
                "logo_url": logo_url,
            },
            "department": {
                "name": department.name if department else "",
                "short_name": department.short_name if department else "",
                "logo_url": department_logo_url,
            },
        }


async def render_course_outline_pdf(context: dict) -> bytes:
    from weasyprint import HTML

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    html = env.get_template("course_outline.html").render(**context)

    def _render():
        return HTML(string=html).write_pdf()

    return await anyio.to_thread.run_sync(_render)
