"""
Verifies at most one active Program Coordinator can hold PROGRAM scope for a
given program, regardless of whether the assignment goes through the generic
role-assignment endpoint or the dedicated "assign coordinator" flow.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.iam.models import PasswordCredential, Role, User, UserRoleAssignment
from app.modules.iam.service.user_service import UserService
from app.modules.org.models import Department, Program
from tests.conftest import TEST_ADMIN_EMAIL, TEST_ORG_ID


async def _make_program(db_session: AsyncSession) -> Program:
    dept = Department(organization_id=TEST_ORG_ID, name="Dept X", short_name="DX")
    db_session.add(dept)
    await db_session.flush()

    program = Program(
        organization_id=TEST_ORG_ID,
        department_id=dept.id,
        title="Test Program",
        acronym="TP",
        program_type="UNDERGRADUATE",
        minimum_duration_semesters=8,
        total_credits=140,
        study_mode="FULL_TIME",
    )
    db_session.add(program)
    await db_session.flush()
    return program


async def _make_user(db_session: AsyncSession, email: str) -> User:
    user = User(
        organization_id=TEST_ORG_ID, email=email, full_name=email,
        employee_id=email.split("@")[0].upper(), status="ACTIVE",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(PasswordCredential(
        user_id=user.id, hashed_password=hash_password("x"), must_change_password=False,
    ))
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_assigning_second_coordinator_revokes_the_first(db_session: AsyncSession):
    admin_result = await db_session.execute(select(User).where(User.email == TEST_ADMIN_EMAIL))
    admin = admin_result.scalar_one()

    pc_role_result = await db_session.execute(
        select(Role).where(Role.organization_id == TEST_ORG_ID, Role.name == "Program Coordinator")
    )
    pc_role = pc_role_result.scalar_one()

    program = await _make_program(db_session)
    user_a = await _make_user(db_session, "pc-a@test.local")
    user_b = await _make_user(db_session, "pc-b@test.local")
    await db_session.commit()

    svc = UserService(db_session)

    # First coordinator assigned via the generic role-assignment path.
    await svc.assign_role(user_a.id, pc_role.id, "PROGRAM", program.id, admin.id)

    a_assignment = (await db_session.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_a.id,
            UserRoleAssignment.role_id == pc_role.id,
            UserRoleAssignment.scope_id == program.id,
        )
    )).scalar_one()
    assert a_assignment.removed_at is None

    # Second coordinator assigned for the SAME program, via the same generic path
    # (i.e. NOT through ProgramService.assign_coordinator) — this is exactly the
    # gap: an admin could otherwise create two simultaneous PC holders.
    await svc.assign_role(user_b.id, pc_role.id, "PROGRAM", program.id, admin.id)

    await db_session.refresh(a_assignment)
    b_assignment = (await db_session.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_b.id,
            UserRoleAssignment.role_id == pc_role.id,
            UserRoleAssignment.scope_id == program.id,
        )
    )).scalar_one()

    assert a_assignment.removed_at is not None, "first coordinator's PC assignment must be revoked"
    assert b_assignment.removed_at is None, "second coordinator's PC assignment must be active"

    # At most one ACTIVE Program Coordinator assignment should remain for this program.
    active_count = (await db_session.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.role_id == pc_role.id,
            UserRoleAssignment.scope_id == program.id,
            UserRoleAssignment.removed_at.is_(None),
        )
    )).scalars().all()
    assert len(active_count) == 1
