"""
Unit tests for PermissionManifestBuilder.

Verifies that the manifest is built correctly from role assignments and that
Redis caching works (cache hit returns the same manifest without hitting DB).
"""
import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis
from app.modules.iam.models import User
from app.modules.iam.service.permission_service import PermissionManifestBuilder
from tests.conftest import TEST_ADMIN_EMAIL, TEST_ML_EMAIL, TEST_TEACHER_EMAIL


@pytest.mark.asyncio
async def test_super_admin_manifest_has_all_permissions(db_session: AsyncSession):
    result = await db_session.execute(
        select(User).where(User.email == TEST_ADMIN_EMAIL)
    )
    admin = result.scalar_one()

    builder = PermissionManifestBuilder(db_session)
    manifest = await builder.build_manifest(admin.id)

    assert manifest.is_super_admin is True
    assert len(manifest.permissions) > 0
    # Super admin must have every permission in seed_data
    from app.modules.iam.seed_data import ALL_PERMISSIONS
    seeded_codes = {p["code"] for p in ALL_PERMISSIONS}
    assert seeded_codes.issubset(set(manifest.permissions))


@pytest.mark.asyncio
async def test_teacher_manifest_has_only_teacher_permissions(db_session: AsyncSession):
    result = await db_session.execute(
        select(User).where(User.email == TEST_TEACHER_EMAIL)
    )
    teacher = result.scalar_one()

    builder = PermissionManifestBuilder(db_session)
    manifest = await builder.build_manifest(teacher.id)

    assert manifest.is_super_admin is False
    assert "co.create" in manifest.permissions
    assert "co.submit" in manifest.permissions
    assert "marks.enter" in manifest.permissions
    # Teacher must NOT have admin-only permissions
    assert "system.audit.read" not in manifest.permissions
    assert "attainment.publish" not in manifest.permissions
    assert "co.publish" not in manifest.permissions


@pytest.mark.asyncio
async def test_ml_manifest_has_only_ml_permissions(db_session: AsyncSession):
    result = await db_session.execute(
        select(User).where(User.email == TEST_ML_EMAIL)
    )
    ml = result.scalar_one()

    builder = PermissionManifestBuilder(db_session)
    manifest = await builder.build_manifest(ml.id)

    assert manifest.is_super_admin is False
    assert "co.approve" in manifest.permissions
    assert "result.approve.ml" in manifest.permissions
    # ML must NOT have PC/admin permissions
    assert "co.publish" not in manifest.permissions
    assert "attainment.initiate" not in manifest.permissions
    assert "user.create" not in manifest.permissions
    assert "program.read" in manifest.permissions


@pytest.mark.asyncio
async def test_manifest_is_cached_in_redis(db_session: AsyncSession):
    result = await db_session.execute(
        select(User).where(User.email == TEST_ADMIN_EMAIL)
    )
    admin = result.scalar_one()

    # Clear cache first
    redis = await get_redis()
    await redis.delete(f"auth:{admin.id}:manifest")

    builder = PermissionManifestBuilder(db_session)

    # First call — populates cache
    manifest1 = await builder.build_manifest(admin.id)

    # Verify key is in Redis
    cached = await redis.get(f"auth:{admin.id}:manifest")
    assert cached is not None
    cached_data = json.loads(cached)
    assert cached_data["is_super_admin"] is True

    # Second call — should return cached manifest
    manifest2 = await builder.build_manifest(admin.id)
    assert manifest2.permissions == manifest1.permissions
    assert manifest2.is_super_admin == manifest1.is_super_admin


@pytest.mark.asyncio
async def test_manifest_invalidation_clears_cache(db_session: AsyncSession):
    result = await db_session.execute(
        select(User).where(User.email == TEST_ADMIN_EMAIL)
    )
    admin = result.scalar_one()

    redis = await get_redis()
    await redis.delete(f"auth:{admin.id}:manifest")

    builder = PermissionManifestBuilder(db_session)
    await builder.build_manifest(admin.id)

    # Confirm cached
    assert await redis.get(f"auth:{admin.id}:manifest") is not None

    # Invalidate
    await builder.invalidate(admin.id)
    assert await redis.get(f"auth:{admin.id}:manifest") is None


@pytest.mark.asyncio
async def test_manifest_role_names_listed(db_session: AsyncSession):
    result = await db_session.execute(
        select(User).where(User.email == TEST_ADMIN_EMAIL)
    )
    admin = result.scalar_one()

    builder = PermissionManifestBuilder(db_session)
    manifest = await builder.build_manifest(admin.id)

    assert "Super Admin" in manifest.role_names
