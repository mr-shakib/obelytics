"""
Run: python -m scripts.build_12_semester_curriculum

Builds out the remaining 9 semesters (curriculum terms 4-12) of the 12-semester
BSc CSE curriculum: 18 new courses (2 per term), each with the full OBE
treatment established for the first 9 courses (course outcomes driven to
PUBLISHED, a consolidated ~2-PO CO-PO mapping set published, CO-CP/CA/KP
mappings, objectives, learning materials, a 12-week lesson plan, and the
standard 100-mark evaluation-tool set).
"""

from __future__ import annotations

import asyncio
import sys
from uuid import UUID

sys.path.insert(0, "/home/mr-nacht/Workspace/University/obelytics/backend")

import app.main  # noqa: F401
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, text

from app.modules.curriculum.models import CurriculumTermDefinition
from app.modules.curriculum.schemas import (
    CourseCreate, CourseObjectivesUpdate, CourseLearningMaterialsUpdate, CourseLearningMaterialInput,
    LessonPlanItemsUpdate, LessonPlanItemInput, CourseBloomDomainsUpdate, CourseAssessmentToolsUpdate,
    CourseCOMarksUpdate, CourseCOMarkInput, CourseSlotCreate, PrerequisiteCreate,
)
from app.modules.curriculum.service import (
    CourseService, CourseObjectiveService, CourseLearningMaterialService, CourseLessonPlanService,
    CourseBloomDomainService, CourseAssessmentToolService, CourseAssessmentPatternService,
    CourseSlotService, PrerequisiteService,
)
from app.modules.obe.models import ProgramOutcome
from app.modules.obe.schemas import (
    CourseOutcomeCreate, COPOMappingEntryUpsert, COCPMappingCreate, COCAMappingCreate, COKPMappingCreate,
)
from app.modules.obe.service import COService, MappingSetService, COCPMappingService, COCAMappingService, COKPMappingService
from app.modules.ref_data.models import CourseCategory, AssessmentType, BloomDomain, BloomLevel, ComplexProblem, ComplexActivity, KnowledgeProfile

ORG_ID = UUID("5b7006ed-03d0-4d19-86b9-34d63b0e298a")
CURRICULUM_ID = UUID("a8c8f7aa-cbfa-4492-8719-01ab5f4de8d4")
ACTOR_ID = UUID("70fc5ca6-feab-455a-ab4d-f2369469b81e")

TOOL_TOTALS = {"Mid-term Exam": 25, "Final Exam": 40, "Assignment": 5, "Presentation": 8, "Attendance": 7, "Quiz": 15}

# (code, title, term, course_type, credits, theory_hours, lab_hours, category, prereq, po_pair, cos)
COURSES = [
    dict(code="CSE302", title="Computer Networks", term=4, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE201", pos=("PO1", "PO3"),
         cos=[("Explain the layered architecture and core protocols of computer networks.", "Understand", "CEP1"),
              ("Apply networking protocols to analyze data transmission across network layers.", "Apply", "CEP1"),
              ("Analyze network performance and troubleshoot common connectivity issues.", "Analyze", "CEP3"),
              ("Design a small-scale network topology meeting stated bandwidth and reliability requirements.", "Create", "CEP2")]),
    dict(code="CSE304", title="Software Engineering", term=4, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE203", pos=("PO3", "PO9"),
         cos=[("Explain software development life-cycle models and requirements engineering practices.", "Understand", "CEP1"),
              ("Apply structured design techniques to model software requirements.", "Apply", "CEP1"),
              ("Analyze project scope and risks to select an appropriate development methodology.", "Analyze", "CEP3"),
              ("Design and document a software system as part of a team, following an SE process.", "Create", "CEP2")]),

    dict(code="CSE401", title="Operating Systems", term=5, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE201", pos=("PO1", "PO2"),
         cos=[("Explain process, memory, and file-system management in modern operating systems.", "Understand", "CEP1"),
              ("Apply scheduling and synchronization algorithms to resolve concurrency problems.", "Apply", "CEP1"),
              ("Analyze deadlock and memory-management strategies for correctness and efficiency.", "Analyze", "CEP3"),
              ("Design a solution to a process-synchronization problem using appropriate OS primitives.", "Create", "CEP2")]),
    dict(code="CSE401L", title="Operating Systems Lab", term=5, course_type="LAB", credits=1, th=0, lab=3, category="Lab", prereq="CSE401", pos=("PO3", "PO5"),
         cos=[("Imitate demonstrated shell scripting and system-call examples.", "Imitation", "CEP1"),
              ("Manipulate process and thread primitives independently to complete guided lab tasks.", "Manipulation", "CEP1"),
              ("Implement a small synchronization or scheduling exercise with precision, working with a partner.", "Precision", "CEP2")]),

    dict(code="CSE402", title="Computer Architecture", term=6, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE101", pos=("PO1", "PO2"),
         cos=[("Explain digital logic, instruction sets, and pipelined processor architecture.", "Understand", "CEP1"),
              ("Apply performance-analysis techniques to evaluate processor design trade-offs.", "Apply", "CEP1"),
              ("Analyze memory hierarchy and cache performance for a given workload.", "Analyze", "CEP3"),
              ("Design a simple datapath and control unit meeting stated performance goals.", "Create", "CEP2")]),
    dict(code="CSE404", title="Artificial Intelligence", term=6, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE102", pos=("PO2", "PO4"),
         cos=[("Explain the foundations of search, knowledge representation, and reasoning in AI.", "Understand", "CEP1"),
              ("Apply search and heuristic algorithms to solve intelligent-agent problems.", "Apply", "CEP1"),
              ("Analyze the performance and limitations of classical AI algorithms on benchmark problems.", "Analyze", "CEP3"),
              ("Design an intelligent agent that solves a stated real-world decision problem.", "Create", "CEP2")]),

    dict(code="CSE405", title="Web Engineering", term=7, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE301", pos=("PO3", "PO5"),
         cos=[("Explain client-server architecture and modern web application design principles.", "Understand", "CEP1"),
              ("Apply front-end and back-end frameworks to implement a dynamic web application.", "Apply", "CEP1"),
              ("Analyze web application security and performance requirements.", "Analyze", "CEP3"),
              ("Design and deploy a full-stack web application meeting stated functional requirements.", "Create", "CEP2")]),
    dict(code="CSE405L", title="Web Engineering Lab", term=7, course_type="LAB", credits=1, th=0, lab=3, category="Lab", prereq="CSE405", pos=("PO3", "PO5"),
         cos=[("Imitate demonstrated front-end and back-end code examples.", "Imitation", "CEP1"),
              ("Manipulate a given web application codebase independently to complete guided lab tasks.", "Manipulation", "CEP1"),
              ("Implement and deploy a small full-stack feature with precision, working in a team.", "Precision", "CEP2")]),

    dict(code="CSE407", title="Machine Learning", term=8, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE404", pos=("PO2", "PO4"),
         cos=[("Explain supervised, unsupervised, and evaluation techniques in machine learning.", "Understand", "CEP1"),
              ("Apply standard ML algorithms to train models on a given dataset.", "Apply", "CEP1"),
              ("Analyze model performance using appropriate evaluation metrics and identify overfitting.", "Analyze", "CEP3"),
              ("Design and train a machine learning pipeline that solves a stated prediction problem.", "Create", "CEP2")]),
    dict(code="CSE409", title="Computer Graphics", term=8, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE101", pos=("PO1", "PO3"),
         cos=[("Explain 2D/3D transformation and rendering pipeline fundamentals.", "Understand", "CEP1"),
              ("Apply graphics algorithms to render and transform basic geometric primitives.", "Apply", "CEP1"),
              ("Analyze rendering performance trade-offs for a given graphics pipeline configuration.", "Analyze", "CEP3"),
              ("Design a small interactive graphics application meeting stated visual requirements.", "Create", "CEP2")]),

    dict(code="CSE411", title="Distributed Systems", term=9, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE401", pos=("PO2", "PO3"),
         cos=[("Explain the principles of distributed computing, consistency, and fault tolerance.", "Understand", "CEP1"),
              ("Apply consensus and replication protocols to maintain distributed system consistency.", "Apply", "CEP1"),
              ("Analyze failure scenarios and scalability trade-offs in a distributed architecture.", "Analyze", "CEP3"),
              ("Design a fault-tolerant distributed system component meeting stated availability goals.", "Create", "CEP2")]),
    dict(code="CSE413", title="Information Security", term=9, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE302", pos=("PO1", "PO6"),
         cos=[("Explain core cryptographic primitives and common security threat models.", "Understand", "CEP1"),
              ("Apply cryptographic techniques to secure data in transit and at rest.", "Apply", "CEP1"),
              ("Analyze a system for common vulnerabilities and assess their societal impact.", "Analyze", "CEP6"),
              ("Design a security control that mitigates a stated threat to an information system.", "Create", "CEP2")]),

    dict(code="CSE415", title="Cloud Computing", term=10, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE401", pos=("PO3", "PO5"),
         cos=[("Explain cloud service and deployment models and virtualization fundamentals.", "Understand", "CEP1"),
              ("Apply cloud platform services to deploy a scalable application.", "Apply", "CEP1"),
              ("Analyze cost, performance, and reliability trade-offs across cloud architectures.", "Analyze", "CEP3"),
              ("Design a cloud-native deployment architecture meeting stated scalability requirements.", "Create", "CEP2")]),
    dict(code="CSE415L", title="Cloud Computing Lab", term=10, course_type="LAB", credits=1, th=0, lab=3, category="Lab", prereq="CSE415", pos=("PO3", "PO5"),
         cos=[("Imitate demonstrated cloud deployment examples on a managed platform.", "Imitation", "CEP1"),
              ("Manipulate given cloud infrastructure configurations independently to complete guided tasks.", "Manipulation", "CEP1"),
              ("Deploy and scale a small application on a cloud platform with precision, working in a team.", "Precision", "CEP2")]),

    dict(code="CSE491", title="Project I", term=11, course_type="THESIS_DEFENSE", credits=3, th=0, lab=3, category="Project", prereq="CSE411", pos=("PO3", "PO11"),
         cos=[("Explain the problem statement, scope, and objectives of the proposed capstone project.", "Understand", "CEP1"),
              ("Apply a suitable design methodology to plan the proposed system architecture.", "Apply", "CEP1"),
              ("Analyze project risks, resource needs, and a realistic implementation timeline.", "Analyze", "CEP6"),
              ("Design and partially implement the proposed system, presenting progress to a review panel.", "Create", "CEP2")]),
    dict(code="CSE419", title="Mobile Application Development", term=11, course_type="THEORY", credits=3, th=3, lab=0, category="Core", prereq="CSE304", pos=("PO3", "PO5"),
         cos=[("Explain mobile application architecture and platform-specific design constraints.", "Understand", "CEP1"),
              ("Apply a mobile development framework to implement core application features.", "Apply", "CEP1"),
              ("Analyze mobile application performance and usability requirements.", "Analyze", "CEP3"),
              ("Design and publish a mobile application meeting stated functional requirements.", "Create", "CEP2")]),

    dict(code="CSE492", title="Project II / Thesis", term=12, course_type="THESIS_DEFENSE", credits=4, th=0, lab=4, category="Thesis", prereq="CSE491", pos=("PO3", "PO12"),
         cos=[("Explain the completed system architecture and its contribution relative to existing work.", "Understand", "CEP1"),
              ("Apply the planned methodology to complete implementation of the proposed system.", "Apply", "CEP1"),
              ("Analyze and evaluate the completed system against its original objectives.", "Analyze", "CEP6"),
              ("Design, complete, and defend the final system before an examination panel.", "Create", "CEP2")]),
    dict(code="CSE498", title="Professional Practice Seminar", term=12, course_type="THEORY", credits=1, th=1, lab=0, category="Core", prereq=None, pos=("PO8", "PO10"),
         cos=[("Explain professional codes of ethics and responsibilities relevant to engineering practice.", "Understand", "CEP6"),
              ("Apply professional communication standards to prepare a technical report and presentation.", "Apply", "CEP6"),
              ("Analyze a real-world ethical dilemma in engineering practice.", "Analyze", "CEP6")]),
]

BLOOM_LEVEL_TO_DOMAIN = {
    "Understand": "Cognitive", "Apply": "Cognitive", "Analyze": "Cognitive", "Create": "Cognitive",
    "Imitation": "Psychomotor", "Manipulation": "Psychomotor", "Precision": "Psychomotor",
}
PO_HINT = {
    "PO1": "engineering knowledge", "PO2": "problem analysis", "PO3": "design of solutions",
    "PO4": "investigation", "PO5": "modern tool usage", "PO6": "engineer and society",
    "PO8": "ethics", "PO9": "individual and team work", "PO10": "communication",
    "PO11": "project management", "PO12": "life-long learning",
}
OBJECTIVES_TEMPLATE = [
    "Provide students with a strong theoretical and practical foundation in {topic}.",
    "Develop students' ability to analyze and solve engineering problems related to {topic}.",
    "Foster the ability to design and implement solutions using {topic} independently and in teams.",
    "Prepare students to apply {topic} concepts in subsequent coursework and professional practice.",
]


async def get_ref_maps(db):
    pos = (await db.execute(select(ProgramOutcome).where(
        ProgramOutcome.organization_id == ORG_ID, ProgramOutcome.program_id.is_(None), ProgramOutcome.status == "ACTIVE"
    ))).scalars().all()
    categories = (await db.execute(select(CourseCategory).where(CourseCategory.organization_id == ORG_ID))).scalars().all()
    types = (await db.execute(select(AssessmentType).where(AssessmentType.organization_id == ORG_ID))).scalars().all()
    domains = (await db.execute(select(BloomDomain).where(BloomDomain.organization_id == ORG_ID))).scalars().all()
    levels = (await db.execute(select(BloomLevel).where(BloomLevel.organization_id == ORG_ID))).scalars().all()
    cps = (await db.execute(select(ComplexProblem).where(ComplexProblem.organization_id == ORG_ID))).scalars().all()
    kps = (await db.execute(select(KnowledgeProfile).where(KnowledgeProfile.organization_id == ORG_ID))).scalars().all()
    terms = (await db.execute(select(CurriculumTermDefinition).where(CurriculumTermDefinition.curriculum_id == CURRICULUM_ID))).scalars().all()
    return {
        "po": {p.code: p for p in pos},
        "cat": {c.name: c for c in categories},
        "atype": {t.name: t for t in types},
        "domain": {d.name: d for d in domains},
        "level": {(l.bloom_domain_id, l.name): l for l in levels},
        "cp": {c.code: c for c in cps},
        "kp": {k.code: k for k in kps},
        "term": {t.term_number: t for t in terms},
    }


async def build_course(db, refs, spec, course_id_by_code):
    course_svc, co_svc = CourseService(db), COService(db)
    mapping_svc, cp_svc, kp_svc = MappingSetService(db), COCPMappingService(db), COKPMappingService(db)
    obj_svc, mat_svc, plan_svc = CourseObjectiveService(db), CourseLearningMaterialService(db), CourseLessonPlanService(db)
    domain_svc, tool_svc, pattern_svc = CourseBloomDomainService(db), CourseAssessmentToolService(db), CourseAssessmentPatternService(db)
    slot_svc, prereq_svc = CourseSlotService(db), PrerequisiteService(db)

    course = await course_svc.create(CourseCreate(
        course_category_id=refs["cat"][spec["category"]].id, course_type=spec["course_type"],
        code=spec["code"], title=spec["title"], credits=spec["credits"],
        theory_hours=spec["th"], lab_hours=spec["lab"],
        description=f"{spec['title']} — part of the 12-semester BSc CSE curriculum.",
    ), ORG_ID)
    course_id_by_code[spec["code"]] = course.id

    term = refs["term"][spec["term"]]
    await slot_svc.add_slot(CourseSlotCreate(curriculum_id=CURRICULUM_ID, curriculum_term_definition_id=term.id, course_id=course.id), ORG_ID)

    if spec["prereq"]:
        prereq_id = course_id_by_code.get(spec["prereq"])
        if prereq_id:
            await prereq_svc.add(PrerequisiteCreate(course_id=course.id, prerequisite_course_id=prereq_id), ORG_ID)

    topic = spec["title"].lower()
    await obj_svc.set_for_course(course.id, CourseObjectivesUpdate(statements=[o.format(topic=topic) for o in OBJECTIVES_TEMPLATE]), ORG_ID)

    await mat_svc.set_for_course(course.id, CourseLearningMaterialsUpdate(materials=[
        CourseLearningMaterialInput(material_type="TEXTBOOK", title=f"{spec['title']}: Concepts and Practice", authors="Standard Textbook Author", publisher="Pearson Education", edition_year="2023"),
        CourseLearningMaterialInput(material_type="REFERENCE", title=f"Advanced Topics in {spec['title']}", authors="Reference Author", publisher="McGraw-Hill", edition_year="2022"),
    ]), ORG_ID)

    domain_name = "Psychomotor" if spec["course_type"] == "LAB" else "Cognitive"
    await domain_svc.set_for_course(course.id, CourseBloomDomainsUpdate(bloom_domain_ids=[refs["domain"][domain_name].id]), ORG_ID)

    tool_names = list(TOOL_TOTALS.keys())
    await tool_svc.set_tools(course.id, CURRICULUM_ID, CourseAssessmentToolsUpdate(assessment_type_ids=[refs["atype"][n].id for n in tool_names]), ORG_ID)

    mapping_set = await mapping_svc.get_or_create(CURRICULUM_ID, course.id, ORG_ID, ACTOR_ID)
    co_by_code, po_entries = {}, []
    po_a_code, po_b_code = spec["pos"]
    n_cos = len(spec["cos"])
    for i, (statement, bloom_name, cp_code) in enumerate(spec["cos"], start=1):
        co_code = f"CO{i}"
        domain = refs["domain"][BLOOM_LEVEL_TO_DOMAIN[bloom_name]]
        level = refs["level"][(domain.id, bloom_name)]
        co = await co_svc.create(CourseOutcomeCreate(curriculum_id=CURRICULUM_ID, course_id=course.id, bloom_level_ids=[level.id], code=co_code, statement=statement), ORG_ID, ACTOR_ID)
        co_by_code[co_code] = co

        await cp_svc.create(COCPMappingCreate(course_outcome_id=co.id, complex_problem_id=refs["cp"][cp_code].id, justification=f"{co_code} requires engineering problem-solving characteristic of {cp_code}."), ORG_ID, ACTOR_ID)
        await kp_svc.create(COKPMappingCreate(course_outcome_id=co.id, knowledge_profile_id=refs["kp"]["K1"].id, justification=f"{co_code} draws on foundational engineering knowledge (K1)."), ORG_ID, ACTOR_ID)

        w_a = 2 if i < n_cos else 3
        w_b = 1 if i == 1 else (2 if i < n_cos else 2)
        po_entries.append(COPOMappingEntryUpsert(course_outcome_id=co.id, program_outcome_id=refs["po"][po_a_code].id, weight=w_a, justification=f"{co_code} contributes to {po_a_code} ({PO_HINT[po_a_code]})."))
        po_entries.append(COPOMappingEntryUpsert(course_outcome_id=co.id, program_outcome_id=refs["po"][po_b_code].id, weight=w_b, justification=f"{co_code} contributes to {po_b_code} ({PO_HINT[po_b_code]})."))

    await mapping_svc.upsert_entries(mapping_set.id, po_entries, ORG_ID)
    validation = await mapping_svc.validate(mapping_set.id, ORG_ID)
    if validation.is_valid:
        await mapping_svc.publish(mapping_set.id, ORG_ID, ACTOR_ID)
    else:
        print(f"  [{spec['code']}] WARNING validation failed: {validation.issues}")

    for co in co_by_code.values():
        await co_svc.submit(co.id, ORG_ID, ACTOR_ID)
        await co_svc.approve(co.id, ORG_ID, ACTOR_ID)
        await co_svc.publish(co.id, ORG_ID, ACTOR_ID)

    co_codes_order = [f"CO{i}" for i in range(1, n_cos + 1)]
    lesson_items = []
    weeks_per_co = 12 // n_cos
    for week in range(1, 13):
        idx = min((week - 1) // weeks_per_co, n_cos - 1)
        co_code = co_codes_order[idx]
        lesson_items.append(LessonPlanItemInput(
            week_number=week, lesson_label=f"Week {week}",
            topic=f"{spec['title']} — session {week}: material supporting {co_code}",
            tla="Lecture, in-class problem solving, and Q&A" if spec["course_type"] != "LAB" else "Guided hands-on lab exercise with instructor supervision",
            assessment_strategy="Formative quiz / lab evaluation" if week % 3 != 0 else "Assignment / lab report submission",
            co_ids=[co_by_code[co_code].id], po_ids=[refs["po"][spec["pos"][0]].id, refs["po"][spec["pos"][1]].id],
        ))
    await plan_svc.set_for_course(course.id, CURRICULUM_ID, LessonPlanItemsUpdate(items=lesson_items), ORG_ID)

    co_ids_list = [co_by_code[c].id for c in co_codes_order]
    marks = [CourseCOMarkInput(assessment_type_id=refs["atype"][name].id, course_outcome_id=None, marks=val) for name, val in TOOL_TOTALS.items()]
    if n_cos == 4:
        mid_split, final_split = [13, 12, 0, 0], [5, 10, 10, 15]
    else:
        mid_split, final_split = [13, 12, 0], [10, 15, 15]
    for co_id, m in zip(co_ids_list, mid_split):
        if m: marks.append(CourseCOMarkInput(assessment_type_id=refs["atype"]["Mid-term Exam"].id, course_outcome_id=co_id, marks=m))
    for co_id, f in zip(co_ids_list, final_split):
        if f: marks.append(CourseCOMarkInput(assessment_type_id=refs["atype"]["Final Exam"].id, course_outcome_id=co_id, marks=f))
    await pattern_svc.set_for_course(course.id, CURRICULUM_ID, CourseCOMarksUpdate(marks=marks), ORG_ID)

    print(f"  [{spec['code']}] {spec['title']} — term {spec['term']}, {n_cos} COs, PO {spec['pos']}, DONE")


async def main():
    async with AsyncSessionLocal() as db:
        refs = await get_ref_maps(db)
        course_id_by_code = {}
        # seed with the 9 existing courses so prerequisite lookups resolve
        rows = (await db.execute(text("select code, id from curriculum.courses where organization_id=:o"), {"o": str(ORG_ID)})).all()
        for code, cid in rows:
            course_id_by_code[code] = cid

        for spec in COURSES:
            print(f"=== {spec['code']} ===")
            await build_course(db, refs, spec, course_id_by_code)
            await db.commit()

        print(f"\nDone. {len(COURSES)} new courses built across terms 4-12.")


if __name__ == "__main__":
    asyncio.run(main())
