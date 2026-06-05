"""
Test infrastructure for Obelytics.

Each async fixture creates its own SQLAlchemy engine so there is no
cross-event-loop sharing of asyncpg connection pools (which would cause
"Future attached to a different loop" errors on Python 3.14).

Fixture scope:
  setup_test_database — session-scoped: creates schemas/tables once, seeds
                         permanent fixtures, tears down after the run.
  db_session          — function-scoped: fresh engine + session per test.
  client              — function-scoped: HTTPX client wired to db_session.
  auth_headers        — function-scoped: Bearer token for Super Admin.
  teacher_auth_headers — function-scoped: Bearer token for Section Teacher.
  ml_auth_headers     — function-scoped: Bearer token for Module Leader.
"""
import inspect
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app

# ── Import every model so Base.metadata is fully populated before create_all ─
from app.shared.events.outbox import OutboxEvent  # noqa: F401
from app.modules.iam.models import (  # noqa: F401
    PasswordCredential, Permission, Role, RolePermission, User, UserRoleAssignment,
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
from app.modules.iam.seed_data import ALL_PERMISSIONS, ROLES

# ─────────────────────────────────────────────────────────────────────────────

_db_base, _ = settings.DATABASE_URL.rsplit("/", 1)
TEST_DATABASE_URL = f"{_db_base}/{settings.POSTGRES_DB}_test"

TEST_ORG_ID           = UUID("10000000-0000-0000-0000-000000000001")
TEST_ADMIN_EMAIL      = "test_admin@obelytics-test.com"
TEST_ADMIN_PASSWORD   = "TestAdmin@123"
TEST_TEACHER_EMAIL    = "test_teacher@obelytics-test.com"
TEST_TEACHER_PASSWORD = "TestTeacher@123"
TEST_ML_EMAIL         = "test_ml@obelytics-test.com"
TEST_ML_PASSWORD      = "TestML@123"

_SCHEMAS = [
    "events", "iam", "org", "config", "curriculum", "obe",
    "assessment", "attainment", "approval", "notification",
    "audit", "accreditation", "reporting",
]


def _make_engine():
    """NullPool: no connection pooling, prevents asyncpg cross-loop issues on Python 3.14."""
    return create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Force all async tests to use the session-scoped event loop.

    pytest-asyncio 0.24.x defaults to per-test (function-scoped) loops for tests,
    even when asyncio_default_fixture_loop_scope = "session" is set for fixtures.
    This mismatch means session-scoped fixtures (setup_test_database, Redis client)
    are bound to the session loop, while tests run on short-lived per-test loops —
    causing "Event loop is closed" errors during fixture teardown.
    """
    session_marker = pytest.mark.asyncio(loop_scope="session")
    for item in items:
        if inspect.iscoroutinefunction(getattr(item, "function", None)):
            item.add_marker(session_marker, append=False)


# ── Session-scoped DB lifecycle ───────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    engine = _make_engine()

    # Always start clean: drop any schemas left over from a previous crashed run,
    # then recreate. This prevents DDL lock contention from zombie sessions.
    async with engine.begin() as conn:
        for schema in reversed(_SCHEMAS):
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        for schema in _SCHEMAS:
            await conn.execute(text(f"CREATE SCHEMA {schema}"))
        await conn.run_sync(Base.metadata.create_all)

    # Seed permanent test data
    Session = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with Session() as session:
        await _seed_db(session)

    # Dispose before yielding — per-test fixtures create their own engines
    await engine.dispose()

    yield

    # Teardown
    engine2 = _make_engine()
    async with engine2.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        for schema in reversed(_SCHEMAS):
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
    await engine2.dispose()


async def _seed_db(session: AsyncSession) -> None:
    # DB is always empty at this point (schemas dropped+recreated above)

    # Organization record — id matches TEST_ORG_ID used by all seeded users
    org = Organization(
        id=TEST_ORG_ID,
        name="Test University",
        short_name="TU",
        status="ACTIVE",
    )
    session.add(org)
    await session.flush()

    perm_map: dict[str, Permission] = {}
    for pdef in ALL_PERMISSIONS:
        perm = Permission(
            code=pdef["code"], description=pdef["description"],
            module=pdef["module"], tier="SYSTEM",
        )
        session.add(perm)
        await session.flush()
        perm_map[pdef["code"]] = perm

    role_map: dict[str, Role] = {}
    for rdef in ROLES:
        role = Role(
            organization_id=TEST_ORG_ID, name=rdef["name"],
            description=rdef["description"], is_system_role=True,
        )
        session.add(role)
        await session.flush()
        for pcode in rdef["permissions"]:
            if pcode in perm_map:
                session.add(RolePermission(role_id=role.id, permission_id=perm_map[pcode].id))
        await session.flush()
        role_map[role.name] = role

    admin = User(organization_id=TEST_ORG_ID, email=TEST_ADMIN_EMAIL,
                 full_name="Test Admin", status="ACTIVE")
    session.add(admin)
    await session.flush()
    session.add(PasswordCredential(user_id=admin.id,
        hashed_password=hash_password(TEST_ADMIN_PASSWORD), must_change_password=False))
    session.add(UserRoleAssignment(user_id=admin.id, role_id=role_map["Super Admin"].id,
        scope_type="GLOBAL", assigned_by=admin.id))

    teacher = User(organization_id=TEST_ORG_ID, email=TEST_TEACHER_EMAIL,
                   full_name="Test Teacher", status="ACTIVE")
    session.add(teacher)
    await session.flush()
    session.add(PasswordCredential(user_id=teacher.id,
        hashed_password=hash_password(TEST_TEACHER_PASSWORD), must_change_password=False))
    session.add(UserRoleAssignment(user_id=teacher.id, role_id=role_map["Section Teacher"].id,
        scope_type="PROGRAM", scope_id=None, assigned_by=admin.id))

    ml = User(organization_id=TEST_ORG_ID, email=TEST_ML_EMAIL,
              full_name="Test ML", status="ACTIVE")
    session.add(ml)
    await session.flush()
    session.add(PasswordCredential(user_id=ml.id,
        hashed_password=hash_password(TEST_ML_PASSWORD), must_change_password=False))
    session.add(UserRoleAssignment(user_id=ml.id, role_id=role_map["Module Leader"].id,
        scope_type="PROGRAM", scope_id=None, assigned_by=admin.id))

    await session.commit()


# ── Per-test fixtures — each creates its own engine ──────────────────────────

@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = _make_engine()
    Session = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def teacher_auth_headers(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_TEACHER_EMAIL, "password": TEST_TEACHER_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def ml_auth_headers(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ML_EMAIL, "password": TEST_ML_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
