-- ============================================================
-- OBE Accreditation Management Platform
-- Complete PostgreSQL DDL — v1.0
-- Database: PostgreSQL 16+
-- Generated from: DB Architecture v1.0 + System Blueprint v1.0
-- ============================================================

-- ============================================================
-- SCHEMAS
-- ============================================================

CREATE SCHEMA IF NOT EXISTS config;
CREATE SCHEMA IF NOT EXISTS iam;
CREATE SCHEMA IF NOT EXISTS org;
CREATE SCHEMA IF NOT EXISTS curriculum;
CREATE SCHEMA IF NOT EXISTS obe;
CREATE SCHEMA IF NOT EXISTS assessment;
CREATE SCHEMA IF NOT EXISTS attainment;
CREATE SCHEMA IF NOT EXISTS approval;
CREATE SCHEMA IF NOT EXISTS notification;
CREATE SCHEMA IF NOT EXISTS events;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS accreditation;
CREATE SCHEMA IF NOT EXISTS reporting;

-- ============================================================
-- CONFIG SCHEMA — Reference / lookup data
-- ============================================================

CREATE TABLE config.bloom_domains (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL,
    name             VARCHAR(100) NOT NULL,
    description      TEXT,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_bloom_domain_name UNIQUE (organization_id, name)
);

CREATE TABLE config.bloom_levels (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL,
    bloom_domain_id  UUID        NOT NULL REFERENCES config.bloom_domains(id),
    code             VARCHAR(10) NOT NULL,
    name             VARCHAR(100) NOT NULL,
    order_index      SMALLINT    NOT NULL,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_bloom_level_code UNIQUE (organization_id, bloom_domain_id, code)
);

CREATE TABLE config.delivery_methods (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL,
    name             VARCHAR(100) NOT NULL,
    description      TEXT,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_delivery_method_name UNIQUE (organization_id, name)
);

CREATE TABLE config.course_types (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL,
    name             VARCHAR(100) NOT NULL,
    description      TEXT,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_course_type_name UNIQUE (organization_id, name)
);

CREATE TABLE config.assessment_types (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL,
    name             VARCHAR(100) NOT NULL,
    is_sessional     BOOLEAN     NOT NULL DEFAULT FALSE,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_assessment_type_name UNIQUE (organization_id, name)
);

CREATE TABLE config.complex_problems (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL,
    code             VARCHAR(20) NOT NULL,
    description      TEXT        NOT NULL,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_complex_problem_code UNIQUE (organization_id, code)
);

CREATE TABLE config.complex_activities (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL,
    code             VARCHAR(20) NOT NULL,
    description      TEXT        NOT NULL,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_complex_activity_code UNIQUE (organization_id, code)
);

CREATE TABLE config.knowledge_profiles (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL,
    code             VARCHAR(20) NOT NULL,
    description      TEXT        NOT NULL,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_knowledge_profile_code UNIQUE (organization_id, code)
);

CREATE TABLE config.mapping_weight_labels (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL,
    weight_value     SMALLINT    NOT NULL,
    label            VARCHAR(50) NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_mapping_weight UNIQUE (organization_id, weight_value),
    CONSTRAINT chk_weight_range CHECK (weight_value IN (1, 2, 3))
);

-- ============================================================
-- ORG SCHEMA — Organization, departments, programs
-- ============================================================

CREATE TABLE org.organizations (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    VARCHAR(255) NOT NULL,
    short_name              VARCHAR(50)  NOT NULL UNIQUE,
    description             TEXT,
    vision                  TEXT,
    mission                 TEXT,
    logo_file_key           VARCHAR(500),
    website                 VARCHAR(255),
    address_street          VARCHAR(255),
    address_city            VARCHAR(100),
    address_country         VARCHAR(100),
    address_postal_code     VARCHAR(20),
    contact_email           VARCHAR(255),
    contact_phone           VARCHAR(50),
    email_validation_regex  VARCHAR(500),
    status                  VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE org.departments (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID         NOT NULL REFERENCES org.organizations(id),
    name             VARCHAR(200) NOT NULL,
    short_name       VARCHAR(30)  NOT NULL,
    year_established SMALLINT,
    description      TEXT,
    vision           TEXT,
    mission          TEXT,
    status           VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    archived_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_dept_short_name_active
    ON org.departments(organization_id, short_name)
    WHERE status = 'ACTIVE';

CREATE TABLE org.programs (
    id                           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id              UUID         NOT NULL REFERENCES org.organizations(id),
    department_id                UUID         NOT NULL REFERENCES org.departments(id),
    title                        VARCHAR(255) NOT NULL,
    acronym                      VARCHAR(20)  NOT NULL,
    program_type                 VARCHAR(20)  NOT NULL,
    minimum_duration_semesters   SMALLINT     NOT NULL,
    total_credits                SMALLINT     NOT NULL,
    study_mode                   VARCHAR(20)  NOT NULL DEFAULT 'FULL_TIME',
    description                  TEXT,
    status                       VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    archived_at                  TIMESTAMPTZ,
    created_at                   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_program_type  CHECK (program_type IN ('UNDERGRADUATE','POSTGRADUATE','PHD')),
    CONSTRAINT chk_study_mode    CHECK (study_mode IN ('FULL_TIME','PART_TIME'))
);

CREATE UNIQUE INDEX uq_program_acronym_active
    ON org.programs(organization_id, acronym)
    WHERE status = 'ACTIVE';

CREATE INDEX idx_programs_department ON org.programs(department_id);

-- ============================================================
-- IAM SCHEMA — Identity and access management
-- Note: linked_student_id FK added after assessment.students
-- ============================================================

CREATE TABLE iam.users (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID         NOT NULL REFERENCES org.organizations(id),
    department_id       UUID         REFERENCES org.departments(id),
    linked_student_id   UUID,        -- FK added after assessment.students created
    faculty_type        VARCHAR(30),
    title               VARCHAR(20),
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    email               VARCHAR(255) NOT NULL,
    contact_number      VARCHAR(30),
    designation         VARCHAR(150),
    status              VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    deactivated_at      TIMESTAMPTZ,
    email_verified_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_user_status CHECK (status IN ('ACTIVE','DEACTIVATED'))
);

CREATE UNIQUE INDEX uq_user_email_per_org ON iam.users(organization_id, email);
CREATE INDEX idx_users_org       ON iam.users(organization_id) WHERE status = 'ACTIVE';
CREATE INDEX idx_users_email     ON iam.users(email)            WHERE status = 'ACTIVE';
CREATE INDEX idx_users_dept      ON iam.users(department_id);

CREATE TABLE iam.password_credentials (
    id                       UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                  UUID         NOT NULL UNIQUE REFERENCES iam.users(id),
    password_hash            VARCHAR(255) NOT NULL,
    reset_token_hash         VARCHAR(255),
    reset_token_expires_at   TIMESTAMPTZ,
    last_changed_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE iam.refresh_tokens (
    id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID         NOT NULL REFERENCES iam.users(id),
    token_hash           VARCHAR(255) NOT NULL UNIQUE,
    expires_at           TIMESTAMPTZ  NOT NULL,
    revoked_at           TIMESTAMPTZ,
    device_fingerprint   VARCHAR(255),
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user_expiry
    ON iam.refresh_tokens(user_id, expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE iam.roles (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID         REFERENCES org.organizations(id),
    name             VARCHAR(100) NOT NULL,
    description      TEXT,
    is_system_role   BOOLEAN      NOT NULL DEFAULT FALSE,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_role_name UNIQUE (organization_id, name)
);

CREATE TABLE iam.permissions (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID         REFERENCES org.organizations(id),
    code             VARCHAR(150) NOT NULL,
    description      TEXT,
    tier             VARCHAR(10)  NOT NULL DEFAULT 'DOMAIN',
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_permission_tier CHECK (tier IN ('SYSTEM','DOMAIN','STUDENT','CUSTOM'))
);

CREATE UNIQUE INDEX uq_system_permission_code
    ON iam.permissions(code) WHERE tier = 'SYSTEM';
CREATE UNIQUE INDEX uq_custom_permission_code
    ON iam.permissions(organization_id, code) WHERE tier IN ('DOMAIN','CUSTOM','STUDENT');

CREATE TABLE iam.role_permissions (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id              UUID        NOT NULL REFERENCES iam.roles(id),
    permission_id        UUID        NOT NULL REFERENCES iam.permissions(id),
    granted_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_by_user_id   UUID        REFERENCES iam.users(id),
    CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
);

CREATE INDEX idx_role_permissions_role ON iam.role_permissions(role_id);

CREATE TABLE iam.user_role_assignments (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID        NOT NULL REFERENCES iam.users(id),
    role_id               UUID        NOT NULL REFERENCES iam.roles(id),
    scope_type            VARCHAR(20) NOT NULL DEFAULT 'PROGRAM',
    scope_id              UUID,
    assigned_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by_user_id   UUID        REFERENCES iam.users(id),
    revoked_at            TIMESTAMPTZ,
    CONSTRAINT chk_scope_type CHECK (scope_type IN ('GLOBAL','DEPARTMENT','PROGRAM'))
);

CREATE UNIQUE INDEX uq_user_role_assignment_active
    ON iam.user_role_assignments(user_id, role_id, scope_type, COALESCE(scope_id, '00000000-0000-0000-0000-000000000000'))
    WHERE revoked_at IS NULL;

CREATE INDEX idx_ura_user  ON iam.user_role_assignments(user_id)  WHERE revoked_at IS NULL;
CREATE INDEX idx_ura_role  ON iam.user_role_assignments(role_id);
CREATE INDEX idx_ura_scope ON iam.user_role_assignments(scope_type, scope_id) WHERE revoked_at IS NULL;

-- ============================================================
-- ORG.DEPARTMENT_HEAD_HISTORY
-- After iam.users to resolve FK order
-- ============================================================

CREATE TABLE org.department_head_history (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id   UUID        NOT NULL REFERENCES org.departments(id),
    user_id         UUID        NOT NULL REFERENCES iam.users(id),
    effective_from  DATE        NOT NULL,
    effective_to    DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tenure CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE UNIQUE INDEX uq_current_hod
    ON org.department_head_history(department_id)
    WHERE effective_to IS NULL;

CREATE INDEX idx_dept_head_dept ON org.department_head_history(department_id);

-- ============================================================
-- ORG.PROGRAM_COORDINATOR_HISTORY
-- After iam.users to resolve FK order
-- ============================================================

CREATE TABLE org.program_coordinator_history (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id      UUID        NOT NULL REFERENCES org.programs(id),
    user_id         UUID        NOT NULL REFERENCES iam.users(id),
    effective_from  DATE        NOT NULL,
    effective_to    DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_coordinator_tenure CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE UNIQUE INDEX uq_current_program_coordinator
    ON org.program_coordinator_history(program_id)
    WHERE effective_to IS NULL;

CREATE INDEX idx_program_coordinator_program ON org.program_coordinator_history(program_id);

-- ============================================================
-- CURRICULUM SCHEMA
-- ============================================================

CREATE TABLE curriculum.curricula (
    id                    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id       UUID         NOT NULL REFERENCES org.organizations(id),
    program_id            UUID         NOT NULL REFERENCES org.programs(id),
    name                  VARCHAR(255) NOT NULL,
    code                  VARCHAR(50)  NOT NULL,
    effective_year        SMALLINT     NOT NULL,
    version_number        SMALLINT     NOT NULL DEFAULT 1,
    parent_curriculum_id  UUID         REFERENCES curriculum.curricula(id),
    status                VARCHAR(20)  NOT NULL DEFAULT 'DRAFT',
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_curriculum_version UNIQUE (program_id, code, version_number),
    CONSTRAINT chk_curriculum_status CHECK (status IN ('DRAFT','ACTIVE','VERSIONED','ARCHIVED'))
);

CREATE INDEX idx_curricula_program ON curriculum.curricula(program_id, status);
CREATE INDEX idx_curricula_parent  ON curriculum.curricula(parent_curriculum_id);

CREATE TABLE curriculum.curriculum_term_definitions (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    curriculum_id UUID         NOT NULL REFERENCES curriculum.curricula(id),
    term_number   SMALLINT     NOT NULL,
    name          VARCHAR(100) NOT NULL,
    total_credit_hours SMALLINT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_term_number UNIQUE (curriculum_id, term_number)
);

CREATE INDEX idx_term_defs_curriculum ON curriculum.curriculum_term_definitions(curriculum_id);

CREATE TABLE curriculum.courses (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID         NOT NULL REFERENCES org.organizations(id),
    course_type_id   UUID         NOT NULL REFERENCES config.course_types(id),
    code             VARCHAR(30)  NOT NULL,
    title            VARCHAR(255) NOT NULL,
    credits          SMALLINT     NOT NULL,
    theory_hours     SMALLINT     NOT NULL DEFAULT 0,
    lab_hours        SMALLINT     NOT NULL DEFAULT 0,
    description      TEXT,
    status           VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    archived_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_course_status CHECK (status IN ('ACTIVE','ARCHIVED'))
);

CREATE UNIQUE INDEX uq_course_code_active
    ON curriculum.courses(organization_id, code)
    WHERE status = 'ACTIVE';

CREATE TABLE curriculum.curriculum_course_slots (
    id                           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    curriculum_id                UUID        NOT NULL REFERENCES curriculum.curricula(id),
    curriculum_term_definition_id UUID       NOT NULL REFERENCES curriculum.curriculum_term_definitions(id),
    course_id                    UUID        NOT NULL REFERENCES curriculum.courses(id),
    is_elective                  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_course_in_curriculum UNIQUE (curriculum_id, course_id)
);

CREATE INDEX idx_slots_curriculum ON curriculum.curriculum_course_slots(curriculum_id);
CREATE INDEX idx_slots_course     ON curriculum.curriculum_course_slots(course_id);

CREATE TABLE curriculum.course_prerequisites (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID        NOT NULL REFERENCES org.organizations(id),
    course_id               UUID        NOT NULL REFERENCES curriculum.courses(id),
    prerequisite_course_id  UUID        NOT NULL REFERENCES curriculum.courses(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_prerequisite      UNIQUE (course_id, prerequisite_course_id),
    CONSTRAINT chk_no_self_prereq   CHECK (course_id <> prerequisite_course_id)
);

CREATE INDEX idx_prereq_course    ON curriculum.course_prerequisites(course_id);
CREATE INDEX idx_prereq_required  ON curriculum.course_prerequisites(prerequisite_course_id);

CREATE TABLE curriculum.batches (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID         NOT NULL REFERENCES org.organizations(id),
    curriculum_id    UUID         NOT NULL REFERENCES curriculum.curricula(id),
    name             VARCHAR(100) NOT NULL,
    intake_year      SMALLINT     NOT NULL,
    graduation_year  SMALLINT,
    status           VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_batch_name     UNIQUE (curriculum_id, name),
    CONSTRAINT chk_batch_status  CHECK (status IN ('ACTIVE','GRADUATED','ARCHIVED'))
);

CREATE INDEX idx_batches_curriculum ON curriculum.batches(curriculum_id, status);

CREATE TABLE curriculum.academic_terms (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID         NOT NULL REFERENCES org.organizations(id),
    name             VARCHAR(100) NOT NULL,
    year             SMALLINT     NOT NULL,
    season           VARCHAR(20)  NOT NULL,
    start_date       DATE         NOT NULL,
    end_date         DATE         NOT NULL,
    status           VARCHAR(20)  NOT NULL DEFAULT 'UPCOMING',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_academic_term    UNIQUE (organization_id, year, season),
    CONSTRAINT chk_term_dates      CHECK (end_date > start_date),
    CONSTRAINT chk_term_season     CHECK (season IN ('SPRING','SUMMER','FALL','WINTER')),
    CONSTRAINT chk_term_status     CHECK (status IN ('UPCOMING','ACTIVE','COMPLETED'))
);

CREATE INDEX idx_academic_terms_org ON curriculum.academic_terms(organization_id, status);

CREATE TABLE curriculum.sections (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL REFERENCES org.organizations(id),
    name             VARCHAR(50) NOT NULL,
    capacity         SMALLINT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_section_name UNIQUE (organization_id, name)
);

CREATE TABLE curriculum.section_offerings (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL REFERENCES org.organizations(id),
    curriculum_id    UUID        NOT NULL REFERENCES curriculum.curricula(id),
    batch_id         UUID        NOT NULL REFERENCES curriculum.batches(id),
    course_id        UUID        NOT NULL REFERENCES curriculum.courses(id),
    academic_term_id UUID        NOT NULL REFERENCES curriculum.academic_terms(id),
    section_id       UUID        NOT NULL REFERENCES curriculum.sections(id),
    status           VARCHAR(20) NOT NULL DEFAULT 'UPCOMING',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_section_offering UNIQUE (batch_id, course_id, academic_term_id, section_id),
    CONSTRAINT chk_offering_status CHECK (status IN ('UPCOMING','ACTIVE','COMPLETED'))
);

CREATE INDEX idx_offerings_batch   ON curriculum.section_offerings(batch_id, academic_term_id);
CREATE INDEX idx_offerings_course  ON curriculum.section_offerings(course_id, academic_term_id);
CREATE INDEX idx_offerings_term    ON curriculum.section_offerings(academic_term_id);

CREATE TABLE curriculum.faculty_assignments (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    section_offering_id UUID        NOT NULL REFERENCES curriculum.section_offerings(id),
    user_id             UUID        NOT NULL REFERENCES iam.users(id),
    role_in_course      VARCHAR(30) NOT NULL,
    assigned_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    removed_at          TIMESTAMPTZ,
    CONSTRAINT chk_faculty_role CHECK (role_in_course IN ('MODULE_LEADER','SECTION_TEACHER'))
);

CREATE UNIQUE INDEX uq_faculty_assignment_active
    ON curriculum.faculty_assignments(section_offering_id, user_id, role_in_course)
    WHERE removed_at IS NULL;

CREATE INDEX idx_faculty_user     ON curriculum.faculty_assignments(user_id)              WHERE removed_at IS NULL;
CREATE INDEX idx_faculty_offering ON curriculum.faculty_assignments(section_offering_id)  WHERE removed_at IS NULL;

-- ============================================================
-- OBE SCHEMA — Program outcomes, course outcomes, mappings
-- ============================================================

CREATE TABLE obe.program_outcomes (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID        NOT NULL REFERENCES org.organizations(id),
    program_id       UUID        NOT NULL REFERENCES org.programs(id),
    bloom_domain_id  UUID        REFERENCES config.bloom_domains(id),
    code             VARCHAR(20) NOT NULL,
    reference        VARCHAR(100),
    statement        TEXT        NOT NULL,
    po_type          VARCHAR(100),
    order_index      SMALLINT    NOT NULL DEFAULT 1,
    status           VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    archived_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_po_status CHECK (status IN ('ACTIVE','ARCHIVED'))
);

CREATE UNIQUE INDEX uq_po_code_active
    ON obe.program_outcomes(program_id, code)
    WHERE status = 'ACTIVE';

CREATE INDEX idx_po_program ON obe.program_outcomes(program_id, status);

CREATE TABLE obe.po_knowledge_profiles (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    program_outcome_id   UUID        NOT NULL REFERENCES obe.program_outcomes(id),
    knowledge_profile_id UUID        NOT NULL REFERENCES config.knowledge_profiles(id),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_po_kp UNIQUE (program_outcome_id, knowledge_profile_id)
);

CREATE TABLE obe.course_outcomes (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID        NOT NULL REFERENCES org.organizations(id),
    curriculum_id       UUID        NOT NULL REFERENCES curriculum.curricula(id),
    course_id           UUID        NOT NULL REFERENCES curriculum.courses(id),
    bloom_level_id      UUID        REFERENCES config.bloom_levels(id),
    code                VARCHAR(20) NOT NULL,
    statement           TEXT        NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_by_user_id  UUID        REFERENCES iam.users(id),
    locked_at           TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_co_code        UNIQUE (curriculum_id, course_id, code),
    CONSTRAINT chk_co_status     CHECK (status IN ('DRAFT','SUBMITTED','UNDER_REVIEW','APPROVED','PUBLISHED','LOCKED'))
);

CREATE INDEX idx_co_curriculum_course ON obe.course_outcomes(curriculum_id, course_id, status);
CREATE INDEX idx_co_course            ON obe.course_outcomes(course_id);

CREATE TABLE obe.co_delivery_methods (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    course_outcome_id   UUID        NOT NULL REFERENCES obe.course_outcomes(id),
    delivery_method_id  UUID        NOT NULL REFERENCES config.delivery_methods(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_co_delivery_method UNIQUE (course_outcome_id, delivery_method_id)
);

CREATE INDEX idx_co_dm_co ON obe.co_delivery_methods(course_outcome_id);

CREATE TABLE obe.co_po_mapping_sets (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID        NOT NULL REFERENCES org.organizations(id),
    curriculum_id       UUID        NOT NULL REFERENCES curriculum.curricula(id),
    course_id           UUID        NOT NULL REFERENCES curriculum.courses(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_by_user_id  UUID        REFERENCES iam.users(id),
    approved_by_user_id UUID        REFERENCES iam.users(id),
    approved_at         TIMESTAMPTZ,
    published_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_co_po_mapping_set UNIQUE (curriculum_id, course_id),
    CONSTRAINT chk_mapping_status   CHECK (status IN ('DRAFT','APPROVED','PUBLISHED'))
);

CREATE INDEX idx_mapping_set_curriculum ON obe.co_po_mapping_sets(curriculum_id, course_id);

CREATE TABLE obe.co_po_mapping_entries (
    id                  UUID       PRIMARY KEY DEFAULT gen_random_uuid(),
    mapping_set_id      UUID       NOT NULL REFERENCES obe.co_po_mapping_sets(id),
    course_outcome_id   UUID       NOT NULL REFERENCES obe.course_outcomes(id),
    program_outcome_id  UUID       NOT NULL REFERENCES obe.program_outcomes(id),
    weight              SMALLINT   NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_co_po_entry   UNIQUE (mapping_set_id, course_outcome_id, program_outcome_id),
    CONSTRAINT chk_entry_weight CHECK (weight IN (1, 2, 3))
);

CREATE INDEX idx_co_po_entries_set ON obe.co_po_mapping_entries(mapping_set_id);
CREATE INDEX idx_co_po_entries_co  ON obe.co_po_mapping_entries(course_outcome_id);
CREATE INDEX idx_co_po_entries_po  ON obe.co_po_mapping_entries(program_outcome_id);

CREATE TABLE obe.co_cp_mappings (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    course_outcome_id   UUID        NOT NULL REFERENCES obe.course_outcomes(id),
    complex_problem_id  UUID        NOT NULL REFERENCES config.complex_problems(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_co_cp    UNIQUE (course_outcome_id, complex_problem_id),
    CONSTRAINT chk_co_cp_status CHECK (status IN ('DRAFT','APPROVED'))
);

CREATE INDEX idx_co_cp_co ON obe.co_cp_mappings(course_outcome_id);

CREATE TABLE obe.co_ca_mappings (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    course_outcome_id     UUID        NOT NULL REFERENCES obe.course_outcomes(id),
    complex_activity_id   UUID        NOT NULL REFERENCES config.complex_activities(id),
    status                VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_co_ca         UNIQUE (course_outcome_id, complex_activity_id),
    CONSTRAINT chk_co_ca_status CHECK (status IN ('DRAFT','APPROVED'))
);

CREATE INDEX idx_co_ca_co ON obe.co_ca_mappings(course_outcome_id);

CREATE TABLE obe.co_kp_mappings (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    course_outcome_id     UUID        NOT NULL REFERENCES obe.course_outcomes(id),
    knowledge_profile_id  UUID        NOT NULL REFERENCES config.knowledge_profiles(id),
    status                VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_co_kp         UNIQUE (course_outcome_id, knowledge_profile_id),
    CONSTRAINT chk_co_kp_status CHECK (status IN ('DRAFT','APPROVED'))
);

CREATE INDEX idx_co_kp_co ON obe.co_kp_mappings(course_outcome_id);

-- ============================================================
-- ASSESSMENT SCHEMA
-- ============================================================

CREATE TABLE assessment.students (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID         NOT NULL REFERENCES org.organizations(id),
    batch_id          UUID         NOT NULL REFERENCES curriculum.batches(id),
    student_id_number VARCHAR(50)  NOT NULL,
    first_name        VARCHAR(100) NOT NULL,
    last_name         VARCHAR(100) NOT NULL,
    email             VARCHAR(255),
    status            VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_student_id_number UNIQUE (organization_id, student_id_number),
    CONSTRAINT chk_student_status   CHECK (status IN ('ACTIVE','GRADUATED','WITHDRAWN'))
);

CREATE INDEX idx_students_batch ON assessment.students(batch_id, status);

-- Deferred FK: iam.users.linked_student_id → assessment.students.id
ALTER TABLE iam.users
    ADD CONSTRAINT fk_users_linked_student
    FOREIGN KEY (linked_student_id) REFERENCES assessment.students(id);

CREATE UNIQUE INDEX uq_linked_student
    ON iam.users(linked_student_id)
    WHERE linked_student_id IS NOT NULL;

CREATE TABLE assessment.student_enrollments (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id          UUID        NOT NULL REFERENCES assessment.students(id),
    section_offering_id UUID        NOT NULL REFERENCES curriculum.section_offerings(id),
    enrollment_date     DATE        NOT NULL DEFAULT CURRENT_DATE,
    status              VARCHAR(20) NOT NULL DEFAULT 'ENROLLED',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_enrollment         UNIQUE (student_id, section_offering_id),
    CONSTRAINT chk_enrollment_status CHECK (status IN ('ENROLLED','DROPPED','COMPLETED'))
);

CREATE INDEX idx_enrollment_student  ON assessment.student_enrollments(student_id, status);
CREATE INDEX idx_enrollment_offering ON assessment.student_enrollments(section_offering_id, status);

CREATE TABLE assessment.assessments (
    id                  UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID           NOT NULL REFERENCES org.organizations(id),
    section_offering_id UUID           NOT NULL REFERENCES curriculum.section_offerings(id),
    assessment_type_id  UUID           NOT NULL REFERENCES config.assessment_types(id),
    name                VARCHAR(200)   NOT NULL,
    total_marks         DECIMAL(6,2)   NOT NULL,
    weightage_percent   DECIMAL(5,2)   NOT NULL,
    status              VARCHAR(30)    NOT NULL DEFAULT 'CONFIGURED',
    created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_assessment_status CHECK (status IN ('CONFIGURED','MARKS_OPEN','PENDING_APPROVAL','PUBLISHED','LOCKED')),
    CONSTRAINT chk_total_marks       CHECK (total_marks > 0),
    CONSTRAINT chk_weightage         CHECK (weightage_percent > 0 AND weightage_percent <= 100)
);

CREATE INDEX idx_assessments_offering ON assessment.assessments(section_offering_id, status);

CREATE TABLE assessment.assessment_co_weights (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id       UUID          NOT NULL REFERENCES assessment.assessments(id),
    course_outcome_id   UUID          NOT NULL REFERENCES obe.course_outcomes(id),
    contribution_percent DECIMAL(5,2) NOT NULL,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_assessment_co     UNIQUE (assessment_id, course_outcome_id),
    CONSTRAINT chk_contribution     CHECK (contribution_percent > 0 AND contribution_percent <= 100)
);

CREATE INDEX idx_acw_assessment ON assessment.assessment_co_weights(assessment_id);
CREATE INDEX idx_acw_co         ON assessment.assessment_co_weights(course_outcome_id);

CREATE TABLE assessment.student_marks (
    id                     UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id          UUID          NOT NULL REFERENCES assessment.assessments(id),
    student_enrollment_id  UUID          NOT NULL REFERENCES assessment.student_enrollments(id),
    marks_obtained         DECIMAL(6,2),
    is_absent              BOOLEAN       NOT NULL DEFAULT FALSE,
    entered_by_user_id     UUID          NOT NULL REFERENCES iam.users(id),
    entered_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    last_updated_by_user_id UUID         REFERENCES iam.users(id),
    last_updated_at        TIMESTAMPTZ,
    CONSTRAINT uq_student_mark      UNIQUE (assessment_id, student_enrollment_id),
    CONSTRAINT chk_mark_or_absent   CHECK (is_absent = TRUE OR marks_obtained IS NOT NULL),
    CONSTRAINT chk_marks_non_negative CHECK (marks_obtained IS NULL OR marks_obtained >= 0)
);

CREATE INDEX idx_marks_assessment  ON assessment.student_marks(assessment_id);
CREATE INDEX idx_marks_enrollment  ON assessment.student_marks(student_enrollment_id);

CREATE TABLE assessment.result_publications (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    section_offering_id     UUID        NOT NULL UNIQUE REFERENCES curriculum.section_offerings(id),
    status                  VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
    submitted_by_user_id    UUID        REFERENCES iam.users(id),
    submitted_at            TIMESTAMPTZ,
    ml_approved_by_user_id  UUID        REFERENCES iam.users(id),
    ml_approved_at          TIMESTAMPTZ,
    ml_rejection_comment    TEXT,
    pc_approved_by_user_id  UUID        REFERENCES iam.users(id),
    pc_approved_at          TIMESTAMPTZ,
    pc_rejection_comment    TEXT,
    published_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_result_status CHECK (status IN ('DRAFT','SUBMITTED','ML_APPROVED','PC_APPROVED','PUBLISHED','LOCKED'))
);

-- ============================================================
-- ATTAINMENT SCHEMA
-- ============================================================

CREATE TABLE attainment.attainment_configurations (
    id                      UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID          NOT NULL REFERENCES org.organizations(id),
    section_offering_id     UUID          NOT NULL UNIQUE REFERENCES curriculum.section_offerings(id),
    co_threshold_percent    DECIMAL(5,2)  NOT NULL,
    course_threshold_percent DECIMAL(5,2) NOT NULL,
    po_threshold_percent    DECIMAL(5,2)  NOT NULL,
    direct_method_weight    DECIMAL(5,2)  NOT NULL DEFAULT 100.00,
    indirect_method_weight  DECIMAL(5,2)  NOT NULL DEFAULT 0.00,
    created_by_user_id      UUID          REFERENCES iam.users(id),
    created_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_method_weights CHECK (direct_method_weight + indirect_method_weight = 100),
    CONSTRAINT chk_co_threshold    CHECK (co_threshold_percent BETWEEN 0 AND 100),
    CONSTRAINT chk_course_threshold CHECK (course_threshold_percent BETWEEN 0 AND 100),
    CONSTRAINT chk_po_threshold    CHECK (po_threshold_percent BETWEEN 0 AND 100)
);

CREATE TABLE attainment.attainment_runs (
    id                           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id              UUID        NOT NULL REFERENCES org.organizations(id),
    section_offering_id          UUID        NOT NULL REFERENCES curriculum.section_offerings(id),
    attainment_configuration_id  UUID        NOT NULL REFERENCES attainment.attainment_configurations(id),
    run_number                   SMALLINT    NOT NULL DEFAULT 1,
    co_po_mapping_snapshot       JSONB       NOT NULL DEFAULT '{}',
    assessment_weight_snapshot   JSONB       NOT NULL DEFAULT '{}',
    formula_type                 VARCHAR(30) NOT NULL DEFAULT 'DIRECT',
    status                       VARCHAR(20) NOT NULL DEFAULT 'INITIATED',
    initiated_by_user_id         UUID        REFERENCES iam.users(id),
    initiated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    calculated_at                TIMESTAMPTZ,
    reviewed_by_user_id          UUID        REFERENCES iam.users(id),
    published_by_user_id         UUID        REFERENCES iam.users(id),
    published_at                 TIMESTAMPTZ,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_run_number     UNIQUE (section_offering_id, run_number),
    CONSTRAINT chk_run_status    CHECK (status IN ('INITIATED','CALCULATED','REVIEWED','PUBLISHED')),
    CONSTRAINT chk_formula_type  CHECK (formula_type IN ('DIRECT','DIRECT_INDIRECT_SPLIT'))
);

CREATE INDEX idx_runs_offering ON attainment.attainment_runs(section_offering_id, status);

CREATE TABLE attainment.co_attainment_results (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    attainment_run_id   UUID          NOT NULL REFERENCES attainment.attainment_runs(id),
    course_outcome_id   UUID          NOT NULL REFERENCES obe.course_outcomes(id),
    total_students      SMALLINT      NOT NULL,
    students_attempted  SMALLINT      NOT NULL,
    students_attained   SMALLINT      NOT NULL,
    attainment_percent  DECIMAL(6,3)  NOT NULL,
    is_threshold_met    BOOLEAN       NOT NULL,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_co_attainment UNIQUE (attainment_run_id, course_outcome_id)
);

CREATE INDEX idx_co_result_run ON attainment.co_attainment_results(attainment_run_id);
CREATE INDEX idx_co_result_co  ON attainment.co_attainment_results(course_outcome_id);

CREATE TABLE attainment.course_attainment_results (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    attainment_run_id   UUID          NOT NULL UNIQUE REFERENCES attainment.attainment_runs(id),
    attainment_percent  DECIMAL(6,3)  NOT NULL,
    is_threshold_met    BOOLEAN       NOT NULL,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE TABLE attainment.po_attainment_results (
    id                       UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    attainment_run_id        UUID          NOT NULL REFERENCES attainment.attainment_runs(id),
    program_outcome_id       UUID          NOT NULL REFERENCES obe.program_outcomes(id),
    weighted_co_contribution DECIMAL(6,3)  NOT NULL,
    attainment_percent       DECIMAL(6,3)  NOT NULL,
    is_threshold_met         BOOLEAN       NOT NULL,
    created_at               TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_po_attainment UNIQUE (attainment_run_id, program_outcome_id)
);

CREATE INDEX idx_po_result_run ON attainment.po_attainment_results(attainment_run_id);
CREATE INDEX idx_po_result_po  ON attainment.po_attainment_results(program_outcome_id);

-- ============================================================
-- APPROVAL SCHEMA
-- ============================================================

CREATE TABLE approval.workflow_definitions (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID         REFERENCES org.organizations(id),
    name             VARCHAR(100) NOT NULL,
    description      TEXT,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_workflow_name UNIQUE (organization_id, name)
);

CREATE TABLE approval.workflow_step_definitions (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_definition_id  UUID         NOT NULL REFERENCES approval.workflow_definitions(id),
    step_order              SMALLINT     NOT NULL,
    step_name               VARCHAR(100) NOT NULL,
    required_role_id        UUID         NOT NULL REFERENCES iam.roles(id),
    required_scope_type     VARCHAR(20)  NOT NULL DEFAULT 'PROGRAM',
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_step_order UNIQUE (workflow_definition_id, step_order)
);

CREATE INDEX idx_wsd_workflow ON approval.workflow_step_definitions(workflow_definition_id);

CREATE TABLE approval.approval_requests (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID        NOT NULL REFERENCES org.organizations(id),
    workflow_definition_id  UUID        NOT NULL REFERENCES approval.workflow_definitions(id),
    entity_type             VARCHAR(50) NOT NULL,
    entity_id               UUID        NOT NULL,
    current_step_order      SMALLINT    NOT NULL DEFAULT 1,
    status                  VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    initiated_by_user_id    UUID        REFERENCES iam.users(id),
    initiated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_request_status CHECK (status IN ('PENDING','UNDER_REVIEW','APPROVED','REJECTED'))
);

CREATE INDEX idx_approval_entity ON approval.approval_requests(entity_type, entity_id);
CREATE INDEX idx_approval_status ON approval.approval_requests(status)
    WHERE status IN ('PENDING','UNDER_REVIEW');

CREATE TABLE approval.approval_step_records (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_request_id  UUID        NOT NULL REFERENCES approval.approval_requests(id),
    step_order           SMALLINT    NOT NULL,
    action               VARCHAR(30) NOT NULL,
    approver_user_id     UUID        NOT NULL REFERENCES iam.users(id),
    comments             TEXT,
    acted_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_step_action CHECK (action IN ('APPROVED','REJECTED','REVISION_REQUESTED'))
);

CREATE INDEX idx_step_records_request ON approval.approval_step_records(approval_request_id);

CREATE TABLE approval.delegate_approvers (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID        NOT NULL REFERENCES org.organizations(id),
    delegator_user_id       UUID        NOT NULL REFERENCES iam.users(id),
    delegate_user_id        UUID        NOT NULL REFERENCES iam.users(id),
    workflow_definition_id  UUID        REFERENCES approval.workflow_definitions(id),
    scope_id                UUID,
    valid_from              TIMESTAMPTZ NOT NULL,
    valid_to                TIMESTAMPTZ NOT NULL,
    is_active               BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_delegate_dates CHECK (valid_to > valid_from)
);

-- ============================================================
-- NOTIFICATION SCHEMA
-- ============================================================

CREATE TABLE notification.notification_templates (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID         REFERENCES org.organizations(id),
    event_type       VARCHAR(100) NOT NULL,
    channel          VARCHAR(20)  NOT NULL,
    subject_template VARCHAR(500),
    body_template    TEXT         NOT NULL,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_template          UNIQUE (organization_id, event_type, channel),
    CONSTRAINT chk_template_channel CHECK (channel IN ('IN_APP','EMAIL'))
);

CREATE TABLE notification.notification_queue (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID         NOT NULL REFERENCES org.organizations(id),
    recipient_user_id   UUID         NOT NULL REFERENCES iam.users(id),
    event_type          VARCHAR(100) NOT NULL,
    channel             VARCHAR(20)  NOT NULL DEFAULT 'EMAIL',
    subject             VARCHAR(500),
    body                TEXT         NOT NULL,
    status              VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
    retry_count         SMALLINT     NOT NULL DEFAULT 0,
    scheduled_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    sent_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_queue_status  CHECK (status IN ('PENDING','SENT','FAILED'))
);

CREATE INDEX idx_notif_queue_pending
    ON notification.notification_queue(status, scheduled_at)
    WHERE status = 'PENDING';

CREATE TABLE notification.in_app_notifications (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID         NOT NULL REFERENCES org.organizations(id),
    recipient_user_id   UUID         NOT NULL REFERENCES iam.users(id),
    title               VARCHAR(300) NOT NULL,
    body                TEXT         NOT NULL,
    entity_type         VARCHAR(50),
    entity_id           UUID,
    is_read             BOOLEAN      NOT NULL DEFAULT FALSE,
    read_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_in_app_inbox
    ON notification.in_app_notifications(recipient_user_id, is_read, created_at);

-- ============================================================
-- EVENTS SCHEMA — Transactional outbox
-- ============================================================

CREATE TABLE events.domain_events (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      VARCHAR(150) NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    organization_id UUID,
    aggregate_type  VARCHAR(100) NOT NULL,
    aggregate_id    UUID,
    payload         JSONB        NOT NULL DEFAULT '{}',
    correlation_id  VARCHAR(100),
    status          VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
    processed_at    TIMESTAMPTZ,
    retry_count     SMALLINT     NOT NULL DEFAULT 0,
    last_error      TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_event_status CHECK (status IN ('PENDING','PROCESSED','FAILED'))
);

CREATE INDEX idx_outbox_pending
    ON events.domain_events(status, occurred_at)
    WHERE status = 'PENDING';

CREATE INDEX idx_outbox_entity
    ON events.domain_events(aggregate_type, aggregate_id);

-- ============================================================
-- AUDIT SCHEMA — Append-only, partitioned by time
-- ============================================================

CREATE TABLE audit.audit_events (
    id                    UUID         NOT NULL DEFAULT gen_random_uuid(),
    organization_id       UUID,
    actor_user_id         UUID,
    actor_email           VARCHAR(255),
    actor_role_snapshot   VARCHAR(255),
    action                VARCHAR(50)  NOT NULL,
    entity_type           VARCHAR(100) NOT NULL,
    entity_id             UUID,
    entity_display_name   VARCHAR(500),
    old_value             JSONB,
    new_value             JSONB,
    metadata              JSONB,
    ip_address            INET,
    user_agent            VARCHAR(500),
    occurred_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (occurred_at);

-- Quarterly partitions 2025–2027
CREATE TABLE audit.audit_events_2025_q1
    PARTITION OF audit.audit_events
    FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');

CREATE TABLE audit.audit_events_2025_q2
    PARTITION OF audit.audit_events
    FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');

CREATE TABLE audit.audit_events_2025_q3
    PARTITION OF audit.audit_events
    FOR VALUES FROM ('2025-07-01') TO ('2025-10-01');

CREATE TABLE audit.audit_events_2025_q4
    PARTITION OF audit.audit_events
    FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');

CREATE TABLE audit.audit_events_2026_q1
    PARTITION OF audit.audit_events
    FOR VALUES FROM ('2026-01-01') TO ('2026-04-01');

CREATE TABLE audit.audit_events_2026_q2
    PARTITION OF audit.audit_events
    FOR VALUES FROM ('2026-04-01') TO ('2026-07-01');

CREATE TABLE audit.audit_events_2026_q3
    PARTITION OF audit.audit_events
    FOR VALUES FROM ('2026-07-01') TO ('2026-10-01');

CREATE TABLE audit.audit_events_2026_q4
    PARTITION OF audit.audit_events
    FOR VALUES FROM ('2026-10-01') TO ('2027-01-01');

CREATE TABLE audit.audit_events_2027_q1
    PARTITION OF audit.audit_events
    FOR VALUES FROM ('2027-01-01') TO ('2027-04-01');

CREATE TABLE audit.audit_events_default
    PARTITION OF audit.audit_events DEFAULT;

-- Indexes on the parent (propagate to all partitions)
CREATE INDEX idx_audit_entity   ON audit.audit_events(organization_id, entity_type, entity_id);
CREATE INDEX idx_audit_actor    ON audit.audit_events(organization_id, actor_user_id, occurred_at);
CREATE INDEX idx_audit_time     ON audit.audit_events(organization_id, occurred_at);
CREATE INDEX idx_audit_oldval   ON audit.audit_events USING GIN (old_value);
CREATE INDEX idx_audit_newval   ON audit.audit_events USING GIN (new_value);

-- ============================================================
-- ACCREDITATION SCHEMA
-- ============================================================

CREATE TABLE accreditation.accreditation_bodies (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID         REFERENCES org.organizations(id),
    name              VARCHAR(100) NOT NULL,
    description       TEXT,
    po_template_count SMALLINT,
    is_active         BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE accreditation.accreditation_cycles (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID         NOT NULL REFERENCES org.organizations(id),
    accreditation_body_id   UUID         NOT NULL REFERENCES accreditation.accreditation_bodies(id),
    program_id              UUID         NOT NULL REFERENCES org.programs(id),
    cycle_name              VARCHAR(100) NOT NULL,
    review_start_date       DATE         NOT NULL,
    review_end_date         DATE         NOT NULL,
    status                  VARCHAR(20)  NOT NULL DEFAULT 'UPCOMING',
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_cycle_dates  CHECK (review_end_date > review_start_date),
    CONSTRAINT chk_cycle_status CHECK (status IN ('UPCOMING','IN_PROGRESS','SUBMITTED','COMPLETED'))
);

CREATE INDEX idx_cycles_program ON accreditation.accreditation_cycles(program_id);

CREATE TABLE accreditation.accreditation_reports (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    accreditation_cycle_id  UUID         NOT NULL REFERENCES accreditation.accreditation_cycles(id),
    report_type             VARCHAR(100) NOT NULL,
    export_format           VARCHAR(10)  NOT NULL DEFAULT 'PDF',
    file_key                VARCHAR(500),
    status                  VARCHAR(20)  NOT NULL DEFAULT 'DRAFT',
    generated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    generated_by_user_id    UUID         REFERENCES iam.users(id),
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_report_status CHECK (status IN ('DRAFT','SUBMITTED','FINAL')),
    CONSTRAINT chk_report_format CHECK (export_format IN ('PDF','EXCEL','CSV'))
);

CREATE INDEX idx_accred_reports_cycle ON accreditation.accreditation_reports(accreditation_cycle_id);

-- ============================================================
-- REPORTING SCHEMA
-- ============================================================

CREATE TABLE reporting.report_definitions (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID         REFERENCES org.organizations(id),
    name             VARCHAR(200) NOT NULL,
    category         VARCHAR(50)  NOT NULL,
    description      TEXT,
    template_config  JSONB,
    is_system_report BOOLEAN      NOT NULL DEFAULT FALSE,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_report_category CHECK (
        category IN ('CURRICULUM','CO','PO','MAPPING','ASSESSMENT','ATTAINMENT','FACULTY','BATCH','ACCREDITATION')
    )
);

CREATE TABLE reporting.report_runs (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID         NOT NULL REFERENCES org.organizations(id),
    report_definition_id    UUID         NOT NULL REFERENCES reporting.report_definitions(id),
    requested_by_user_id    UUID         NOT NULL REFERENCES iam.users(id),
    parameters              JSONB        NOT NULL DEFAULT '{}',
    export_format           VARCHAR(10)  NOT NULL DEFAULT 'PDF',
    status                  VARCHAR(20)  NOT NULL DEFAULT 'QUEUED',
    file_key                VARCHAR(500),
    error_message           TEXT,
    queued_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_run_status  CHECK (status IN ('QUEUED','PROCESSING','COMPLETED','FAILED')),
    CONSTRAINT chk_run_format  CHECK (export_format IN ('PDF','EXCEL','CSV'))
);

CREATE INDEX idx_report_runs_user ON reporting.report_runs(organization_id, requested_by_user_id, queued_at);

-- ============================================================
-- SEED DATA — System roles, permissions, reference data
-- ============================================================

-- Insert system roles (no organization_id = platform-level)
INSERT INTO iam.roles (name, description, is_system_role, is_active) VALUES
    ('Super Admin',         'Platform-level administrator with global access',       TRUE, TRUE),
    ('Program Coordinator', 'Program-level administrator managing curriculum and OBE', TRUE, TRUE),
    ('Module Leader',       'Course-level authority for CO governance and mark approval', TRUE, TRUE),
    ('Section Teacher',     'Course delivery: creates COs, enters marks',             TRUE, TRUE),
    ('Student',             'Self-service read-only access to own academic data',    TRUE, TRUE);

-- Insert system-tier permissions
INSERT INTO iam.permissions (code, description, tier) VALUES
    ('system.organization.configure', 'Edit organization settings',           'SYSTEM'),
    ('system.audit.read',             'Read all audit logs',                  'SYSTEM'),
    ('system.roles.create',           'Create new roles',                     'SYSTEM'),
    ('system.roles.delete',           'Delete non-system roles',              'SYSTEM'),
    ('system.permissions.grant',      'Grant permissions to roles',           'SYSTEM'),
    ('system.permissions.revoke',     'Revoke permissions from roles',        'SYSTEM');

-- Insert domain-tier permissions (abbreviated — full list via migration seed script)
INSERT INTO iam.permissions (code, description, tier) VALUES
    ('department.create',             'Create departments',                   'DOMAIN'),
    ('department.read',               'View departments',                     'DOMAIN'),
    ('department.update',             'Edit departments',                     'DOMAIN'),
    ('department.archive',            'Archive departments',                  'DOMAIN'),
    ('program.create',                'Create programs',                      'DOMAIN'),
    ('program.read',                  'View programs',                        'DOMAIN'),
    ('program.update',                'Edit programs',                        'DOMAIN'),
    ('program.archive',               'Archive programs',                     'DOMAIN'),
    ('user.create',                   'Create user accounts',                 'DOMAIN'),
    ('user.read',                     'View user profiles',                   'DOMAIN'),
    ('user.update',                   'Edit user information',                'DOMAIN'),
    ('user.deactivate',               'Deactivate users',                     'DOMAIN'),
    ('user.password.reset',           'Reset user passwords',                 'DOMAIN'),
    ('user.role.assign',              'Assign roles to users',                'DOMAIN'),
    ('user.role.revoke',              'Revoke role assignments',              'DOMAIN'),
    ('curriculum.create',             'Create curricula',                     'DOMAIN'),
    ('curriculum.read',               'View curricula',                       'DOMAIN'),
    ('curriculum.update',             'Edit curricula',                       'DOMAIN'),
    ('curriculum.archive',            'Archive curricula',                    'DOMAIN'),
    ('curriculum.version',            'Version a curriculum',                 'DOMAIN'),
    ('course.create',                 'Create courses',                       'DOMAIN'),
    ('course.read',                   'View courses',                         'DOMAIN'),
    ('course.update',                 'Edit courses',                         'DOMAIN'),
    ('course.archive',                'Archive courses',                      'DOMAIN'),
    ('course.prerequisite.manage',    'Manage course prerequisites',          'DOMAIN'),
    ('batch.create',                  'Create batches',                       'DOMAIN'),
    ('batch.read',                    'View batches',                         'DOMAIN'),
    ('batch.update',                  'Edit batches',                         'DOMAIN'),
    ('po.create',                     'Create program outcomes',              'DOMAIN'),
    ('po.read',                       'View program outcomes',                'DOMAIN'),
    ('po.update',                     'Edit program outcomes',                'DOMAIN'),
    ('po.archive',                    'Archive program outcomes',             'DOMAIN'),
    ('co.create',                     'Create course outcomes',               'DOMAIN'),
    ('co.read',                       'View course outcomes',                 'DOMAIN'),
    ('co.update',                     'Edit course outcomes',                 'DOMAIN'),
    ('co.submit',                     'Submit CO for approval',               'DOMAIN'),
    ('co.approve',                    'Approve CO submission',                'DOMAIN'),
    ('co.reject',                     'Reject CO submission',                 'DOMAIN'),
    ('co.publish',                    'Publish approved CO',                  'DOMAIN'),
    ('mapping.co_po.create',          'Create CO-PO mapping set',             'DOMAIN'),
    ('mapping.co_po.read',            'View CO-PO mapping',                   'DOMAIN'),
    ('mapping.co_po.update',          'Edit CO-PO mapping entries',           'DOMAIN'),
    ('mapping.co_po.publish',         'Publish CO-PO mapping',               'DOMAIN'),
    ('mapping.co_cp.manage',          'Manage CO-CP mappings',                'DOMAIN'),
    ('mapping.co_cp.approve',         'Approve CO-CP mappings',              'DOMAIN'),
    ('mapping.co_ca.manage',          'Manage CO-CA mappings',                'DOMAIN'),
    ('mapping.co_ca.approve',         'Approve CO-CA mappings',              'DOMAIN'),
    ('mapping.co_kp.manage',          'Manage CO-KP mappings',                'DOMAIN'),
    ('mapping.co_kp.approve',         'Approve CO-KP mappings',              'DOMAIN'),
    ('assessment.configure',          'Configure assessments',                'DOMAIN'),
    ('assessment.read',               'View assessments',                     'DOMAIN'),
    ('assessment.publish_config',     'Publish assessment configuration',     'DOMAIN'),
    ('marks.enter',                   'Enter student marks',                  'DOMAIN'),
    ('marks.update',                  'Update student marks',                 'DOMAIN'),
    ('marks.read.section',            'View marks for assigned section',      'DOMAIN'),
    ('marks.read.all',                'View all marks within scope',          'DOMAIN'),
    ('result.submit',                 'Submit results for approval',          'DOMAIN'),
    ('result.approve.ml',             'Module Leader result approval',        'DOMAIN'),
    ('result.reject.ml',              'Module Leader result rejection',       'DOMAIN'),
    ('result.approve.pc',             'Program Coordinator result approval',  'DOMAIN'),
    ('result.reject.pc',              'Program Coordinator result rejection', 'DOMAIN'),
    ('result.publish',                'Publish results',                      'DOMAIN'),
    ('result.read.section',           'View results for assigned section',    'DOMAIN'),
    ('result.read.all',               'View all results within scope',        'DOMAIN'),
    ('attainment.configure',          'Configure attainment thresholds',      'DOMAIN'),
    ('attainment.initiate',           'Initiate attainment calculation',      'DOMAIN'),
    ('attainment.review',             'Review attainment results',            'DOMAIN'),
    ('attainment.publish',            'Publish attainment run',               'DOMAIN'),
    ('attainment.read',               'View attainment results',              'DOMAIN'),
    ('report.curriculum.generate',    'Generate curriculum reports',          'DOMAIN'),
    ('report.co.generate',            'Generate CO reports',                  'DOMAIN'),
    ('report.po.generate',            'Generate PO reports',                  'DOMAIN'),
    ('report.attainment.generate',    'Generate attainment reports',          'DOMAIN'),
    ('report.accreditation.generate', 'Generate accreditation reports',       'DOMAIN'),
    ('report.faculty.generate',       'Generate faculty reports',             'DOMAIN'),
    ('report.batch.generate',         'Generate batch reports',               'DOMAIN'),
    ('report.assessment.generate',    'Generate assessment reports',          'DOMAIN'),
    ('report.export',                 'Export/download generated reports',    'DOMAIN'),
    ('accreditation.body.manage',     'Manage accreditation bodies',          'DOMAIN'),
    ('accreditation.cycle.create',    'Create accreditation cycles',          'DOMAIN'),
    ('accreditation.cycle.manage',    'Manage accreditation cycles',          'DOMAIN'),
    ('accreditation.report.generate', 'Generate accreditation submissions',   'DOMAIN');

-- Student-tier permissions
INSERT INTO iam.permissions (code, description, tier) VALUES
    ('student.profile.read.own',      'View own student profile',             'STUDENT'),
    ('student.curriculum.read.own',   'View own curriculum',                  'STUDENT'),
    ('student.course.read.own',       'View enrolled courses',                'STUDENT'),
    ('student.result.read.own',       'View own results',                     'STUDENT'),
    ('student.marks.read.own',        'View own marks',                       'STUDENT'),
    ('student.co.read.own',           'View COs for enrolled courses',        'STUDENT'),
    ('student.po.read.own',           'View program outcomes',                'STUDENT');

-- Default bloom levels seed (Cognitive domain)
-- Full seeding done via scripts/seed_reference_data.py

-- Approval workflow definitions seed
INSERT INTO approval.workflow_definitions (name, description) VALUES
    ('CO_APPROVAL',             'Two-step CO approval: Module Leader review then Program Coordinator publish'),
    ('ATTAINMENT_PUBLICATION',  'One-step attainment review by Program Coordinator');

-- ============================================================
-- END OF SCHEMA DDL
-- ============================================================
