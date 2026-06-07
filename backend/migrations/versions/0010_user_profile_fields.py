"""Add user profile fields (title, name parts, faculty_type, nid, dept, designation, contact, qualification, experience)

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as pg

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("title", sa.String(20), nullable=True), schema="iam")
    op.add_column("users", sa.Column("first_name", sa.String(100), nullable=True), schema="iam")
    op.add_column("users", sa.Column("middle_name", sa.String(100), nullable=True), schema="iam")
    op.add_column("users", sa.Column("last_name", sa.String(100), nullable=True), schema="iam")
    op.add_column("users", sa.Column("faculty_type", sa.String(50), nullable=True), schema="iam")
    op.add_column("users", sa.Column("nid", sa.String(50), nullable=True), schema="iam")
    op.add_column("users", sa.Column("department_id", pg(as_uuid=True), nullable=True), schema="iam")
    op.add_column("users", sa.Column("designation", sa.String(100), nullable=True), schema="iam")
    op.add_column("users", sa.Column("contact_number", sa.String(50), nullable=True), schema="iam")
    op.add_column("users", sa.Column("qualification", sa.String(255), nullable=True), schema="iam")
    op.add_column("users", sa.Column("experience_years", sa.SmallInteger(), nullable=True), schema="iam")

    op.create_foreign_key(
        "fk_iam_users_department_id",
        "users",
        "departments",
        ["department_id"],
        ["id"],
        source_schema="iam",
        referent_schema="org",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_iam_users_department_id", "users", schema="iam", type_="foreignkey")
    op.drop_column("users", "experience_years", schema="iam")
    op.drop_column("users", "qualification", schema="iam")
    op.drop_column("users", "contact_number", schema="iam")
    op.drop_column("users", "designation", schema="iam")
    op.drop_column("users", "department_id", schema="iam")
    op.drop_column("users", "nid", schema="iam")
    op.drop_column("users", "faculty_type", schema="iam")
    op.drop_column("users", "last_name", schema="iam")
    op.drop_column("users", "middle_name", schema="iam")
    op.drop_column("users", "first_name", schema="iam")
    op.drop_column("users", "title", schema="iam")
