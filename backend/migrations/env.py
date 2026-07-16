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
from app.modules.accreditation.models import (  # noqa: F401
    AccreditationCriterion,
    AccreditationCycle,
    CriterionPOMapping,
)
from app.modules.approval.models import ReviewComment  # noqa: F401
from app.modules.assessment.models import (  # noqa: F401
    Assessment,
    AssessmentCOWeight,
    ResultPublication,
    Student,
    StudentEnrollment,
    StudentMark,
)
from app.modules.attainment.models import (  # noqa: F401
    AttainmentConfig,
    COAttainmentResult,
    POAttainmentResult,
)
from app.modules.audit.models import AuditLog  # noqa: F401
from app.modules.copilot.models import CopilotConversation, CopilotMessage  # noqa: F401
from app.modules.curriculum.models import (  # noqa: F401
    AcademicTerm,
    Batch,
    Course,
    CourseBloomDomain,
    CoursePrerequisite,
    Curriculum,
    CurriculumCourseSlot,
    CurriculumTermDefinition,
    FacultyAssignment,
    Section,
    SectionOffering,
)
from app.modules.iam.models import (  # noqa: F401
    PasswordCredential,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserRoleAssignment,
)
from app.modules.notification.models import Notification  # noqa: F401
from app.modules.obe.models import (  # noqa: F401
    COCAMapping,
    COCPMapping,
    CODeliveryMethod,
    COKPMapping,
    COPOMappingEntry,
    COPOMappingSet,
    CourseOutcome,
    POKnowledgeProfile,
    ProgramOutcome,
)
from app.modules.org.models import (  # noqa: F401
    Department,
    DepartmentHeadHistory,
    Organization,
    Program,
)
from app.modules.ref_data.models import (  # noqa: F401
    AssessmentType,
    BloomDomain,
    BloomLevel,
    ComplexActivity,
    ComplexProblem,
    CourseCategory,
    DeliveryMethod,
    KnowledgeProfile,
    MappingWeightLabel,
)

# ── Import all models here so Alembic autogenerate can detect them ──
from app.shared.events.outbox import OutboxEvent  # noqa: F401

# Reporting has no models (pure query module)

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
