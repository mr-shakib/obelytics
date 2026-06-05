import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import Base

# ── Import all models here so Alembic autogenerate can detect them ──
from app.shared.events.outbox import OutboxEvent  # noqa: F401
from app.modules.iam.models import (  # noqa: F401
    User, PasswordCredential, RefreshToken, Role, Permission, RolePermission, UserRoleAssignment
)
from app.modules.org.models import Organization, Department, DepartmentHeadHistory, Program  # noqa: F401
from app.modules.ref_data.models import (  # noqa: F401
    BloomDomain, BloomLevel, DeliveryMethod, CourseType, AssessmentType,
    ComplexProblem, ComplexActivity, KnowledgeProfile, MappingWeightLabel,
)
from app.modules.curriculum.models import (  # noqa: F401
    Curriculum, CurriculumTermDefinition, Course, CurriculumCourseSlot,
    CoursePrerequisite, Batch, AcademicTerm, Section, SectionOffering, FacultyAssignment,
)
from app.modules.obe.models import (  # noqa: F401
    ProgramOutcome, POKnowledgeProfile, CourseOutcome, CODeliveryMethod,
    COPOMappingSet, COPOMappingEntry, COCPMapping, COCAMapping, COKPMapping,
)
from app.modules.assessment.models import (  # noqa: F401
    Student, StudentEnrollment, Assessment, AssessmentCOWeight, StudentMark, ResultPublication,
)
from app.modules.attainment.models import AttainmentConfig, COAttainmentResult, POAttainmentResult  # noqa: F401
from app.modules.approval.models import ReviewComment  # noqa: F401
from app.modules.audit.models import AuditLog  # noqa: F401
from app.modules.notification.models import Notification  # noqa: F401
# Phase 9: from app.modules.accreditation.models import *  # noqa: F401
# Phase 9: from app.modules.reporting.models import *  # noqa: F401

alembic_config = context.config
alembic_config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = alembic_config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
