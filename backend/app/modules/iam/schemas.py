from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str  # plain str — login is a DB lookup, not a registration form
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequestBody(BaseModel):
    email: EmailStr


class PasswordResetConfirmBody(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


# ── User ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=20)
    faculty_type: str | None = Field(default=None, max_length=50)
    nid: str | None = Field(default=None, max_length=50)
    department_id: UUID | None = None
    designation: str | None = Field(default=None, max_length=100)
    contact_number: str | None = Field(default=None, max_length=50)
    qualification: str | None = Field(default=None, max_length=255)
    experience_years: int | None = Field(default=None, ge=0, le=99)
    password: str = Field(min_length=8)
    role_id: UUID
    scope_type: str = Field(pattern="^(GLOBAL|PROGRAM)$")
    scope_id: UUID | None = None


class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=20)
    faculty_type: str | None = Field(default=None, max_length=50)
    nid: str | None = Field(default=None, max_length=50)
    department_id: UUID | None = None
    designation: str | None = Field(default=None, max_length=100)
    contact_number: str | None = Field(default=None, max_length=50)
    qualification: str | None = Field(default=None, max_length=255)
    experience_years: int | None = Field(default=None, ge=0, le=99)


class RoleAssignRequest(BaseModel):
    role_id: UUID
    scope_type: str = Field(pattern="^(GLOBAL|PROGRAM)$")
    scope_id: UUID | None = None


class UserResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    full_name: str
    title: str | None
    first_name: str | None
    middle_name: str | None
    last_name: str | None
    faculty_type: str | None
    nid: str | None
    department_id: UUID | None
    designation: str | None
    contact_number: str | None
    qualification: str | None
    experience_years: int | None
    status: str
    linked_student_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserRoleAssignmentResponse(BaseModel):
    id: UUID
    role_id: UUID
    role_name: str
    scope_type: str
    scope_id: UUID | None
    assigned_at: datetime

    model_config = {"from_attributes": True}


class BulkCreateResult(BaseModel):
    created: list[UserResponse]
    errors: list[dict]


# ── Role ─────────────────────────────────────────────────────────────────────

class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_system_role: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PermissionResponse(BaseModel):
    id: UUID
    code: str
    description: str | None
    tier: str
    module: str

    model_config = {"from_attributes": True}


class AddPermissionRequest(BaseModel):
    permission_id: UUID


# ── Permission Manifest ───────────────────────────────────────────────────────

class ProgramScopeEntry(BaseModel):
    program_id: UUID
    role_name: str


class PermissionManifestResponse(BaseModel):
    user_id: UUID
    permissions: list[str]
    program_ids: list[UUID]
    role_names: list[str]
    is_super_admin: bool
