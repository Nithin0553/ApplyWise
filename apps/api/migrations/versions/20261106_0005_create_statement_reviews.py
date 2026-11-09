"""Create F09 statement review decisions and immutable audit events.

Revision ID: 20261106_0005
Revises: 20261006_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261106_0005"
down_revision: str | None = "20261006_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "statement_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("statement_id", sa.Uuid(), nullable=False),
        sa.Column("verification_revision", sa.String(length=128), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "statement_id", name="uq_statement_reviews_user_statement"),
        sa.UniqueConstraint("id", "user_id", name="uq_statement_reviews_id_user"),
        sa.CheckConstraint("event_count > 0", name="ck_statement_reviews_positive_event_count"),
        sa.CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')", name="ck_statement_review_decision"
        ),
    )
    op.create_index("ix_statement_reviews_user_id", "statement_reviews", ["user_id"])
    op.create_index(
        "ix_statement_reviews_statement_id", "statement_reviews", ["statement_id"]
    )

    op.create_table(
        "statement_review_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("verification_revision", sa.String(length=128), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["review_id", "user_id"],
            ["statement_reviews.id", "statement_reviews.user_id"],
            name="fk_statement_review_event_owned_review",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("review_id", "sequence", name="uq_statement_review_event_sequence"),
        sa.CheckConstraint("sequence > 0", name="ck_statement_review_event_positive_sequence"),
        sa.CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')", name="ck_statement_review_event_decision"
        ),
    )
    op.create_index(
        "ix_statement_review_events_review_id", "statement_review_events", ["review_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_statement_review_events_review_id", table_name="statement_review_events")
    op.drop_table("statement_review_events")
    op.drop_index("ix_statement_reviews_statement_id", table_name="statement_reviews")
    op.drop_index("ix_statement_reviews_user_id", table_name="statement_reviews")
    op.drop_table("statement_reviews")
