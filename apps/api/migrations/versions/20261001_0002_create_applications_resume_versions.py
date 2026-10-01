"""Create F13 applications and resume versions.

Revision ID: 20261001_0002
Revises: 20260921_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261001_0002"
down_revision: str | None = "20260921_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("role_title", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("job_url", sa.String(length=1000), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("applied_on", sa.Date(), nullable=True),
        sa.Column("next_action_on", sa.Date(), nullable=True),
        sa.Column("closed_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ("
            "'draft', 'applied', 'interviewing', 'offer', "
            "'accepted', 'rejected', 'withdrawn'"
            ")",
            name="ck_applications_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "user_id",
            name="uq_applications_id_user",
        ),
    )
    op.create_index(
        op.f("ix_applications_user_id"),
        "applications",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "resume_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "version_number > 0",
            name="ck_resume_versions_positive_version",
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "user_id"],
            ["applications.id", "applications.user_id"],
            name="fk_resume_versions_application_owner",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id",
            "version_number",
            name="uq_resume_versions_application_version",
        ),
    )
    op.create_index(
        op.f("ix_resume_versions_application_id"),
        "resume_versions",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_resume_versions_user_id"),
        "resume_versions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_resume_versions_user_id"), table_name="resume_versions")
    op.drop_index(op.f("ix_resume_versions_application_id"), table_name="resume_versions")
    op.drop_table("resume_versions")
    op.drop_index(op.f("ix_applications_user_id"), table_name="applications")
    op.drop_table("applications")
