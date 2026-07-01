"""
Run: python -m scripts.seed_demo_courses [--org-id <uuid>] [--curriculum-id <uuid>]

Creates 20 fully detailed demo CSE courses:
  - course catalog rows with syllabus content
  - course objectives
  - learning materials
  - Bloom domains
  - curriculum course slots
  - course outcomes with Bloom levels
  - CO delivery methods
  - CO-PO mapping sets and entries
  - assessment tools, CO marks, Bloom marks
  - 14-week lesson plans linked to COs and POs

Safe to re-run: courses are upserted by active course code, while detail rows for
these courses are replaced.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from decimal import Decimal
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.modules.curriculum.models import (
    Course,
    CourseAssessmentTool,
    CourseBloomDomain,
    CourseBloomMarks,
    CourseCOMarks,
    CourseLearningMaterial,
    CourseLessonPlanItem,
    CourseLessonPlanItemCO,
    CourseLessonPlanItemPO,
    CourseObjective,
    CoursePrerequisite,
    Curriculum,
    CurriculumCourseSlot,
    CurriculumTermDefinition,
)
from app.modules.obe.models import (
    COCPMapping,
    CODeliveryMethod,
    COKPMapping,
    COPOMappingEntry,
    COPOMappingSet,
    CourseOutcome,
    CourseOutcomeBloomLevel,
    ProgramOutcome,
)
from app.modules.org.models import Department, Organization, Program
from app.modules.ref_data.models import (
    AssessmentType,
    BloomDomain,
    BloomLevel,
    ComplexProblem,
    CourseCategory,
    DeliveryMethod,
    KnowledgeProfile,
)
from scripts.seed_reference_data import seed as seed_reference_data

COURSES = [
    {
        "code": "CSE101",
        "title": "Structured Programming",
        "term": 1,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Introduces procedural problem solving using C with emphasis on control flow, functions, arrays, pointers, and disciplined testing.",
        "topics": [
            "Problem solving and algorithmic thinking",
            "C program structure, variables, types, and operators",
            "Selection and iterative control structures",
            "Functions, scope, recursion, and modular design",
            "Arrays, strings, and memory layout",
            "Pointers, dynamic allocation, and file processing",
            "Debugging, testing, and program documentation",
        ],
        "textbook": ("C Programming: A Modern Approach", "K. N. King", "W. W. Norton", "2nd Edition, 2008"),
    },
    {
        "code": "CSE102",
        "title": "Discrete Mathematics",
        "term": 1,
        "category": "Core",
        "type": "THEORY",
        "credits": 3,
        "theory_hours": 3,
        "lab_hours": 0,
        "description": "Builds mathematical foundations for computing through logic, proof, sets, relations, functions, counting, recurrence, and graph theory.",
        "topics": [
            "Logic, propositions, predicates, and inference",
            "Proof techniques and mathematical induction",
            "Sets, relations, functions, and orders",
            "Counting, pigeonhole principle, and inclusion-exclusion",
            "Recurrences and discrete probability foundations",
            "Graphs, trees, connectivity, and traversals",
            "Applications in computing and algorithm analysis",
        ],
        "textbook": ("Discrete Mathematics and Its Applications", "Kenneth H. Rosen", "McGraw-Hill", "8th Edition, 2019"),
    },
    {
        "code": "CSE103",
        "title": "Digital Logic Design",
        "term": 1,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Covers number systems, Boolean algebra, combinational and sequential circuit design, and practical logic implementation.",
        "topics": [
            "Number systems, codes, and binary arithmetic",
            "Boolean algebra and logic minimization",
            "Combinational circuit design",
            "MSI components, decoders, multiplexers, and adders",
            "Flip-flops, counters, and registers",
            "Sequential circuit analysis and design",
            "Hardware description and circuit verification",
        ],
        "textbook": ("Digital Design", "M. Morris Mano and Michael D. Ciletti", "Pearson", "6th Edition, 2018"),
    },
    {
        "code": "CSE104",
        "title": "Data Structures",
        "term": 2,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Studies linear and nonlinear data structures, abstraction, complexity, and implementation trade-offs for efficient software.",
        "topics": [
            "Abstract data types and complexity review",
            "Arrays, linked lists, stacks, and queues",
            "Trees, binary search trees, and heaps",
            "Hash tables and collision resolution",
            "Graphs and graph representations",
            "Sorting and searching algorithms",
            "Designing data-structure-backed applications",
        ],
        "textbook": ("Data Structures and Algorithm Analysis in C++", "Mark Allen Weiss", "Pearson", "4th Edition, 2014"),
    },
    {
        "code": "CSE105",
        "title": "Object Oriented Programming",
        "term": 2,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Develops object-oriented modeling and programming skills using encapsulation, inheritance, polymorphism, interfaces, and patterns.",
        "topics": [
            "Objects, classes, fields, and methods",
            "Encapsulation, constructors, and access control",
            "Inheritance, interfaces, and polymorphism",
            "Exception handling and collections",
            "Generic programming and reusable components",
            "UML class modeling and design principles",
            "Testing and refactoring object-oriented systems",
        ],
        "textbook": ("Core Java Volume I: Fundamentals", "Cay S. Horstmann", "Pearson", "12th Edition, 2021"),
    },
    {
        "code": "CSE106",
        "title": "Computer Organization and Architecture",
        "term": 2,
        "category": "Core",
        "type": "THEORY",
        "credits": 3,
        "theory_hours": 3,
        "lab_hours": 0,
        "description": "Explores processor organization, instruction sets, memory hierarchy, I/O, pipelining, and performance evaluation.",
        "topics": [
            "Computer system components and performance metrics",
            "Instruction set architecture and assembly basics",
            "Arithmetic logic units and datapath design",
            "Control unit design and micro-operations",
            "Memory hierarchy, cache, and virtual memory",
            "Pipelining and hazards",
            "I/O organization and storage systems",
        ],
        "textbook": ("Computer Organization and Design", "David A. Patterson and John L. Hennessy", "Morgan Kaufmann", "6th Edition, 2020"),
    },
    {
        "code": "CSE201",
        "title": "Algorithms",
        "term": 3,
        "category": "Core",
        "type": "THEORY",
        "credits": 3,
        "theory_hours": 3,
        "lab_hours": 0,
        "description": "Analyzes algorithm design paradigms and complexity for sorting, graph, greedy, divide-and-conquer, and dynamic programming problems.",
        "topics": [
            "Asymptotic notation and recurrence solving",
            "Divide-and-conquer algorithms",
            "Greedy method and matroid intuition",
            "Dynamic programming design",
            "Graph traversal and shortest paths",
            "Minimum spanning trees and network flow basics",
            "NP-completeness and approximation awareness",
        ],
        "textbook": ("Introduction to Algorithms", "Cormen, Leiserson, Rivest, and Stein", "MIT Press", "4th Edition, 2022"),
    },
    {
        "code": "CSE202",
        "title": "Database Systems",
        "term": 3,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Presents conceptual modeling, relational design, SQL, normalization, transactions, indexing, and database application development.",
        "topics": [
            "Database system architecture and data models",
            "ER modeling and relational schema design",
            "Relational algebra and SQL querying",
            "Normalization and dependency theory",
            "Transactions, concurrency, and recovery",
            "Indexes, query processing, and optimization",
            "Application integration and security basics",
        ],
        "textbook": ("Database System Concepts", "Silberschatz, Korth, and Sudarshan", "McGraw-Hill", "7th Edition, 2019"),
    },
    {
        "code": "CSE203",
        "title": "Operating Systems",
        "term": 3,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Examines process management, synchronization, memory management, file systems, storage, and OS-level resource protection.",
        "topics": [
            "OS structure, system calls, and processes",
            "Threads, scheduling, and context switching",
            "Synchronization, deadlocks, and concurrency bugs",
            "Memory allocation, paging, and virtual memory",
            "File systems and storage management",
            "Protection, security, and virtualization",
            "Shell scripting and kernel-facing programming",
        ],
        "textbook": ("Operating System Concepts", "Silberschatz, Galvin, and Gagne", "Wiley", "10th Edition, 2018"),
    },
    {
        "code": "CSE204",
        "title": "Software Engineering",
        "term": 4,
        "category": "Core",
        "type": "THEORY",
        "credits": 3,
        "theory_hours": 3,
        "lab_hours": 0,
        "description": "Covers requirements, architecture, design, testing, maintenance, project management, and quality practices for software systems.",
        "topics": [
            "Software process models and agile practice",
            "Requirements elicitation and specification",
            "Architecture styles and design modeling",
            "Implementation quality and code review",
            "Verification, validation, and test strategy",
            "Project planning, estimation, and risk",
            "Maintenance, evolution, and DevOps awareness",
        ],
        "textbook": ("Software Engineering", "Ian Sommerville", "Pearson", "10th Edition, 2015"),
    },
    {
        "code": "CSE205",
        "title": "Computer Networks",
        "term": 4,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Introduces layered networking, protocols, addressing, routing, transport reliability, application protocols, and network security basics.",
        "topics": [
            "Network architecture, layering, and performance",
            "Physical and data link layer concepts",
            "Ethernet, switching, and wireless LANs",
            "IP addressing, subnetting, and routing",
            "Transport protocols, TCP, UDP, and congestion",
            "DNS, HTTP, email, and socket programming",
            "Security, firewalls, and network troubleshooting",
        ],
        "textbook": ("Computer Networking: A Top-Down Approach", "James F. Kurose and Keith W. Ross", "Pearson", "8th Edition, 2021"),
    },
    {
        "code": "CSE206",
        "title": "Theory of Computation",
        "term": 4,
        "category": "Core",
        "type": "THEORY",
        "credits": 3,
        "theory_hours": 3,
        "lab_hours": 0,
        "description": "Studies formal languages, automata, grammars, computability, decidability, and complexity foundations.",
        "topics": [
            "Languages, alphabets, strings, and proofs",
            "Finite automata and regular expressions",
            "Regular languages and pumping lemma",
            "Context-free grammars and pushdown automata",
            "Turing machines and Church-Turing thesis",
            "Decidability and reducibility",
            "Complexity classes and intractability",
        ],
        "textbook": ("Introduction to the Theory of Computation", "Michael Sipser", "Cengage", "3rd Edition, 2012"),
    },
    {
        "code": "CSE301",
        "title": "Web Engineering",
        "term": 5,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Develops modern web applications using client-server architecture, APIs, persistence, authentication, testing, and deployment practice.",
        "topics": [
            "Web architecture, HTTP, and browser runtime",
            "HTML, CSS, JavaScript, and accessibility",
            "Server-side routing and REST API design",
            "Authentication, sessions, and authorization",
            "Database-backed web applications",
            "Frontend state, components, and testing",
            "Deployment, monitoring, and web security",
        ],
        "textbook": ("Web Engineering", "Gerti Kappel, Birgit Proll, Siegfried Reich, and Werner Retschitzegger", "Wiley", "2006"),
    },
    {
        "code": "CSE302",
        "title": "Artificial Intelligence",
        "term": 5,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Introduces intelligent agents, search, knowledge representation, reasoning, uncertainty, planning, and learning foundations.",
        "topics": [
            "Intelligent agents and problem formulation",
            "Uninformed and informed search",
            "Adversarial search and game playing",
            "Knowledge representation and inference",
            "Probabilistic reasoning and Bayesian networks",
            "Planning and constraint satisfaction",
            "Machine learning overview and AI ethics",
        ],
        "textbook": ("Artificial Intelligence: A Modern Approach", "Stuart Russell and Peter Norvig", "Pearson", "4th Edition, 2020"),
    },
    {
        "code": "CSE303",
        "title": "Compiler Design",
        "term": 5,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Covers lexical analysis, parsing, semantic analysis, intermediate representation, optimization, and code generation.",
        "topics": [
            "Compiler phases and language processing tools",
            "Lexical analysis and regular specifications",
            "Context-free grammars and parsing",
            "Syntax-directed translation and semantic checks",
            "Intermediate code generation",
            "Runtime environments and storage allocation",
            "Optimization and target code generation",
        ],
        "textbook": ("Compilers: Principles, Techniques, and Tools", "Aho, Lam, Sethi, and Ullman", "Pearson", "2nd Edition, 2006"),
    },
    {
        "code": "CSE304",
        "title": "Machine Learning",
        "term": 6,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Builds supervised and unsupervised learning foundations with model evaluation, feature engineering, and responsible use.",
        "topics": [
            "Learning problems, data preparation, and metrics",
            "Linear and logistic regression",
            "Decision trees and ensemble methods",
            "Support vector machines and kernels",
            "Clustering and dimensionality reduction",
            "Neural network foundations",
            "Model selection, fairness, and deployment risks",
        ],
        "textbook": ("Pattern Recognition and Machine Learning", "Christopher M. Bishop", "Springer", "2006"),
    },
    {
        "code": "CSE305",
        "title": "Information Security",
        "term": 6,
        "category": "Core",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Explores security principles, cryptography, authentication, access control, software vulnerabilities, and operational defense.",
        "topics": [
            "Security goals, threat modeling, and risk",
            "Classical and modern cryptography",
            "Public-key infrastructure and authentication",
            "Access control and security protocols",
            "Web and software vulnerabilities",
            "Network security and intrusion detection",
            "Incident response, policy, and ethics",
        ],
        "textbook": ("Computer Security: Principles and Practice", "William Stallings and Lawrie Brown", "Pearson", "4th Edition, 2018"),
    },
    {
        "code": "CSE306",
        "title": "Human Computer Interaction",
        "term": 6,
        "category": "Elective",
        "type": "THEORY",
        "credits": 3,
        "theory_hours": 3,
        "lab_hours": 0,
        "description": "Studies user-centered design, interaction principles, prototyping, usability evaluation, accessibility, and design ethics.",
        "topics": [
            "Human factors and interaction principles",
            "User research and requirements for interfaces",
            "Information architecture and interaction design",
            "Prototyping and design critique",
            "Usability testing and analytics",
            "Accessibility and inclusive design",
            "Ethics, dark patterns, and design communication",
        ],
        "textbook": ("Interaction Design: Beyond Human-Computer Interaction", "Sharp, Rogers, and Preece", "Wiley", "6th Edition, 2023"),
    },
    {
        "code": "CSE401",
        "title": "Cloud Computing",
        "term": 7,
        "category": "Elective",
        "type": "THEORY_LAB",
        "credits": 4,
        "theory_hours": 3,
        "lab_hours": 2,
        "description": "Examines virtualization, containers, cloud service models, distributed storage, orchestration, resilience, and cloud operations.",
        "topics": [
            "Cloud service models and deployment models",
            "Virtualization and containerization",
            "Distributed storage and object storage",
            "Cloud networking and identity",
            "Orchestration, scaling, and resilience",
            "Observability and cost-aware operations",
            "Cloud-native application design",
        ],
        "textbook": ("Cloud Computing: Concepts, Technology and Architecture", "Thomas Erl, Zaigham Mahmood, and Ricardo Puttini", "Prentice Hall", "2013"),
    },
    {
        "code": "CSE402",
        "title": "Capstone Project",
        "term": 8,
        "category": "Project",
        "type": "THESIS_DEFENSE",
        "credits": 6,
        "theory_hours": 0,
        "lab_hours": 6,
        "description": "Integrates computing knowledge through a team project involving proposal, design, implementation, evaluation, documentation, and defense.",
        "topics": [
            "Problem identification and stakeholder analysis",
            "Proposal writing and feasibility study",
            "Architecture and technical planning",
            "Iterative implementation and sprint reviews",
            "Testing, validation, and risk handling",
            "Technical report writing",
            "Final presentation and defense",
        ],
        "textbook": ("The Software Project Manager's Bridge to Agility", "Michele Sliger and Stacia Broderick", "Addison-Wesley", "2008"),
    },
]

PO_STATEMENTS = [
    ("PO1", "Engineering Knowledge", "Apply mathematics, natural science, computing fundamentals, and engineering specialization to solve computing problems."),
    ("PO2", "Problem Analysis", "Identify, formulate, research literature, and analyze complex computing problems using first principles."),
    ("PO3", "Design/Development", "Design solutions for complex computing problems with appropriate consideration for public health, safety, culture, society, and environment."),
    ("PO4", "Investigation", "Conduct investigation of complex problems using research methods, experiments, data analysis, and synthesis."),
    ("PO5", "Modern Tool Usage", "Create, select, and apply modern computing and engineering tools with awareness of limitations."),
    ("PO6", "The Engineer and Society", "Apply reasoning informed by contextual knowledge to assess societal, legal, and cultural issues."),
    ("PO7", "Environment and Sustainability", "Understand and evaluate sustainability and environmental impact of professional computing solutions."),
    ("PO8", "Ethics", "Apply ethical principles and commit to professional responsibilities and norms of computing practice."),
    ("PO9", "Individual and Team Work", "Function effectively as an individual and as a member or leader in diverse teams."),
    ("PO10", "Communication", "Communicate effectively on complex computing activities with technical and non-technical audiences."),
    ("PO11", "Project Management and Finance", "Demonstrate knowledge of engineering management principles and apply them to projects."),
    ("PO12", "Life-long Learning", "Recognize the need for and prepare for independent and life-long learning."),
]

COMPLEX_PROBLEMS = [
    (
        "CEP1",
        "Depth of Knowledge",
        "Requires principles-based analysis using advanced computing, mathematics, or engineering knowledge.",
    ),
    (
        "CEP2",
        "Range of Conflicting Requirements",
        "Contains wide-ranging or conflicting technical, stakeholder, business, or societal requirements.",
    ),
    (
        "CEP3",
        "Depth of Analysis",
        "Requires abstraction, modeling, investigation, or interpretation of incomplete and uncertain information.",
    ),
    (
        "CEP4",
        "Familiarity of Issues",
        "Includes issues that are infrequently encountered and cannot be solved by routine procedures alone.",
    ),
    (
        "CEP5",
        "Extent of Applicable Codes",
        "Requires selection and application of appropriate standards, methods, regulations, or professional practices.",
    ),
    (
        "CEP6",
        "Stakeholder and Consequence",
        "Has consequences for users, organizations, society, security, sustainability, or professional responsibility.",
    ),
    (
        "CEP7",
        "Interdependence",
        "Includes interdependent components, constraints, interfaces, or systems that must be considered together.",
    ),
]

KNOWLEDGE_PROFILES = [
    ("K1", "Natural sciences, mathematics, and computing fundamentals that support problem formulation and analysis."),
    ("K2", "Conceptually based mathematics, numerical analysis, statistics, and formal reasoning for computing systems."),
    ("K3", "Engineering fundamentals and abstraction principles that connect computing theory to practical design."),
    ("K4", "Specialist computing knowledge for algorithms, data, systems, networks, software, and intelligent applications."),
    ("K5", "Engineering design knowledge for requirements, architecture, validation, trade-offs, and constraints."),
    ("K6", "Engineering practice knowledge including tools, experimentation, data handling, and professional workflows."),
    ("K7", "Societal, ethical, legal, environmental, economic, and sustainability knowledge for computing practice."),
    ("K8", "Research literature, emerging technologies, and independent learning required for modern computing work."),
]


async def _one(session: AsyncSession, stmt):
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def resolve_org(session: AsyncSession, org_id: UUID | None) -> Organization:
    if org_id:
        org = await _one(session, select(Organization).where(Organization.id == org_id))
        if org is None:
            raise RuntimeError(f"Organization not found: {org_id}")
        return org

    org = await _one(session, select(Organization).order_by(Organization.created_at).limit(1))
    if org is not None:
        return org

    org = Organization(name="Demo University", short_name="DEMO")
    session.add(org)
    await session.flush()
    await session.refresh(org)
    print(f"  Created organization: {org.name} ({org.id})")
    return org


async def ensure_reference_maps(session: AsyncSession, org_id: UUID) -> dict[str, dict[str, object]]:
    await seed_reference_data(org_id)

    async def by_name(model):
        rows = (
            await session.execute(
                select(model).where(model.organization_id == org_id, model.is_active.is_(True))
            )
        ).scalars().all()
        return {row.name: row for row in rows}

    bloom_domains = await by_name(BloomDomain)
    delivery_methods = await by_name(DeliveryMethod)
    categories = await by_name(CourseCategory)
    assessment_types = await by_name(AssessmentType)

    levels = (
        await session.execute(
            select(BloomLevel).where(
                BloomLevel.organization_id == org_id,
                BloomLevel.is_active.is_(True),
            )
        )
    ).scalars().all()
    bloom_levels = {level.code: level for level in levels}

    attendance = await _one(
        session,
        select(AssessmentType).where(
            AssessmentType.organization_id == org_id,
            AssessmentType.name == "Attendance",
        ),
    )
    if attendance is None:
        attendance = AssessmentType(
            organization_id=org_id,
            name="Attendance",
            is_sessional=False,
            is_active=True,
        )
        session.add(attendance)
        await session.flush()
        assessment_types["Attendance"] = attendance
        print("  Created assessment type: Attendance")
    else:
        attendance.is_active = True
        assessment_types["Attendance"] = attendance

    complex_problems: dict[str, ComplexProblem] = {}
    for code, name, description in COMPLEX_PROBLEMS:
        legacy_codes = [
            code.replace("CEP", "CP", 1),
            code.replace("CEP", "P", 1),
        ]
        record = await _one(
            session,
            select(ComplexProblem).where(
                ComplexProblem.organization_id == org_id,
                ComplexProblem.code == code,
            ),
        )
        legacy_records = [
            row
            for row in (
                await session.execute(
                    select(ComplexProblem).where(
                        ComplexProblem.organization_id == org_id,
                        ComplexProblem.code.in_(legacy_codes),
                    )
                )
            ).scalars().all()
        ]
        legacy_record = legacy_records[0] if legacy_records else None
        if record is None and legacy_record is not None:
            record = legacy_record
            record.code = code
        if record is None:
            record = ComplexProblem(
                organization_id=org_id,
                code=code,
                name=name,
                description=description,
                is_active=True,
            )
            session.add(record)
            await session.flush()
            print(f"  Created CEP: {code} - {name}")
        else:
            record.name = name
            record.description = description
            record.is_active = True
            if legacy_record is record:
                print(f"  Renamed legacy CEP attribute: {legacy_record.code} -> {code}")
        for legacy in legacy_records:
            if legacy is not record:
                legacy.is_active = False
        complex_problems[code] = record

    knowledge_profiles: dict[str, KnowledgeProfile] = {}
    for code, description in KNOWLEDGE_PROFILES:
        record = await _one(
            session,
            select(KnowledgeProfile).where(
                KnowledgeProfile.organization_id == org_id,
                KnowledgeProfile.code == code,
            ),
        )
        if record is None:
            record = KnowledgeProfile(
                organization_id=org_id,
                code=code,
                description=description,
                is_active=True,
            )
            session.add(record)
            await session.flush()
            print(f"  Created knowledge profile: {code}")
        else:
            record.description = description
            record.is_active = True
        knowledge_profiles[code] = record

    return {
        "bloom_domains": bloom_domains,
        "bloom_levels": bloom_levels,
        "complex_problems": complex_problems,
        "delivery_methods": delivery_methods,
        "knowledge_profiles": knowledge_profiles,
        "categories": categories,
        "assessment_types": assessment_types,
    }


async def ensure_curriculum(
    session: AsyncSession, org_id: UUID, curriculum_id: UUID | None
) -> Curriculum:
    if curriculum_id:
        curriculum = await _one(
            session,
            select(Curriculum).where(
                Curriculum.id == curriculum_id,
                Curriculum.organization_id == org_id,
            ),
        )
        if curriculum is None:
            raise RuntimeError(f"Curriculum not found for this organization: {curriculum_id}")
        return curriculum

    existing = await _one(
        session,
        select(Curriculum)
        .where(Curriculum.organization_id == org_id, Curriculum.status.in_(["DRAFT", "ACTIVE"]))
        .order_by(Curriculum.created_at)
        .limit(1),
    )
    if existing:
        return existing

    dept = await _one(
        session,
        select(Department).where(
            Department.organization_id == org_id,
            Department.short_name == "CSE",
            Department.status == "ACTIVE",
        ),
    )
    if dept is None:
        dept = Department(
            organization_id=org_id,
            name="Department of Computer Science and Engineering",
            short_name="CSE",
            year_established=2001,
            description="Demo department for computing programs.",
            status="ACTIVE",
        )
        session.add(dept)
        await session.flush()

    program = await _one(
        session,
        select(Program).where(
            Program.organization_id == org_id,
            Program.acronym == "BSCSE",
            Program.status == "ACTIVE",
        ),
    )
    if program is None:
        program = Program(
            organization_id=org_id,
            department_id=dept.id,
            title="Bachelor of Science in Computer Science and Engineering",
            acronym="BSCSE",
            program_type="UNDERGRADUATE",
            minimum_duration_semesters=8,
            total_credits=136,
            study_mode="FULL_TIME",
            description="Demo undergraduate CSE program seeded with complete course outlines.",
            status="ACTIVE",
        )
        session.add(program)
        await session.flush()

    curriculum = Curriculum(
        organization_id=org_id,
        program_id=program.id,
        name="BSc CSE Curriculum 2026",
        code="BSCSE-2026",
        effective_year=2026,
        version_number=1,
        status="DRAFT",
        threshold_co_score_pct=Decimal("50.00"),
        threshold_student_pct=Decimal("50.00"),
    )
    session.add(curriculum)
    await session.flush()
    await session.refresh(curriculum)
    print(f"  Created curriculum: {curriculum.name} ({curriculum.id})")
    return curriculum


async def ensure_terms(session: AsyncSession, curriculum: Curriculum) -> dict[int, CurriculumTermDefinition]:
    existing = (
        await session.execute(
            select(CurriculumTermDefinition).where(
                CurriculumTermDefinition.curriculum_id == curriculum.id
            )
        )
    ).scalars().all()
    terms = {term.term_number: term for term in existing}
    for term_number in range(1, 9):
        if term_number not in terms:
            term = CurriculumTermDefinition(
                curriculum_id=curriculum.id,
                term_number=term_number,
                name=f"Semester {term_number}",
                total_credit_hours=18 if term_number < 8 else 15,
            )
            session.add(term)
            await session.flush()
            terms[term_number] = term
    return terms


async def ensure_program_outcomes(
    session: AsyncSession, org_id: UUID, program_id: UUID, cognitive_domain_id: UUID
) -> list[ProgramOutcome]:
    outcomes: list[ProgramOutcome] = []
    for index, (code, po_type, statement) in enumerate(PO_STATEMENTS, start=1):
        po = await _one(
            session,
            select(ProgramOutcome).where(
                ProgramOutcome.organization_id == org_id,
                ProgramOutcome.code == code,
                ProgramOutcome.status == "ACTIVE",
            ),
        )
        if po is None:
            po = ProgramOutcome(
                organization_id=org_id,
                program_id=program_id,
                bloom_domain_id=cognitive_domain_id,
                code=code,
                reference=po_type,
                statement=statement,
                po_type=po_type,
                order_index=index,
                status="ACTIVE",
            )
            session.add(po)
            await session.flush()
        outcomes.append(po)
    return outcomes


def _objectives(course: dict) -> list[str]:
    return [
        f"Explain the core concepts and terminology of {course['title'].lower()}.",
        f"Apply relevant methods, tools, and notations to solve {course['title'].lower()} problems.",
        f"Analyze design choices, trade-offs, and limitations in {course['title'].lower()} scenarios.",
        f"Develop and communicate a tested solution or artifact aligned with {course['title'].lower()} practice.",
    ]


def _co_statements(course: dict) -> list[tuple[str, str, list[str]]]:
    title = course["title"].lower()
    return [
        ("CO1", f"Describe fundamental principles, vocabulary, and models used in {title}.", ["C1", "C2"]),
        ("CO2", f"Apply standard techniques and tools to solve well-defined {title} tasks.", ["C3"]),
        ("CO3", f"Analyze requirements, constraints, data, or behavior in realistic {title} problems.", ["C4"]),
        ("CO4", f"Design, evaluate, and present a defensible {title} solution or project artifact.", ["C5", "C6"]),
    ]


def _lesson_items(course: dict, co_ids: list[UUID], po_ids: list[UUID]) -> list[dict]:
    topics = course["topics"]
    expanded = topics + topics
    items = []
    for index in range(14):
        topic = expanded[index]
        co_id = co_ids[min(index // 4, len(co_ids) - 1)]
        po_pair = [po_ids[index % len(po_ids)], po_ids[(index + 4) % len(po_ids)]]
        items.append(
            {
                "week_number": index + 1,
                "lesson_label": f"Week {index + 1}",
                "topic": topic,
                "tla": "Lecture, guided discussion, worked examples, lab or tutorial activity, and feedback on formative tasks.",
                "assessment_strategy": "Short quiz, in-class exercise, lab check, assignment milestone, or project review aligned with the weekly CO.",
                "co_ids": [co_id],
                "po_ids": po_pair,
            }
        )
    return items


async def replace_course_details(
    session: AsyncSession,
    course: Course,
    curriculum: Curriculum,
    source: dict,
    refs: dict[str, dict[str, object]],
    terms: dict[int, CurriculumTermDefinition],
    program_outcomes: list[ProgramOutcome],
) -> None:
    await session.execute(delete(CourseObjective).where(CourseObjective.course_id == course.id))
    session.add_all(
        [
            CourseObjective(course_id=course.id, order_index=index, statement=statement)
            for index, statement in enumerate(_objectives(source), start=1)
        ]
    )

    await session.execute(
        delete(CourseLearningMaterial).where(CourseLearningMaterial.course_id == course.id)
    )
    textbook_title, authors, publisher, edition_year = source["textbook"]
    materials = [
        ("TEXTBOOK", textbook_title, authors, publisher, edition_year),
        ("REFERENCE", "Computer Science Illuminated", "Nell Dale and John Lewis", "Jones & Bartlett Learning", "7th Edition, 2019"),
        ("REFERENCE", "IEEE/ACM Computing Curricula and relevant open documentation", "IEEE, ACM, and vendor documentation", "Online", "Current"),
    ]
    session.add_all(
        [
            CourseLearningMaterial(
                course_id=course.id,
                material_type=material_type,
                order_index=index,
                title=title,
                authors=material_authors,
                publisher=material_publisher,
                edition_year=material_year,
            )
            for index, (material_type, title, material_authors, material_publisher, material_year)
            in enumerate(materials, start=1)
        ]
    )

    await session.execute(delete(CourseBloomDomain).where(CourseBloomDomain.course_id == course.id))
    bloom_domains = refs["bloom_domains"]
    selected_domains = ["Cognitive"]
    if source["type"] in {"THEORY_LAB", "LAB", "THESIS_DEFENSE"}:
        selected_domains.append("Psychomotor")
    if source["code"] in {"CSE204", "CSE306", "CSE402"}:
        selected_domains.append("Affective")
    session.add_all(
        [
            CourseBloomDomain(course_id=course.id, bloom_domain_id=bloom_domains[name].id)
            for name in selected_domains
        ]
    )

    slot = await _one(
        session,
        select(CurriculumCourseSlot).where(
            CurriculumCourseSlot.curriculum_id == curriculum.id,
            CurriculumCourseSlot.course_id == course.id,
        ),
    )
    if slot is None:
        slot = CurriculumCourseSlot(
            curriculum_id=curriculum.id,
            curriculum_term_definition_id=terms[source["term"]].id,
            course_id=course.id,
            is_elective=source["category"] == "Elective",
        )
        session.add(slot)
    else:
        slot.curriculum_term_definition_id = terms[source["term"]].id
        slot.is_elective = source["category"] == "Elective"

    existing_cos = (
        await session.execute(
            select(CourseOutcome).where(
                CourseOutcome.curriculum_id == curriculum.id,
                CourseOutcome.course_id == course.id,
            )
        )
    ).scalars().all()
    existing_co_ids = [co.id for co in existing_cos]
    if existing_co_ids:
        await session.execute(
            delete(CourseLessonPlanItemCO).where(
                CourseLessonPlanItemCO.course_outcome_id.in_(existing_co_ids)
            )
        )
        await session.execute(
            delete(COCPMapping).where(COCPMapping.course_outcome_id.in_(existing_co_ids))
        )
        await session.execute(
            delete(COKPMapping).where(COKPMapping.course_outcome_id.in_(existing_co_ids))
        )
        await session.execute(
            delete(COPOMappingEntry).where(COPOMappingEntry.course_outcome_id.in_(existing_co_ids))
        )
        await session.execute(
            delete(CourseCOMarks).where(CourseCOMarks.course_outcome_id.in_(existing_co_ids))
        )
        await session.execute(
            delete(CODeliveryMethod).where(CODeliveryMethod.course_outcome_id.in_(existing_co_ids))
        )
        await session.execute(
            delete(CourseOutcomeBloomLevel).where(
                CourseOutcomeBloomLevel.course_outcome_id.in_(existing_co_ids)
            )
        )
    await session.execute(
        delete(CourseOutcome).where(
            CourseOutcome.curriculum_id == curriculum.id,
            CourseOutcome.course_id == course.id,
        )
    )

    bloom_levels = refs["bloom_levels"]
    delivery_methods = refs["delivery_methods"]
    co_records: list[CourseOutcome] = []
    for code, statement, level_codes in _co_statements(source):
        co = CourseOutcome(
            organization_id=course.organization_id,
            curriculum_id=curriculum.id,
            course_id=course.id,
            code=code,
            statement=statement,
            status="DRAFT",
        )
        session.add(co)
        await session.flush()
        for level_code in level_codes:
            session.add(
                CourseOutcomeBloomLevel(
                    course_outcome_id=co.id,
                    bloom_level_id=bloom_levels[level_code].id,
                )
            )
        method_names = ["Lecture", "Tutorial"]
        if source["type"] in {"THEORY_LAB", "LAB", "THESIS_DEFENSE"}:
            method_names.append("Lab")
        for name in method_names:
            session.add(
                CODeliveryMethod(
                    course_outcome_id=co.id,
                    delivery_method_id=delivery_methods[name].id,
                )
            )
        co_records.append(co)

    complex_problems = refs["complex_problems"]
    knowledge_profiles = refs["knowledge_profiles"]
    cp_plan = [
        ["CEP1", "CEP3"],
        ["CEP1", "CEP7"],
        ["CEP2", "CEP6"],
        ["CEP4", "CEP5"],
    ]
    kp_plan = [
        ["K1", "K4"],
        ["K3", "K6"],
        ["K4", "K5"],
        ["K5", "K8"],
    ]
    for co, cp_codes, kp_codes in zip(co_records, cp_plan, kp_plan, strict=False):
        for cp_code in cp_codes:
            cp = complex_problems[cp_code]
            session.add(
                COCPMapping(
                    organization_id=course.organization_id,
                    course_outcome_id=co.id,
                    complex_problem_id=cp.id,
                    justification=(
                        f"{co.code} addresses {cp_code} by requiring students to handle "
                        f"non-trivial {source['title'].lower()} analysis, constraints, and trade-offs."
                    ),
                    status="DRAFT",
                )
            )
        for kp_code in kp_codes:
            kp = knowledge_profiles[kp_code]
            session.add(
                COKPMapping(
                    organization_id=course.organization_id,
                    course_outcome_id=co.id,
                    knowledge_profile_id=kp.id,
                    justification=(
                        f"{co.code} uses {kp_code} knowledge through assessed "
                        f"{source['title'].lower()} concepts, tools, design work, or reflection."
                    ),
                    status="DRAFT",
                )
            )

    mapping_set = await _one(
        session,
        select(COPOMappingSet).where(
            COPOMappingSet.curriculum_id == curriculum.id,
            COPOMappingSet.course_id == course.id,
        ),
    )
    if mapping_set is None:
        mapping_set = COPOMappingSet(
            organization_id=course.organization_id,
            curriculum_id=curriculum.id,
            course_id=course.id,
            status="DRAFT",
        )
        session.add(mapping_set)
        await session.flush()
    else:
        await session.execute(delete(COPOMappingEntry).where(COPOMappingEntry.mapping_set_id == mapping_set.id))

    for index, co in enumerate(co_records):
        primary_po = program_outcomes[index]
        secondary_po = program_outcomes[(index + 4) % len(program_outcomes)]
        session.add(
            COPOMappingEntry(
                mapping_set_id=mapping_set.id,
                course_outcome_id=co.id,
                program_outcome_id=primary_po.id,
                weight=3,
                justification=f"{co.code} strongly supports {primary_po.code} through assessed {source['title'].lower()} work.",
            )
        )
        session.add(
            COPOMappingEntry(
                mapping_set_id=mapping_set.id,
                course_outcome_id=co.id,
                program_outcome_id=secondary_po.id,
                weight=2,
                justification=f"{co.code} also contributes to {secondary_po.code} through communication, tools, or design practice.",
            )
        )

    assessment_types = refs["assessment_types"]
    locked_tool_names = {"Final Exam", "Lab Final"}
    if source["type"] == "THEORY":
        tool_names = [
            "Mid-term Exam",
            "Final Exam",
            "Attendance",
            "Presentation",
            "Quiz",
            "Assignment",
        ]
        locked_tool_names = {"Mid-term Exam", "Final Exam"}
    else:
        tool_names = ["Assignment", "Quiz", "Mid-term Exam", "Final Exam"]
        if source["type"] in {"THEORY_LAB", "LAB", "THESIS_DEFENSE"}:
            tool_names += ["Lab Report", "Lab Final"]
        if source["type"] == "THESIS_DEFENSE":
            tool_names += ["Project", "Presentation", "Viva"]

    await session.execute(
        delete(CourseAssessmentTool).where(
            CourseAssessmentTool.curriculum_id == curriculum.id,
            CourseAssessmentTool.course_id == course.id,
        )
    )
    session.add_all(
        [
            CourseAssessmentTool(
                curriculum_id=curriculum.id,
                course_id=course.id,
                assessment_type_id=assessment_types[name].id,
                is_locked=name in locked_tool_names,
            )
            for name in tool_names
            if name in assessment_types
        ]
    )

    await session.execute(
        delete(CourseCOMarks).where(
            CourseCOMarks.curriculum_id == curriculum.id,
            CourseCOMarks.course_id == course.id,
        )
    )
    if source["type"] == "THEORY":
        co_mark_plan = [
            ("Mid-term Exam", [5, 5, 10, 5]),
            ("Final Exam", [5, 10, 10, 15]),
            ("Attendance", [2, 2, 2, 1]),
            ("Presentation", [0, 2, 3, 3]),
            ("Quiz", [3, 4, 4, 4]),
            ("Assignment", [1, 1, 1, 2]),
        ]
    else:
        co_mark_plan = [
            ("Assignment", [5, 5, 5, 5]),
            ("Quiz", [3, 3, 2, 2]),
            ("Mid-term Exam", [5, 10, 10, 5]),
            ("Final Exam", [10, 10, 15, 15]),
            ("Lab Report", [5, 5, 5, 5]),
            ("Lab Final", [0, 5, 10, 10]),
            ("Project", [0, 10, 15, 20]),
            ("Presentation", [0, 0, 5, 10]),
            ("Viva", [0, 0, 5, 10]),
        ]
    for tool_name, marks_by_co in co_mark_plan:
        if tool_name not in tool_names or tool_name not in assessment_types:
            continue
        for co, marks in zip(co_records, marks_by_co, strict=False):
            if marks:
                session.add(
                    CourseCOMarks(
                        curriculum_id=curriculum.id,
                        course_id=course.id,
                        assessment_type_id=assessment_types[tool_name].id,
                        course_outcome_id=co.id,
                        marks=Decimal(f"{marks}.00"),
                    )
                )

    await session.execute(
        delete(CourseBloomMarks).where(
            CourseBloomMarks.curriculum_id == curriculum.id,
            CourseBloomMarks.course_id == course.id,
        )
    )
    if source["type"] == "THEORY":
        bloom_mark_plan = [
            ("Mid-term Exam", "CIE", [("C2", 5), ("C3", 10), ("C4", 10)]),
            ("Final Exam", "SEE", [("C2", 5), ("C3", 15), ("C4", 15), ("C5", 5)]),
            ("Attendance", "CIE", [("C1", 3), ("C2", 4)]),
            ("Presentation", "CIE", [("C3", 2), ("C4", 3), ("C5", 3)]),
            ("Quiz", "CIE", [("C1", 5), ("C2", 5), ("C3", 5)]),
            ("Assignment", "CIE", [("C3", 2), ("C4", 3)]),
        ]
    else:
        bloom_mark_plan = [
            ("Assignment", "CIE", [("C2", 5), ("C3", 10), ("C4", 5)]),
            ("Quiz", "CIE", [("C1", 4), ("C2", 4), ("C3", 2)]),
            ("Mid-term Exam", "CIE", [("C2", 5), ("C3", 10), ("C4", 15)]),
            ("Final Exam", "SEE", [("C2", 10), ("C3", 15), ("C4", 15), ("C5", 10)]),
            ("Lab Report", "CIE", [("C3", 10), ("C4", 10)]),
            ("Lab Final", "SEE", [("C3", 10), ("C4", 10), ("C5", 5)]),
            ("Project", "CIE", [("C4", 15), ("C5", 15), ("C6", 15)]),
            ("Presentation", "CIE", [("C5", 5), ("C6", 10)]),
            ("Viva", "SEE", [("C4", 5), ("C5", 10), ("C6", 10)]),
        ]
    for tool_name, component, level_marks in bloom_mark_plan:
        if tool_name not in tool_names or tool_name not in assessment_types:
            continue
        for level_code, marks in level_marks:
            session.add(
                CourseBloomMarks(
                    curriculum_id=curriculum.id,
                    course_id=course.id,
                    assessment_type_id=assessment_types[tool_name].id,
                    bloom_level_id=bloom_levels[level_code].id,
                    component=component,
                    marks=Decimal(f"{marks}.00"),
                )
            )

    lesson_items = (
        await session.execute(
            select(CourseLessonPlanItem.id).where(
                CourseLessonPlanItem.curriculum_id == curriculum.id,
                CourseLessonPlanItem.course_id == course.id,
            )
        )
    ).all()
    lesson_item_ids = [row[0] for row in lesson_items]
    if lesson_item_ids:
        await session.execute(
            delete(CourseLessonPlanItemCO).where(CourseLessonPlanItemCO.item_id.in_(lesson_item_ids))
        )
        await session.execute(
            delete(CourseLessonPlanItemPO).where(CourseLessonPlanItemPO.item_id.in_(lesson_item_ids))
        )
    await session.execute(
        delete(CourseLessonPlanItem).where(
            CourseLessonPlanItem.curriculum_id == curriculum.id,
            CourseLessonPlanItem.course_id == course.id,
        )
    )
    co_ids = [co.id for co in co_records]
    po_ids = [po.id for po in program_outcomes]
    for order_index, item in enumerate(_lesson_items(source, co_ids, po_ids), start=1):
        co_link_ids = item.pop("co_ids")
        po_link_ids = item.pop("po_ids")
        lesson = CourseLessonPlanItem(
            curriculum_id=curriculum.id,
            course_id=course.id,
            order_index=order_index,
            **item,
        )
        session.add(lesson)
        await session.flush()
        session.add_all(
            [
                CourseLessonPlanItemCO(item_id=lesson.id, course_outcome_id=co_id)
                for co_id in co_link_ids
            ]
        )
        session.add_all(
            [
                CourseLessonPlanItemPO(item_id=lesson.id, program_outcome_id=po_id)
                for po_id in po_link_ids
            ]
        )


async def seed_courses(org_id: UUID | None = None, curriculum_id: UUID | None = None) -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        org = await resolve_org(session, org_id)
        await session.commit()

    async with session_factory() as session:
        refs = await ensure_reference_maps(session, org.id)
        curriculum = await ensure_curriculum(session, org.id, curriculum_id)
        terms = await ensure_terms(session, curriculum)
        program_outcomes = await ensure_program_outcomes(
            session,
            org.id,
            curriculum.program_id,
            refs["bloom_domains"]["Cognitive"].id,
        )

        courses_by_code: dict[str, Course] = {}
        for source in COURSES:
            category = refs["categories"][source["category"]]
            syllabus = "\n".join(f"{index}. {topic}" for index, topic in enumerate(source["topics"], start=1))
            course = await _one(
                session,
                select(Course).where(
                    Course.organization_id == org.id,
                    Course.code == source["code"],
                    Course.status == "ACTIVE",
                ),
            )
            if course is None:
                course = Course(
                    organization_id=org.id,
                    course_category_id=category.id,
                    course_type=source["type"],
                    code=source["code"],
                    title=source["title"],
                    credits=source["credits"],
                    theory_hours=source["theory_hours"],
                    lab_hours=source["lab_hours"],
                    description=source["description"],
                    syllabus_content=syllabus,
                    status="ACTIVE",
                )
                session.add(course)
                await session.flush()
                print(f"  Created course: {source['code']} - {source['title']}")
            else:
                course.course_category_id = category.id
                course.course_type = source["type"]
                course.title = source["title"]
                course.credits = source["credits"]
                course.theory_hours = source["theory_hours"]
                course.lab_hours = source["lab_hours"]
                course.description = source["description"]
                course.syllabus_content = syllabus
                print(f"  Updated course: {source['code']} - {source['title']}")
            courses_by_code[source["code"]] = course
            await replace_course_details(
                session,
                course,
                curriculum,
                source,
                refs,
                terms,
                program_outcomes,
            )

        prereq_pairs = [
            ("CSE104", "CSE101"),
            ("CSE105", "CSE101"),
            ("CSE201", "CSE104"),
            ("CSE202", "CSE104"),
            ("CSE203", "CSE106"),
            ("CSE301", "CSE202"),
            ("CSE302", "CSE201"),
            ("CSE303", "CSE206"),
            ("CSE304", "CSE201"),
            ("CSE305", "CSE205"),
            ("CSE401", "CSE203"),
            ("CSE402", "CSE204"),
        ]
        for course_code, prereq_code in prereq_pairs:
            course = courses_by_code[course_code]
            prereq = courses_by_code[prereq_code]
            existing = await _one(
                session,
                select(CoursePrerequisite).where(
                    CoursePrerequisite.course_id == course.id,
                    CoursePrerequisite.prerequisite_course_id == prereq.id,
                ),
            )
            if existing is None:
                session.add(
                    CoursePrerequisite(
                        organization_id=org.id,
                        course_id=course.id,
                        prerequisite_course_id=prereq.id,
                    )
                )

        await session.commit()
        print("\nDemo courses seeded successfully.")
        print(f"Organization: {org.name} ({org.id})")
        print(f"Curriculum: {curriculum.name} ({curriculum.id})")
        print(f"Courses: {len(COURSES)}")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed 20 fully detailed demo CSE courses")
    parser.add_argument("--org-id", default=None, help="Organization UUID")
    parser.add_argument("--curriculum-id", default=None, help="Curriculum UUID")
    args = parser.parse_args()

    asyncio.run(
        seed_courses(
            UUID(args.org_id) if args.org_id else None,
            UUID(args.curriculum_id) if args.curriculum_id else None,
        )
    )
