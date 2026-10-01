"""Create F14 resume sharing and peer feedback.

Revision ID: 20261001_0003
Revises: 20261001_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261001_0003"
down_revision: str | None = "20261001_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_resume_versions_id_user",
        "resume_versions",
        ["id", "user_id"],
    )

    op.create_table(
        "resume_shares",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["resume_version_id", "owner_user_id"],
            ["resume_versions.id", "resume_versions.user_id"],
            name="fk_resume_shares_resume_owner",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "resume_version_id",
            name="uq_resume_shares_id_version",
        ),
        sa.UniqueConstraint(
            "token_digest",
            name="uq_resume_shares_token_digest",
        ),
    )
    op.create_index(
        op.f("ix_resume_shares_owner_user_id"),
        "resume_shares",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_resume_shares_resume_version_id"),
        "resume_shares",
        ["resume_version_id"],
        unique=False,
    )

    op.create_table(
        "peer_review_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("share_id", sa.Uuid(), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["share_id", "resume_version_id"],
            ["resume_shares.id", "resume_shares.resume_version_id"],
            name="fk_peer_feedback_share_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_peer_review_feedback_reviewer_user_id"),
        "peer_review_feedback",
        ["reviewer_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peer_review_feedback_share_id"),
        "peer_review_feedback",
        ["share_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_peer_review_feedback_share_id"),
        table_name="peer_review_feedback",
    )
    op.drop_index(
        op.f("ix_peer_review_feedback_reviewer_user_id"),
        table_name="peer_review_feedback",
    )
    op.drop_table("peer_review_feedback")
    op.drop_index(
        op.f("ix_resume_shares_resume_version_id"),
        table_name="resume_shares",
    )
    op.drop_index(
        op.f("ix_resume_shares_owner_user_id"),
        table_name="resume_shares",
    )
    op.drop_table("resume_shares")
    op.drop_constraint(
        "uq_resume_versions_id_user",
        "resume_versions",
        type_="unique",
    )
