import sqlalchemy as sa
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, SmallInteger, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from app.core.database import Base

# All relationships use lazy="raise" to prevent implicit I/O in async context.
# Every query that needs related objects must use explicit selectinload()/joinedload().


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_iam_users_email"),
        Index(
            "uq_iam_users_linked_student_id",
            "linked_student_id",
            unique=True,
            postgresql_where=sa.text("linked_student_id IS NOT NULL"),
        ),
        {"schema": "iam"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    title = Column(String(20), nullable=True)
    first_name = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    employee_id = Column(String(100), nullable=False)
    faculty_type = Column(String(50), nullable=True)
    nid = Column(String(50), nullable=True)
    department_id = Column(PGUUID(as_uuid=True), nullable=True)  # FK to org.departments — no ORM rel to avoid cross-schema coupling
    designation = Column(String(100), nullable=True)
    contact_number = Column(String(50), nullable=True)
    qualification = Column(String(255), nullable=True)
    experience_years = Column(SmallInteger, nullable=True)
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    linked_student_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )

    credential = relationship("PasswordCredential", back_populates="user", uselist=False, lazy="raise")
    role_assignments = relationship(
        "UserRoleAssignment",
        foreign_keys="UserRoleAssignment.user_id",
        back_populates="user",
        lazy="raise",
    )


class PasswordCredential(Base):
    __tablename__ = "password_credentials"
    __table_args__ = {"schema": "iam"}

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    hashed_password = Column(String(255), nullable=False)
    must_change_password = Column(Boolean, nullable=False, server_default="false")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )

    user = relationship("User", back_populates="credential", lazy="raise")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "iam"}

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_iam_roles_org_name"),
        {"schema": "iam"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    is_system_role = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    permissions = relationship(
        "Permission",
        secondary="iam.role_permissions",
        lazy="raise",
    )
    user_assignments = relationship("UserRoleAssignment", back_populates="role", lazy="raise")


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "iam"}

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    code = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    tier = Column(String(20), nullable=False, server_default="SYSTEM")  # SYSTEM | CUSTOM
    module = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = {"schema": "iam"}

    role_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("iam.roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("iam.permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"
    __table_args__ = {"schema": "iam"}

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("iam.roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    scope_type = Column(String(20), nullable=False)  # GLOBAL | PROGRAM
    scope_id = Column(PGUUID(as_uuid=True), nullable=True)  # program_id when PROGRAM scope
    assigned_by = Column(
        PGUUID(as_uuid=True), ForeignKey("iam.users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    removed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="role_assignments", lazy="raise")
    role = relationship("Role", back_populates="user_assignments", lazy="raise")
