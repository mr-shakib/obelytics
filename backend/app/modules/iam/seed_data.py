"""
Authoritative permission and role definitions for Obelytics.

Imported by both the seed script (scripts/seed_superadmin.py) and the
test fixtures (tests/conftest.py) to ensure they stay in sync.
"""

ALL_PERMISSIONS: list[dict] = [
    # ── IAM / System ──────────────────────────────────────────────────────────
    {"code": "system.organization.configure", "module": "org",          "description": "Configure organization settings"},
    {"code": "department.create",             "module": "org",          "description": "Create departments"},
    {"code": "department.update",             "module": "org",          "description": "Update departments"},
    {"code": "department.archive",            "module": "org",          "description": "Archive departments"},
    {"code": "program.create",                "module": "org",          "description": "Create programs"},
    {"code": "program.update",                "module": "org",          "description": "Update programs"},
    {"code": "program.archive",               "module": "org",          "description": "Archive programs"},
    {"code": "user.create",                   "module": "iam",          "description": "Create users"},
    {"code": "user.read",                     "module": "iam",          "description": "View user list"},
    {"code": "user.update",                   "module": "iam",          "description": "Update users"},
    {"code": "user.role.assign",              "module": "iam",          "description": "Assign roles to users"},
    {"code": "system.roles.create",           "module": "iam",          "description": "Create custom roles"},
    {"code": "system.permissions.grant",      "module": "iam",          "description": "Grant permissions to roles"},
    {"code": "config.manage",                 "module": "ref_data",     "description": "Manage reference data"},
    {"code": "system.audit.read",             "module": "audit",        "description": "View audit logs"},
    # ── Curriculum ────────────────────────────────────────────────────────────
    {"code": "curriculum.create",             "module": "curriculum",   "description": "Create curricula"},
    {"code": "curriculum.update",             "module": "curriculum",   "description": "Update curricula"},
    {"code": "curriculum.version",            "module": "curriculum",   "description": "Version curricula"},
    {"code": "curriculum.read",               "module": "curriculum",   "description": "Read curricula"},
    {"code": "course.create",                 "module": "curriculum",   "description": "Create courses"},
    {"code": "course.update",                 "module": "curriculum",   "description": "Update courses"},
    {"code": "batch.create",                  "module": "curriculum",   "description": "Create batches"},
    {"code": "section_offering.create",       "module": "curriculum",   "description": "Create section offerings"},
    {"code": "faculty_assignment.create",     "module": "curriculum",   "description": "Assign faculty"},
    # ── OBE ───────────────────────────────────────────────────────────────────
    {"code": "po.create",                     "module": "obe",          "description": "Create program outcomes"},
    {"code": "po.update",                     "module": "obe",          "description": "Update program outcomes"},
    {"code": "po.archive",                    "module": "obe",          "description": "Archive program outcomes"},
    {"code": "po.read",                       "module": "obe",          "description": "Read program outcomes"},
    {"code": "co.create",                     "module": "obe",          "description": "Create course outcomes"},
    {"code": "co.update",                     "module": "obe",          "description": "Update course outcomes"},
    {"code": "co.submit",                     "module": "obe",          "description": "Submit COs for approval"},
    {"code": "co.approve",                    "module": "obe",          "description": "Approve course outcomes"},
    {"code": "co.reject",                     "module": "obe",          "description": "Reject course outcomes"},
    {"code": "co.publish",                    "module": "obe",          "description": "Publish course outcomes"},
    {"code": "co.read",                       "module": "obe",          "description": "Read course outcomes"},
    {"code": "mapping.co_po.create",          "module": "obe",          "description": "Create CO-PO mappings"},
    {"code": "mapping.co_po.update",          "module": "obe",          "description": "Update CO-PO mappings"},
    {"code": "mapping.co_po.publish",         "module": "obe",          "description": "Publish CO-PO mapping set"},
    {"code": "mapping.co_po.read",            "module": "obe",          "description": "Read CO-PO mappings"},
    {"code": "mapping.co_cp.manage",          "module": "obe",          "description": "Author CO-CP mappings"},
    {"code": "mapping.co_cp.approve",         "module": "obe",          "description": "Approve CO-CP mappings"},
    {"code": "mapping.co_ca.manage",          "module": "obe",          "description": "Author CO-CA mappings"},
    {"code": "mapping.co_ca.approve",         "module": "obe",          "description": "Approve CO-CA mappings"},
    {"code": "mapping.co_kp.manage",          "module": "obe",          "description": "Author CO-KP mappings"},
    {"code": "mapping.co_kp.approve",         "module": "obe",          "description": "Approve CO-KP mappings"},
    # ── Assessment ────────────────────────────────────────────────────────────
    {"code": "assessment.configure",          "module": "assessment",   "description": "Configure assessments"},
    {"code": "assessment.publish_config",     "module": "assessment",   "description": "Publish assessment config"},
    {"code": "assessment.read",               "module": "assessment",   "description": "Read assessment configuration"},
    {"code": "marks.enter",                   "module": "assessment",   "description": "Enter student marks"},
    {"code": "marks.update",                  "module": "assessment",   "description": "Update student marks"},
    {"code": "marks.read.all",                "module": "assessment",   "description": "Read all marks in program"},
    {"code": "marks.read.section",            "module": "assessment",   "description": "Read marks for assigned section"},
    {"code": "result.submit",                 "module": "assessment",   "description": "Submit results for approval"},
    {"code": "result.approve.ml",             "module": "assessment",   "description": "Approve results (ML step)"},
    {"code": "result.reject.ml",              "module": "assessment",   "description": "Reject results (ML step)"},
    {"code": "result.approve.pc",             "module": "assessment",   "description": "Approve results (PC step)"},
    {"code": "result.publish",                "module": "assessment",   "description": "Publish results"},
    {"code": "result.read.section",           "module": "assessment",   "description": "Read results for assigned section"},
    # ── Attainment ────────────────────────────────────────────────────────────
    {"code": "attainment.configure",          "module": "attainment",   "description": "Configure attainment thresholds"},
    {"code": "attainment.initiate",           "module": "attainment",   "description": "Initiate attainment run"},
    {"code": "attainment.publish",            "module": "attainment",   "description": "Publish attainment run"},
    {"code": "attainment.read",               "module": "attainment",   "description": "Read attainment results"},
    # ── Reporting ─────────────────────────────────────────────────────────────
    {"code": "report.generate",               "module": "reporting",    "description": "Generate all reports"},
    {"code": "report.co.generate",            "module": "reporting",    "description": "Generate CO reports"},
    {"code": "report.assessment.generate",    "module": "reporting",    "description": "Generate assessment reports"},
    # ── Accreditation ─────────────────────────────────────────────────────────
    {"code": "accreditation.cycle.create",    "module": "accreditation","description": "Create accreditation cycles"},
    {"code": "accreditation.read",            "module": "accreditation","description": "View accreditation cycles and criteria"},
    {"code": "accreditation.manage",          "module": "accreditation","description": "Manage accreditation cycles, criteria, and mappings"},
    # ── Approval ──────────────────────────────────────────────────────────────
    {"code": "approval.inbox.read",           "module": "approval",     "description": "View approval inbox and add review comments"},
    # ── Student self-service ──────────────────────────────────────────────────
    {"code": "student.profile.read.own",      "module": "iam",          "description": "View own student profile"},
    {"code": "student.curriculum.read.own",   "module": "curriculum",   "description": "View own enrolled curriculum"},
    {"code": "student.course.read.own",       "module": "curriculum",   "description": "View own enrolled courses"},
    {"code": "student.po.read.own",           "module": "obe",          "description": "View POs for own program"},
    {"code": "student.co.read.own",           "module": "obe",          "description": "View COs for own courses"},
    {"code": "student.marks.read.own",        "module": "assessment",   "description": "View own published marks"},
    {"code": "student.result.read.own",       "module": "assessment",   "description": "View own published results"},
    # ── Notifications ─────────────────────────────────────────────────────────
    {"code": "notification.read.own",         "module": "notification", "description": "View and manage own notifications"},
]

_SA = "Super Admin"
_PC = "Program Coordinator"
_ML = "Module Leader"
_ST = "Section Teacher"
_S  = "Student"

ROLES: list[dict] = [
    {
        "name": _SA,
        "description": "Full system access",
        "permissions": [p["code"] for p in ALL_PERMISSIONS],
    },
    {
        "name": _PC,
        "description": "Manages curriculum, OBE, assessment, and attainment for assigned programs",
        "permissions": [
            "system.organization.configure",
            "department.create", "department.update",
            "program.create", "program.update",
            "user.create", "user.read", "user.update", "user.role.assign",
            "config.manage",
            "curriculum.create", "curriculum.update", "curriculum.version", "curriculum.read",
            "course.create", "course.update",
            "batch.create", "section_offering.create", "faculty_assignment.create",
            "po.create", "po.update", "po.archive", "po.read",
            "co.approve", "co.reject", "co.publish", "co.read",
            "mapping.co_po.create", "mapping.co_po.update", "mapping.co_po.publish", "mapping.co_po.read",
            "mapping.co_cp.approve", "mapping.co_ca.approve", "mapping.co_kp.approve",
            "assessment.configure", "assessment.publish_config", "assessment.read",
            "marks.read.all",
            "result.approve.pc", "result.publish",
            "attainment.configure", "attainment.initiate", "attainment.publish", "attainment.read",
            "report.generate", "report.co.generate", "report.assessment.generate",
            "accreditation.cycle.create", "accreditation.read", "accreditation.manage",
            "approval.inbox.read",
            "notification.read.own",
        ],
    },
    {
        "name": _ML,
        "description": "Reviews COs and marks for assigned courses",
        "permissions": [
            "curriculum.read", "po.read",
            "course.update",
            "co.read", "co.create", "co.update", "co.approve", "co.reject",
            "mapping.co_po.read", "mapping.co_po.create", "mapping.co_po.update",
            "mapping.co_cp.manage", "mapping.co_cp.approve",
            "mapping.co_ca.manage", "mapping.co_ca.approve",
            "mapping.co_kp.approve",
            "assessment.read",
            "marks.read.section",
            "result.approve.ml", "result.reject.ml",
            "attainment.read",
            "report.co.generate", "report.assessment.generate",
            "accreditation.read",
            "approval.inbox.read",
            "notification.read.own",
        ],
    },
    {
        "name": _ST,
        "description": "Creates COs and enters marks for assigned sections",
        "permissions": [
            "curriculum.read", "po.read",
            "co.create", "co.update", "co.submit", "co.read",
            "mapping.co_po.read",
            "mapping.co_cp.manage", "mapping.co_ca.manage", "mapping.co_kp.manage",
            "assessment.read",
            "marks.enter", "marks.update",
            "result.submit", "result.read.section",
            "attainment.read",
            "approval.inbox.read",
            "notification.read.own",
        ],
    },
    {
        "name": _S,
        "description": "View own academic records",
        "permissions": [
            "student.profile.read.own",
            "student.curriculum.read.own",
            "student.course.read.own",
            "student.po.read.own",
            "student.co.read.own",
            "student.marks.read.own",
            "student.result.read.own",
            "notification.read.own",
        ],
    },
]

ROLE_NAMES = [r["name"] for r in ROLES]
