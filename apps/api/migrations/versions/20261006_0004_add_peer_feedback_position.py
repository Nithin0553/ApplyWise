"""Add deterministic append position to F14 peer feedback.

Revision ID: 20261006_0004
Revises: 20261001_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261006_0004"
down_revision: str | None = "20261001_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add nullable first so existing installations can be backfilled before the
    # invariant is enforced.
    op.add_column(
        "peer_review_feedback",
        sa.Column("position", sa.Integer(), nullable=True),
    )

    feedback = sa.table(
        "peer_review_feedback",
        sa.column("id", sa.Uuid()),
        sa.column("share_id", sa.Uuid()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("position", sa.Integer()),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(feedback.c.id, feedback.c.share_id).order_by(
            feedback.c.share_id,
            feedback.c.created_at,
            feedback.c.id,
        )
    ).all()

    current_share = None
    position = 0
    for feedback_id, share_id in rows:
        if share_id != current_share:
            current_share = share_id
            position = 1
        else:
            position += 1
        bind.execute(
            feedback.update()
            .where(feedback.c.id == feedback_id)
            .values(position=position)
        )

    op.alter_column(
        "peer_review_feedback",
        "position",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_peer_feedback_share_position",
        "peer_review_feedback",
        ["share_id", "position"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_peer_feedback_share_position",
        "peer_review_feedback",
        type_="unique",
    )
    op.drop_column("peer_review_feedback", "position")
