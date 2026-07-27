"""
Run: python -m scripts.seed_superadmin [options]

Creates the organization record, system permissions, system roles, and the
first Super Admin user.  Safe to re-run — skips records that already exist.
"""
import asyncio
import os
import sys
from uuid import UUID, uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.modules.iam.models import (
    PasswordCredential,
    Permission,
    Role,
    RolePermission,
    User,
    UserRoleAssignment,
)
from app.modules.iam.seed_data import ALL_PERMISSIONS, ROLES
from app.modules.org.models import Organization


async def seed(
    admin_email: str = "admin@obelytics.local",
    admin_password: str = "Admin@123",
    org_id: UUID | None = None,
    org_name: str = "My University",
    org_short_name: str = "UNIV",
    admin_employee_id: str = "ADMIN001",
) -> None:
    if org_id is None:
        org_id = uuid4()
        print(f"[i] Generated organization_id: {org_id}")
        print(f"    Use --org-id {org_id} on subsequent runs to keep it stable.\n")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        # ── Organization ──────────────────────────────────────────────────────
        result = await session.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()
        if org is None:
            result = await session.execute(
                select(Organization).where(Organization.short_name == org_short_name)
            )
            org = result.scalar_one_or_none()
        if org is None:
            org = Organization(id=org_id, name=org_name, short_name=org_short_name)
            session.add(org)
            await session.flush()
            print(f"[+] Organization created: {org_name} ({org_short_name})")
        else:
            print(f"[=] Organization already exists: {org.name}")

        # ── Permissions ───────────────────────────────────────────────────────
        perm_map: dict[str, Permission] = {}
        for pdef in ALL_PERMISSIONS:
            result = await session.execute(
                select(Permission).where(Permission.code == pdef["code"])
            )
            perm = result.scalar_one_or_none()
            if perm is None:
                perm = Permission(
                    code=pdef["code"],
                    description=pdef["description"],
                    module=pdef["module"],
                    tier="SYSTEM",
                )
                session.add(perm)
                await session.flush()
            perm_map[perm.code] = perm
        print(f"[ok] {len(perm_map)} permissions ready")

        # ── Roles ─────────────────────────────────────────────────────────────
        role_map: dict[str, Role] = {}
        for rdef in ROLES:
            result = await session.execute(
                select(Role).where(
                    Role.name == rdef["name"],
                    Role.organization_id == org_id,
                )
            )
            role = result.scalar_one_or_none()
            if role is None:
                role = Role(
                    organization_id=org_id,
                    name=rdef["name"],
                    description=rdef["description"],
                    is_system_role=True,
                )
                session.add(role)
                await session.flush()
                existing_codes: set[str] = set()
            else:
                result = await session.execute(
                    select(Permission.code)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .where(RolePermission.role_id == role.id)
                )
                existing_codes = set(result.scalars().all())

            added = 0
            for pcode in rdef["permissions"]:
                if pcode in perm_map and pcode not in existing_codes:
                    session.add(
                        RolePermission(role_id=role.id, permission_id=perm_map[pcode].id)
                    )
                    added += 1
            if added:
                await session.flush()
                print(f"[+] {role.name}: added {added} missing permission(s)")
            role_map[role.name] = role
        print(f"[ok] {len(role_map)} roles ready")

        # ── Super Admin user ─────────────────────────────────────────────────
        result = await session.execute(
            select(User).where(User.email == admin_email.lower())
        )
        admin = result.scalar_one_or_none()
        if admin is None:
            admin = User(
                organization_id=org_id,
                email=admin_email.lower(),
                full_name="Super Admin",
                employee_id=admin_employee_id,
                status="ACTIVE",
            )
            session.add(admin)
            await session.flush()

            session.add(
                PasswordCredential(
                    user_id=admin.id,
                    hashed_password=hash_password(admin_password),
                    must_change_password=False,
                )
            )
            session.add(
                UserRoleAssignment(
                    user_id=admin.id,
                    role_id=role_map["Super Admin"].id,
                    scope_type="GLOBAL",
                    scope_id=None,
                    assigned_by=admin.id,
                )
            )
            print(f"[+] Super Admin created: {admin_email}")
        else:
            print(f"[=] Super Admin already exists: {admin_email}")

        await session.commit()
        print("[ok] Seed complete")

    await engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed Obelytics super admin")
    parser.add_argument("--email",          default="admin@obelytics.local")
    parser.add_argument("--password",       default="Admin@123")
    parser.add_argument("--org-id",         default=None, help="UUID of the organization")
    parser.add_argument("--org-name",       default="My University", help="Organization display name")
    parser.add_argument("--org-short-name", default="UNIV", help="Organization acronym/short name")
    parser.add_argument("--employee-id",    default="ADMIN001", help="Employee ID for the admin (NOT NULL since 0034)")
    args = parser.parse_args()

    org_id = UUID(args.org_id) if args.org_id else None
    asyncio.run(
        seed(
            args.email,
            args.password,
            org_id,
            args.org_name,
            args.org_short_name,
            args.employee_id,
        )
    )
