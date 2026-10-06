"""F01: create users table

Revision ID: 0001
Revises:
Create Date: 2026-10-01

NOTE (coordination required before merge): this migration is currently a
root migration (down_revision=None). PR #8 (F02/F13/F14) also adds a root
migration. Only one root can exist once both land -- per
docs/ARCHITECTURE.md, other modules' tables depend on `users` existing
(F02=F01, F13=F01 in docs/FEATURE_BOUNDARIES.md), so this migration should
become the actual root and PR #8's first migration should set
down_revision="0001" once this merges. Whoever merges second should do
that rebase; don't leave two Alembic heads.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="job_seeker",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
