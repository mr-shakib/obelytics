"""
Run: python -m scripts.seed_authoring_demo --org-id <uuid> [--password <pw>]

Adds what is needed to try AI outcome authoring on top of seed_demo_courses
(run that first). All data is synthetic.

  - Complex engineering activities CEA1–CEA5 (the CEA rule for PO10)
  - A sample PO → required knowledge profile table for PO1–PO8 (the K rule).
    It is an example for testing, not an official accreditation table.
  - PO8 (Ethics) and PO9 (Team Work) in the Affective domain, so the
    "different Bloom domain" warning can show
  - CSE307 Computer Graphics: full course text, no COs — try "Write COs with AI"
  - CSE308 Distributed Systems: deliberately weak COs and no mappings — try
    "Refine with AI" and "Suggest with AI"
  - CSE226 Numerical Methods: course text only, placed in the curriculum so
    scripts.seed_integrity_demo can add its COs, section and marks
  - Two more accounts: a Program Coordinator and a Section Teacher
    (@demo.example.edu), to see what each role may do
  - Ten synthetic job postings for the program — try Workforce Readiness
  - With --outline-out PATH: writes a synthetic CSE307 course outline (.docx) to
    try "Import outline" (keep it under private/, e.g. ../private/demo/)

Safe to re-run: existing rows are left as they are.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import hash_password
from app.modules.curriculum.models import (
    Course,
    CourseBloomDomain,
    CourseLessonPlanItem,
    CourseObjective,
    Curriculum,
    CurriculumCourseSlot,
    CurriculumTermDefinition,
)
from app.modules.iam.models import PasswordCredential, Role, User, UserRoleAssignment
from app.modules.obe.models import (
    CourseOutcome,
    CourseOutcomeBloomLevel,
    POKnowledgeProfile,
    ProgramOutcome,
)
from app.modules.org.models import Organization, Program  # noqa: F401  (foreign-key targets)
from app.modules.ref_data.models import (
    BloomDomain,
    BloomLevel,
    ComplexActivity,
    CourseCategory,
    KnowledgeProfile,
)
from app.modules.workforce.models import MarketPosting

COMPLEX_ACTIVITIES = [
    ("CEA1", "Range of Resources",
     "Involve the use of diverse resources: people, money, equipment, materials, information and technologies."),
    ("CEA2", "Level of Interaction",
     "Require resolution of significant problems arising from interactions between wide-ranging technical, engineering or other issues."),
    ("CEA3", "Innovation",
     "Involve creative use of engineering principles and research-based knowledge in novel ways."),
    ("CEA4", "Consequences for Society and the Environment",
     "Have significant consequences in a range of contexts, characterized by difficulty of prediction and mitigation."),
    ("CEA5", "Familiarity",
     "Can extend beyond previous experiences by applying principles-based approaches."),
]

# Sample K rule table for testing — an institution sets its own on the program page.
PO_REQUIRED_KS = {
    "PO1": ["K1", "K2", "K3", "K4"],
    "PO2": ["K1", "K2", "K4"],
    "PO3": ["K5"],
    "PO4": ["K8"],
    "PO5": ["K6"],
    "PO6": ["K7"],
    "PO7": ["K7"],
    "PO8": ["K7"],
}
AFFECTIVE_POS = ["PO8", "PO9"]

COURSES = [
    {
        "code": "CSE307",
        "title": "Computer Graphics",
        "term": 5,
        "credits": 3,
        "description": (
            "The mathematics and algorithms behind rendering: the graphics pipeline, geometric "
            "transformations, rasterization, visibility, lighting and shading, texturing, curves and "
            "ray tracing, with programmable shaders on the GPU."
        ),
        "topics": [
            "The graphics pipeline and display hardware",
            "Line and polygon rasterization",
            "2D and 3D geometric transformations with homogeneous coordinates",
            "Viewing, projection and the camera model",
            "Clipping algorithms",
            "Hidden surface removal and the z-buffer",
            "Lighting models: ambient, diffuse and specular",
            "Shading: flat, Gouraud and Phong",
            "Texture mapping and sampling",
            "Bezier curves and B-splines",
            "Ray tracing and global illumination basics",
            "Programmable shaders with OpenGL/GLSL",
            "Animation and interaction",
            "Term project demonstrations",
        ],
        "objectives": [
            "Introduce the algorithms and mathematics that turn 3D scenes into images.",
            "Develop the ability to implement rendering techniques with a modern graphics API.",
            "Build skills to analyze the quality and performance trade-offs of rendering methods.",
        ],
        "outcomes": [],
    },
    {
        "code": "CSE308",
        "title": "Distributed Systems",
        "term": 6,
        "credits": 3,
        "description": (
            "Principles of systems whose components run on networked computers: communication, "
            "time and ordering, replication and consistency, consensus, fault tolerance and "
            "distributed storage."
        ),
        "topics": [
            "Characteristics and goals of distributed systems",
            "Communication: remote procedure calls and message passing",
            "Naming and service discovery",
            "Physical and logical clocks; Lamport and vector clocks",
            "Mutual exclusion and leader election",
            "Replication and consistency models",
            "Consensus: Paxos and Raft",
            "Fault tolerance and failure detection",
            "Distributed transactions and two-phase commit",
            "Distributed file systems and key-value stores",
            "The CAP theorem and eventual consistency",
            "MapReduce and large-scale data processing",
            "Security in distributed systems",
            "Case studies and project presentations",
        ],
        "objectives": [
            "Explain how independent computers coordinate to act as one system.",
            "Develop skills to design and evaluate fault-tolerant distributed services.",
        ],
        # Deliberately uneven wording, to try "Refine with AI" and "Suggest with AI".
        "outcomes": [
            ("CO1", "Understand the basic concepts of distributed systems.", ["C2"]),
            ("CO2", "Students will be able to analyze consistency models and replication protocols and "
                    "also implement a fault tolerant key value store", ["C4"]),
            ("CO3", "Implement remote procedure calls and message passing between processes using a "
                    "common framework.", ["C3"]),
            ("CO4", "Evaluate consensus algorithms such as Paxos and Raft for availability and fault "
                    "tolerance under network partitions.", ["C5"]),
        ],
    },
    {
        # COs, a section and marks come from scripts.seed_integrity_demo.
        "code": "CSE226",
        "title": "Numerical Methods",
        "term": 4,
        "credits": 3,
        "description": (
            "Numerical techniques for solving mathematical problems on a computer: errors, roots of "
            "equations, linear systems, interpolation, numerical differentiation and integration, and "
            "ordinary differential equations."
        ),
        "topics": [
            "Errors, floating-point arithmetic and stability",
            "Roots of equations: bisection and false position",
            "Newton-Raphson and secant methods",
            "Linear systems: Gaussian elimination and LU decomposition",
            "Iterative methods: Jacobi and Gauss-Seidel",
            "Interpolation: Lagrange and Newton divided differences",
            "Curve fitting and least squares",
            "Numerical differentiation",
            "Numerical integration: trapezoidal and Simpson's rules",
            "Ordinary differential equations: Euler and Runge-Kutta methods",
            "Boundary value problems",
            "Eigenvalues: power method",
            "Implementation and error analysis case studies",
            "Review",
        ],
        "objectives": [
            "Introduce numerical methods for problems without closed-form solutions.",
            "Develop the ability to choose, implement and analyze numerical algorithms.",
        ],
        "outcomes": [],
    },
]

_POSTING_BASE = "Demo Employer"
POSTINGS = [
    ("Junior Backend Engineer", "We build payment APIs. You will design REST APIs in Python, model data in "
     "PostgreSQL with well-designed SQL, write unit tests, use Git and code review, and deploy services in Docker "
     "containers. Understanding of data structures and algorithm complexity is required. Good written English for "
     "documentation, teamwork in an agile team."),
    ("Software QA Engineer", "Plan and run manual and automated tests. Write test cases from requirements, automate "
     "UI tests, report defects clearly, and work with developers. Knowledge of SQL for test data, basic scripting in "
     "Python, Git, and understanding of the software development life cycle. Communication and attention to detail."),
    ("Data Analyst", "Turn data into decisions. Strong SQL, statistics (hypothesis testing, regression), data "
     "visualization and dashboards, Python with pandas. Clean messy data, explain findings to non-technical managers. "
     "Teamwork and clear written communication. Knowledge of machine learning basics is a plus."),
    ("Cloud / DevOps Engineer", "Run our platform on AWS. Linux administration, Docker and Kubernetes, CI/CD "
     "pipelines, infrastructure as code, monitoring and incident response, networking fundamentals (TCP/IP, DNS, "
     "load balancing). Scripting in Python or Bash. Git. On-call teamwork and clear incident write-ups."),
    ("Frontend Developer (React)", "Build web interfaces in React and TypeScript, consume REST APIs, write unit "
     "tests, care about accessibility and performance. Git and code review. Work closely with designers; "
     "communicate trade-offs clearly. Understanding of HTTP and web security basics is required."),
    ("Junior Machine Learning Engineer", "Train and evaluate models for credit scoring. Python, machine learning "
     "(classification, model evaluation, overfitting), SQL, data preprocessing, and deploying models as APIs. "
     "Understanding of fairness and bias in models. Linear algebra and statistics. Report results clearly."),
    ("Network Engineer", "Configure and troubleshoot routers, switches and firewalls. TCP/IP, subnetting, routing "
     "protocols (OSPF, BGP), VLANs, network monitoring, Linux administration. Document network designs. Work with "
     "vendors and the security team; customer communication."),
    ("Cybersecurity Analyst", "Monitor alerts, investigate incidents, run vulnerability scans, harden Linux "
     "servers, review secure coding issues in web applications (OWASP Top 10), networking fundamentals, scripting in "
     "Python. Write clear incident reports. Professional ethics and confidentiality are essential."),
    ("Mobile App Developer", "Build Android and iOS apps with Flutter. Consume REST APIs, local data storage, "
     "unit testing, Git, app performance. Understanding of object-oriented design and data structures. Work in an "
     "agile team and communicate with product owners."),
    ("Embedded Systems Engineer", "Develop firmware in C for microcontrollers, read datasheets, debug hardware with "
     "oscilloscopes, real-time operating systems, digital logic and computer architecture, communication protocols "
     "(UART, SPI, I2C). Version control with Git. Document designs and work in a team."),
]

USERS = [
    ("coordinator@demo.example.edu", "Demo Program Coordinator", "DEMO0002", "Program Coordinator"),
    ("teacher@demo.example.edu", "Demo Section Teacher", "DEMO0003", "Section Teacher"),
]


async def _one(session: AsyncSession, stmt):
    return (await session.execute(stmt)).scalar_one_or_none()


async def seed_activities(session: AsyncSession, org_id: UUID) -> None:
    for code, name, description in COMPLEX_ACTIVITIES:
        existing = await _one(session, select(ComplexActivity).where(
            ComplexActivity.organization_id == org_id, ComplexActivity.code == code))
        if existing is None:
            session.add(ComplexActivity(organization_id=org_id, code=code, name=name,
                                        description=description, is_active=True))
            print(f"  Created CEA: {code} - {name}")


async def seed_po_rules(session: AsyncSession, org_id: UUID, program_id: UUID) -> None:
    pos = {po.code: po for po in (await session.execute(select(ProgramOutcome).where(
        ProgramOutcome.organization_id == org_id, ProgramOutcome.program_id == program_id,
        ProgramOutcome.status == "ACTIVE",
    ))).scalars().all()}
    kps = {kp.code: kp for kp in (await session.execute(select(KnowledgeProfile).where(
        KnowledgeProfile.organization_id == org_id))).scalars().all()}
    if not pos or not kps:
        raise RuntimeError("Run scripts.seed_demo_courses first: no POs or knowledge profiles found.")

    added = 0
    for po_code, k_codes in PO_REQUIRED_KS.items():
        po = pos.get(po_code)
        if po is None:
            continue
        have = set((await session.execute(select(POKnowledgeProfile.knowledge_profile_id).where(
            POKnowledgeProfile.program_outcome_id == po.id))).scalars().all())
        for k_code in k_codes:
            kp = kps.get(k_code)
            if kp and kp.id not in have:
                session.add(POKnowledgeProfile(program_outcome_id=po.id, knowledge_profile_id=kp.id))
                added += 1
    print(f"  PO → knowledge profile rules: {added} added")

    affective = await _one(session, select(BloomDomain).where(
        BloomDomain.organization_id == org_id, BloomDomain.name == "Affective"))
    if affective:
        for code in AFFECTIVE_POS:
            if code in pos:
                pos[code].bloom_domain_id = affective.id
        print(f"  {', '.join(AFFECTIVE_POS)} set to the Affective domain")


async def seed_courses(session: AsyncSession, org_id: UUID, curriculum: Curriculum) -> None:
    category = await _one(session, select(CourseCategory).where(
        CourseCategory.organization_id == org_id, CourseCategory.name == "Core"))
    if category is None:
        category = (await session.execute(select(CourseCategory).where(
            CourseCategory.organization_id == org_id).limit(1))).scalar_one()
    cognitive = await _one(session, select(BloomDomain).where(
        BloomDomain.organization_id == org_id, BloomDomain.name == "Cognitive"))
    levels = {lvl.code: lvl for lvl in (await session.execute(select(BloomLevel).where(
        BloomLevel.organization_id == org_id))).scalars().all()}
    terms = {t.term_number: t for t in (await session.execute(select(CurriculumTermDefinition).where(
        CurriculumTermDefinition.curriculum_id == curriculum.id))).scalars().all()}

    for source in COURSES:
        course = await _one(session, select(Course).where(
            Course.organization_id == org_id, Course.code == source["code"], Course.status == "ACTIVE"))
        if course is not None:
            print(f"  = {source['code']} already exists")
            continue
        course = Course(
            organization_id=org_id, course_category_id=category.id, course_type="THEORY",
            code=source["code"], title=source["title"], credits=source["credits"],
            theory_hours=3, lab_hours=0, description=source["description"],
            syllabus_content="\n".join(f"{i}. {t}" for i, t in enumerate(source["topics"], 1)),
            status="ACTIVE",
        )
        session.add(course)
        await session.flush()
        session.add(CurriculumCourseSlot(
            curriculum_id=curriculum.id, curriculum_term_definition_id=terms[source["term"]].id,
            course_id=course.id, is_elective=False,
        ))
        if cognitive:
            session.add(CourseBloomDomain(course_id=course.id, bloom_domain_id=cognitive.id))
        session.add_all([
            CourseObjective(course_id=course.id, order_index=i, statement=text)
            for i, text in enumerate(source["objectives"], 1)
        ])
        session.add_all([
            CourseLessonPlanItem(
                curriculum_id=curriculum.id, course_id=course.id, week_number=week,
                lesson_label=f"Lesson {week}", topic=topic, order_index=week,
            )
            for week, topic in enumerate(source["topics"], 1)
        ])
        for code, statement, level_codes in source["outcomes"]:
            co = CourseOutcome(organization_id=org_id, curriculum_id=curriculum.id,
                               course_id=course.id, code=code, statement=statement)
            session.add(co)
            await session.flush()
            session.add_all([
                CourseOutcomeBloomLevel(course_outcome_id=co.id, bloom_level_id=levels[c].id)
                for c in level_codes if c in levels
            ])
        print(f"  Created course: {source['code']} - {source['title']} "
              f"({len(source['outcomes'])} COs, no mappings)")


async def seed_users(session: AsyncSession, org_id: UUID, program_id: UUID, password: str) -> None:
    roles = {r.name: r for r in (await session.execute(select(Role).where(
        Role.organization_id == org_id))).scalars().all()}
    admin = await _one(session, select(User).where(User.organization_id == org_id).order_by(User.created_at).limit(1))
    for email, name, employee_id, role_name in USERS:
        if await _one(session, select(User).where(User.email == email)):
            print(f"  = {email} already exists")
            continue
        user = User(organization_id=org_id, email=email, full_name=name, employee_id=employee_id,
                    status="ACTIVE")
        session.add(user)
        await session.flush()
        session.add(PasswordCredential(user_id=user.id, hashed_password=hash_password(password),
                                       must_change_password=False))
        session.add(UserRoleAssignment(user_id=user.id, role_id=roles[role_name].id,
                                       scope_type="PROGRAM", scope_id=program_id,
                                       assigned_by=admin.id if admin else user.id))
        print(f"  Created {role_name}: {email}")


async def seed_postings(session: AsyncSession, org_id: UUID, program_id: UUID) -> None:
    existing = set((await session.execute(select(MarketPosting.title).where(
        MarketPosting.program_id == program_id))).scalars().all())
    added = 0
    for i, (title, text) in enumerate(POSTINGS, 1):
        if title in existing:
            continue
        session.add(MarketPosting(
            organization_id=org_id, program_id=program_id, title=title,
            employer=f"{_POSTING_BASE} {chr(64 + i)}", source="synthetic demo posting", text=text,
        ))
        added += 1
    print(f"  Job postings: {added} added (skills are read at the first analysis)")


OUTLINE_LINES = [
    "Course Outline — CSE307 Computer Graphics (3 credits)",
    "Course Description: This course introduces the mathematics and algorithms that turn three-dimensional "
    "scenes into images, from the graphics pipeline and transformations to lighting, texturing and ray tracing, "
    "with practical work using programmable shaders.",
    "Course Objectives",
    "1. To introduce the graphics pipeline and the mathematics of geometric transformations.",
    "2. To develop the ability to implement rendering techniques with a modern graphics API.",
    "3. To build skills in evaluating the quality and performance of rendering methods.",
    "Course Outcomes (COs) — on successful completion, students will be able to:",
    "CO1 Explain the stages of the graphics pipeline and how a 3D scene becomes an image. (C2)",
    "CO2 Apply homogeneous transformations, viewing and projection to position objects and the camera. (C3)",
    "CO3 Implement rasterization, hidden surface removal and Phong shading with programmable shaders. (C3)",
    "CO4 Evaluate rasterization against ray tracing for image quality and performance on a given scene. (C5)",
    "Weekly Plan",
    "Week 1: The graphics pipeline and display hardware",
    "Week 2: Line and polygon rasterization",
    "Week 3: 2D and 3D transformations with homogeneous coordinates",
    "Week 4: Viewing, projection and the camera model",
    "Week 5: Clipping algorithms",
    "Week 6: Hidden surface removal and the z-buffer",
    "Week 7: Lighting models and shading",
    "Week 8: Texture mapping and sampling",
    "Week 9: Curves and surfaces",
    "Week 10: Ray tracing basics",
    "Week 11: Programmable shaders with GLSL",
    "Week 12: Project demonstrations",
]


def write_outline(path: str) -> None:
    import io
    import zipfile
    from xml.sax.saxutils import escape

    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    body = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{escape(line)}</w:t></w:r></w:p>' for line in OUTLINE_LINES
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/'
        'content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
        'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName='
        '"/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.'
        'document.main+xml"/></Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/'
        '2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
        '2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", f"<w:document {ns}><w:body>{body}</w:body></w:document>")
    target = os.path.abspath(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "wb") as handle:
        handle.write(buffer.getvalue())
    print(f"  Wrote synthetic outline: {target}")


async def main(org_id: UUID, password: str) -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        curriculum = await _one(session, select(Curriculum).where(
            Curriculum.organization_id == org_id).order_by(Curriculum.created_at).limit(1))
        if curriculum is None:
            raise RuntimeError("Run scripts.seed_demo_courses first: no curriculum found.")
        await seed_activities(session, org_id)
        await seed_po_rules(session, org_id, curriculum.program_id)
        await seed_courses(session, org_id, curriculum)
        await seed_users(session, org_id, curriculum.program_id, password)
        await seed_postings(session, org_id, curriculum.program_id)
        await session.commit()
    await engine.dispose()
    print("\nAuthoring demo data ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic data for trying AI outcome authoring")
    parser.add_argument("--org-id", required=True)
    parser.add_argument("--password", default="Demo@2026", help="Password for the two extra accounts")
    parser.add_argument("--outline-out", help="Also write a synthetic CSE307 outline .docx here")
    args = parser.parse_args()
    asyncio.run(main(UUID(args.org_id), args.password))
    if args.outline_out:
        write_outline(args.outline_out)
