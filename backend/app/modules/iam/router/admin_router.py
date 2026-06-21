"""
Super-admin only: DB backup export and restore.

Backup  → GET  /admin/backup           → downloads a JSON snapshot
Restore → POST /admin/restore          → uploads a JSON snapshot and re-populates
"""
import io
import json
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin
from app.modules.iam.models import RolePermission
from app.modules.iam.repository.role_repository import PermissionRepository, RoleRepository
from app.modules.iam.schemas import PermissionManifestResponse

router = APIRouter(prefix="/admin", tags=["Admin"])

# ── Table list (dependency order — children come after parents) ───────────────

BACKUP_TABLES: list[tuple[str, str]] = [
    # Config (user-managed reference data)
    ("config", "po_types"),
    ("config", "complex_problems"),
    ("config", "complex_activities"),
    # Org
    ("org", "departments"),
    ("org", "programs"),
    # IAM — users before credentials/assignments
    ("iam", "users"),
    ("iam", "password_credentials"),
    ("iam", "user_role_assignments"),
    # Curriculum
    ("curriculum", "academic_terms"),
    ("curriculum", "curricula"),
    ("curriculum", "curriculum_term_definitions"),
    ("curriculum", "courses"),
    ("curriculum", "curriculum_course_slots"),
    ("curriculum", "batches"),
    ("curriculum", "batch_term_calendar"),
    ("curriculum", "sections"),
    ("curriculum", "section_offerings"),
    ("curriculum", "faculty_assignments"),
    ("curriculum", "module_leader_assignments"),
    ("curriculum", "course_objectives"),
    ("curriculum", "course_prerequisites"),
    ("curriculum", "course_learning_materials"),
    ("curriculum", "course_lesson_plan_items"),
    ("curriculum", "course_lesson_plan_item_cos"),
    ("curriculum", "course_lesson_plan_item_pos"),
    ("curriculum", "course_bloom_domains"),
    ("curriculum", "course_assessment_tools"),
    ("curriculum", "course_co_marks"),
    ("curriculum", "course_bloom_marks"),
    # OBE
    ("obe", "program_outcomes"),
    ("obe", "program_missions"),
    ("obe", "program_educational_objectives"),
    ("obe", "peo_po_mappings"),
    ("obe", "peo_mission_mappings"),
    ("obe", "po_knowledge_profiles"),
    ("obe", "course_outcomes"),
    ("obe", "course_outcome_bloom_levels"),
    ("obe", "co_delivery_methods"),
    ("obe", "co_cp_mappings"),
    ("obe", "co_ca_mappings"),
    ("obe", "co_kp_mappings"),
    ("obe", "co_po_mapping_sets"),
    ("obe", "co_po_mapping_entries"),
    # Assessment
    ("assessment", "students"),
    ("assessment", "student_enrollments"),
    ("assessment", "assessments"),
    ("assessment", "assessment_co_weights"),
    ("assessment", "student_marks"),
    ("assessment", "marksheet_questions"),
    ("assessment", "marksheet_marks"),
    ("assessment", "result_publications"),
    ("assessment", "course_end_reports"),
    # Attainment
    ("attainment", "attainment_configs"),
    ("attainment", "co_attainment_results"),
    ("attainment", "po_attainment_results"),
    # Accreditation
    ("accreditation", "accreditation_cycles"),
    ("accreditation", "accreditation_criteria"),
    ("accreditation", "criterion_po_mappings"),
    # Approval
    ("approval", "review_comments"),
]


def _serialize(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/backup")
async def export_backup(
    _: Annotated[PermissionManifestResponse, Depends(require_super_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Download a full JSON snapshot of all user data and role-permission assignments."""
    payload: dict = {
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "role_permissions": {},
        "tables": {},
    }

    # Role-permission assignments stored by name/code so they are portable
    role_repo = RoleRepository(db)
    perm_repo = PermissionRepository(db)

    roles = await role_repo.list_by_org(
        (await db.execute(text("SELECT organization_id FROM iam.users LIMIT 1"))).scalar()
    )
    all_perms = {p.id: p.code for p in await perm_repo.list_all()}

    for role in roles:
        role_with_perms = await role_repo.get_by_id(role.id)
        if role_with_perms:
            payload["role_permissions"][role.name] = [
                all_perms[p.id] for p in role_with_perms.permissions if p.id in all_perms
            ]

    # Table data
    for schema, table in BACKUP_TABLES:
        result = await db.execute(text(f'SELECT * FROM "{schema}"."{table}"'))
        rows = result.mappings().all()
        payload["tables"][f"{schema}.{table}"] = [
            {k: _serialize(v) for k, v in row.items()} for row in rows
        ]

    content = json.dumps(payload, indent=2, default=str)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=obelytics_backup_{ts}.json"},
    )


# ── Restore ───────────────────────────────────────────────────────────────────

@router.post("/restore", status_code=status.HTTP_204_NO_CONTENT)
async def import_backup(
    file: UploadFile = File(...),
    _: Annotated[PermissionManifestResponse, Depends(require_super_admin())] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    Restore from a JSON backup produced by GET /admin/backup.
    All operational data is wiped and re-populated from the file.
    """
    raw = await file.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if payload.get("version") != 1:
        raise HTTPException(status_code=400, detail="Unsupported backup version")

    tables: dict = payload.get("tables", {})
    role_permissions_map: dict = payload.get("role_permissions", {})

    # Truncate in reverse order so FK constraints are satisfied
    truncate_order = list(reversed(BACKUP_TABLES))

    try:
        # Disable FK triggers for the session so we can truncate/insert freely
        await db.execute(text("SET LOCAL session_replication_role = 'replica'"))

        for schema, table in truncate_order:
            await db.execute(text(f'TRUNCATE TABLE "{schema}"."{table}"'))

        # Re-insert in forward (dependency) order
        for schema, table in BACKUP_TABLES:
            key = f"{schema}.{table}"
            rows: list[dict] = tables.get(key, [])
            if not rows:
                continue
            cols = list(rows[0].keys())
            col_list = ", ".join(f'"{c}"' for c in cols)
            val_list = ", ".join(f":{c}" for c in cols)
            stmt = text(f'INSERT INTO "{schema}"."{table}" ({col_list}) VALUES ({val_list})')
            for row in rows:
                await db.execute(stmt, row)

        # Restore role-permission assignments by name/code (portable across envs)
        if role_permissions_map:
            role_repo = RoleRepository(db)
            perm_repo = PermissionRepository(db)

            org_id_result = await db.execute(text("SELECT id FROM org.organizations LIMIT 1"))
            org_id = org_id_result.scalar()

            all_roles = await role_repo.list_by_org(org_id)
            role_by_name = {r.name: r for r in all_roles}

            all_perms = await perm_repo.list_all()
            perm_by_code = {p.code: p for p in all_perms}

            # Clear all existing role_permissions
            await db.execute(delete(RolePermission))

            for role_name, perm_codes in role_permissions_map.items():
                role = role_by_name.get(role_name)
                if not role:
                    continue
                for code in perm_codes:
                    perm = perm_by_code.get(code)
                    if perm:
                        db.add(RolePermission(role_id=role.id, permission_id=perm.id))

        await db.commit()

    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(exc)}")
