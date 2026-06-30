"""
Super-admin only: DB backup export and restore.

Backup  → GET  /admin/backup           → downloads a JSON snapshot
Restore → POST /admin/restore          → uploads a JSON snapshot and re-populates
Verify  → POST /admin/restore/verify   → validates a backup file without restoring
"""
import io
import json
import re
from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_super_admin
from app.modules.iam.schemas import PermissionManifestResponse

router = APIRouter(prefix="/admin", tags=["Admin"])

# ── Table list (dependency order — children come after parents) ───────────────

BACKUP_TABLES: list[tuple[str, str]] = [
    # Org — organizations must come first (root of FK tree)
    ("org", "organizations"),
    # Config reference data - many restored rows point at these IDs.
    ("config", "bloom_domains"),
    ("config", "bloom_levels"),
    ("config", "delivery_methods"),
    ("config", "course_categories"),
    ("config", "assessment_types"),
    ("config", "knowledge_profiles"),
    ("config", "mapping_weight_labels"),
    # OBE reference versions - programs and POs can point at these IDs.
    ("obe", "po_versions"),
    ("org", "departments"),
    ("org", "programs"),
    # IAM — core identity tables
    ("iam", "users"),
    ("iam", "password_credentials"),
    ("iam", "roles"),
    ("iam", "permissions"),
    ("iam", "role_permissions"),
    ("iam", "user_role_assignments"),
    # Config (user-managed reference data)
    ("config", "po_types"),
    ("config", "complex_problems"),
    ("config", "complex_activities"),
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
    # Outcomes are referenced by lesson-plan mappings and course mark tables.
    ("obe", "program_outcomes"),
    ("obe", "course_outcomes"),
    ("curriculum", "course_lesson_plan_item_cos"),
    ("curriculum", "course_lesson_plan_item_pos"),
    ("curriculum", "course_bloom_domains"),
    ("curriculum", "course_assessment_tools"),
    ("curriculum", "course_co_marks"),
    ("curriculum", "course_bloom_marks"),
    # OBE
    ("obe", "program_missions"),
    ("obe", "program_educational_objectives"),
    ("obe", "peo_po_mappings"),
    ("obe", "peo_mission_mappings"),
    ("obe", "po_knowledge_profiles"),
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


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _deserialize_row(row: dict) -> dict:
    out: dict = {}
    for k, v in row.items():
        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v)
            continue
        if isinstance(v, str):
            if "T" in v:
                try:
                    out[k] = datetime.fromisoformat(v)
                    continue
                except (ValueError, TypeError):
                    pass
            if _DATE_RE.match(v):
                try:
                    out[k] = date.fromisoformat(v)
                    continue
                except (ValueError, TypeError):
                    pass
            if len(v) == 36 and v.count("-") == 4 and _UUID_RE.match(v):
                try:
                    out[k] = UUID(v)
                    continue
                except (ValueError, TypeError):
                    pass
        out[k] = v
    return out


def _validate_backup(tables: dict) -> None:
    """Reject backups that are missing critical tables."""
    required = {"org.organizations", "iam.users", "iam.roles", "iam.permissions"}
    missing = required - set(tables.keys())
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Backup is missing required tables: {', '.join(sorted(missing))}. "
            "Please create a fresh backup from this version before restoring.",
        )


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
    from app.modules.iam.repository.role_repository import PermissionRepository, RoleRepository

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
    _validate_backup(tables)

    # Truncate in reverse order — CASCADE handles cross-schema FK references
    truncate_order = list(reversed(BACKUP_TABLES))

    try:
        for schema, table in truncate_order:
            await db.execute(text(f'TRUNCATE TABLE "{schema}"."{table}" CASCADE'))

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
                await db.execute(stmt, _deserialize_row(row))

        await db.commit()

    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(exc)}")


# ── Verify ────────────────────────────────────────────────────────────────────


@router.post("/restore/verify")
async def verify_backup(
    file: UploadFile = File(...),
    _: Annotated[PermissionManifestResponse, Depends(require_super_admin())] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    Validate a backup file and report what it contains.
    Does NOT modify the database.
    """
    raw = await file.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if payload.get("version") != 1:
        raise HTTPException(status_code=400, detail="Unsupported backup version")

    tables: dict = payload.get("tables", {})
    _validate_backup(tables)

    # Count current DB rows for comparison
    current_counts: dict[str, int] = {}
    for schema, table in BACKUP_TABLES:
        try:
            result = await db.execute(text(f'SELECT count(*) FROM "{schema}"."{table}"'))
            current_counts[f"{schema}.{table}"] = result.scalar()
        except Exception:
            current_counts[f"{schema}.{table}"] = -1

    # Count backup rows
    backup_counts: dict[str, int] = {}
    for schema, table in BACKUP_TABLES:
        key = f"{schema}.{table}"
        backup_counts[key] = len(tables.get(key, []))

    # Check role-permission map
    role_permissions_map: dict = payload.get("role_permissions", {})
    roles_count = len(role_permissions_map)
    total_perms = sum(len(v) for v in role_permissions_map.values())

    return {
        "valid": True,
        "exported_at": payload.get("exported_at"),
        "roles_in_map": roles_count,
        "total_role_permissions": total_perms,
        "tables": {
            key: {"backup_rows": backup_counts[key], "current_rows": current_counts.get(key, 0)}
            for key in sorted(
                {f"{s}.{t}" for s, t in BACKUP_TABLES}
                | set(backup_counts.keys())
                | set(current_counts.keys())
            )
        },
    }
