"""
Run: python -m scripts.seed_reference_data --org-id <uuid>

Seeds default reference data for an organization:
  - Bloom Cognitive, Affective, and Psychomotor domains with their levels
  - Delivery methods (Lecture, Lab, Tutorial, Online, Hybrid)
  - Course types (Core, Elective, Lab, Project, Thesis)
  - Assessment types (Quiz, Assignment, Mid-term, Final, Lab Report, Project)
  - Mapping weight labels (1=Low, 2=Medium, 3=High)

Safe to re-run: skips records that already exist.
"""
import asyncio
import os
import sys
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.modules.ref_data.models import (
    AssessmentType,
    BloomDomain,
    BloomLevel,
    CourseCategory,
    DeliveryMethod,
    MappingWeightLabel,
)

_BLOOM_DOMAINS = [
    (
        "Cognitive",
        "Bloom's Taxonomy Cognitive Domain",
        [
            ("C1", "Remember", 1),
            ("C2", "Understand", 2),
            ("C3", "Apply", 3),
            ("C4", "Analyze", 4),
            ("C5", "Evaluate", 5),
            ("C6", "Create", 6),
        ],
    ),
    (
        "Affective",
        "Bloom's Taxonomy Affective Domain",
        [
            ("A1", "Receiving", 1),
            ("A2", "Responding", 2),
            ("A3", "Valuing", 3),
            ("A4", "Organizing", 4),
            ("A5", "Characterizing", 5),
        ],
    ),
    (
        "Psychomotor",
        "Bloom's Taxonomy Psychomotor Domain",
        [
            ("P1", "Imitation", 1),
            ("P2", "Manipulation", 2),
            ("P3", "Precision", 3),
            ("P4", "Articulation", 4),
            ("P5", "Naturalization", 5),
        ],
    ),
]

_DELIVERY_METHODS = [
    ("Lecture", "Traditional instructor-led lecture"),
    ("Lab", "Hands-on laboratory session"),
    ("Tutorial", "Small-group tutorial session"),
    ("Online", "Fully online delivery"),
    ("Hybrid", "Mix of online and in-person delivery"),
]

_COURSE_CATEGORIES = [
    ("Core", "Mandatory core course"),
    ("Elective", "Student-chosen elective course"),
    ("Lab", "Laboratory-based course"),
    ("Project", "Project-based course"),
    ("Thesis", "Thesis or dissertation"),
]

_ASSESSMENT_TYPES = [
    ("Quiz", False),
    ("Assignment", False),
    ("Mid-term Exam", False),
    ("Final Exam", False),
    ("Lab Report", True),
    ("Lab Final", True),
    ("Project", False),
    ("Presentation", False),
    ("Viva", False),
]

_MAPPING_WEIGHTS = [
    (1, "Low"),
    (2, "Medium"),
    (3, "High"),
]


async def seed(org_id: UUID) -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        # Bloom domains
        for domain_name, domain_desc, levels in _BLOOM_DOMAINS:
            result = await session.execute(
                select(BloomDomain).where(BloomDomain.organization_id == org_id, BloomDomain.name == domain_name)
            )
            domain = result.scalar_one_or_none()
            if domain is None:
                domain = BloomDomain(organization_id=org_id, name=domain_name, description=domain_desc)
                session.add(domain)
                await session.flush()
                print(f"  Created Bloom domain: {domain_name} ({domain.id})")
            else:
                print(f"  Bloom domain already exists: {domain_name} ({domain.id})")

            for code, name, order in levels:
                r = await session.execute(
                    select(BloomLevel).where(
                        BloomLevel.organization_id == org_id,
                        BloomLevel.bloom_domain_id == domain.id,
                        BloomLevel.code == code,
                    )
                )
                if r.scalar_one_or_none() is None:
                    session.add(BloomLevel(organization_id=org_id, bloom_domain_id=domain.id,
                                           code=code, name=name, order_index=order))
                    print(f"    Created Bloom level: {code} - {name}")

        # Delivery methods
        for name, desc in _DELIVERY_METHODS:
            r = await session.execute(
                select(DeliveryMethod).where(DeliveryMethod.organization_id == org_id, DeliveryMethod.name == name)
            )
            if r.scalar_one_or_none() is None:
                session.add(DeliveryMethod(organization_id=org_id, name=name, description=desc))
                print(f"  Created delivery method: {name}")

        # Course categories
        for name, desc in _COURSE_CATEGORIES:
            r = await session.execute(
                select(CourseCategory).where(CourseCategory.organization_id == org_id, CourseCategory.name == name)
            )
            if r.scalar_one_or_none() is None:
                session.add(CourseCategory(organization_id=org_id, name=name, description=desc))
                print(f"  Created course category: {name}")

        # Assessment types
        for name, is_sessional in _ASSESSMENT_TYPES:
            r = await session.execute(
                select(AssessmentType).where(AssessmentType.organization_id == org_id, AssessmentType.name == name)
            )
            if r.scalar_one_or_none() is None:
                session.add(AssessmentType(organization_id=org_id, name=name, is_sessional=is_sessional))
                print(f"  Created assessment type: {name}")

        # Mapping weight labels
        for value, label in _MAPPING_WEIGHTS:
            r = await session.execute(
                select(MappingWeightLabel).where(
                    MappingWeightLabel.organization_id == org_id,
                    MappingWeightLabel.weight_value == value,
                )
            )
            if r.scalar_one_or_none() is None:
                session.add(MappingWeightLabel(organization_id=org_id, weight_value=value, label=label))
                print(f"  Created mapping weight: {value} = {label}")

        await session.commit()
        print("\nReference data seeded successfully.")

    await engine.dispose()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed default reference data for an organization")
    parser.add_argument("--org-id", required=True, help="Organization UUID")
    args = parser.parse_args()

    asyncio.run(seed(UUID(args.org_id)))
