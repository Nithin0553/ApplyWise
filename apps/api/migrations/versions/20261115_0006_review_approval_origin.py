"""Record the source statement of F09 carry-forward approvals.

Revision ID: 20261115_0006
Revises: 20261109_0005

The new field is nullable: historic events have unknown origin, and direct
user-clicked decisions leave it null. It is deliberately not a foreign key,
because F08 source statements may be withdrawn while the audit must survive.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261115_0006"
down_revision: str | None = "20261109_0005"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "statement_review_events",
        sa.Column("carried_from_statement_id", sa.Uuid(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("statement_review_events", "carried_from_statement_id")
