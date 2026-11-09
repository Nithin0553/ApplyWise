"""create verification statements

Only the claim is stored. Classification and revision are derived on read, so
there are deliberately no columns for them: a persisted verdict could disagree
with the evidence it was based on, and F09's invalidation rests on that never
happening.

Revision ID: 20261109_0005
Revises: 20261106_0005
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261109_0005"
down_revision: str | None = "20261106_0005"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "verification_statements",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("evidence_ids", sa.String(length=1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_verification_statements_user_id", "verification_statements", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_verification_statements_user_id", table_name="verification_statements"
    )
    op.drop_table("verification_statements")
