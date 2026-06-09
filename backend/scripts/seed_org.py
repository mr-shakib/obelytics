"""
Run: python -m scripts.seed_org --org-id <UUID> [options]

Creates (or updates) the organization record for an existing installation
where users already have an organization_id in their JWTs but the org row
was never inserted into org.organizations.

Required:
  --org-id   The UUID that is already embedded in user JWTs (check the 'org'
             claim in any existing access token, or query: SELECT organization_id
             FROM iam.users LIMIT 1;)

Optional:
  --name       Display name  (default: "My University")
  --short-name Acronym       (default: "UNIV")
"""
import argparse
import asyncio
import os
import sys
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.modules.org.models import Organization


async def seed_org(org_id: UUID, name: str, short_name: str) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        result = await session.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()

        if org is None:
            org = Organization(id=org_id, name=name, short_name=short_name)
            session.add(org)
            await session.commit()
            print(f"[+] Organization created: {name} ({short_name})  id={org_id}")
        else:
            print(f"[=] Organization already exists: {org.name} ({org.short_name})  id={org_id}")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed / register the organization record")
    parser.add_argument("--org-id",    required=True, help="UUID already in user JWTs")
    parser.add_argument("--name",       default="My University", help="Organization display name")
    parser.add_argument("--short-name", default="UNIV",          help="Organization acronym")
    args = parser.parse_args()

    asyncio.run(seed_org(UUID(args.org_id), args.name, args.short_name))
