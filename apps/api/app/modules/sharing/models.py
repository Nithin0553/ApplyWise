from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ResumeShareRecord(Base):
    __tablename__ = "resume_shares"
    __table_args__ = (
        ForeignKeyConstraint(
            ["resume_version_id", "owner_user_id"],
            ["resume_versions.id", "resume_versions.user_id"],
            name="fk_resume_shares_resume_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "id",
            "resume_version_id",
            name="uq_resume_shares_id_version",
        ),
        UniqueConstraint(
            "token_digest",
            name="uq_resume_shares_token_digest",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
    )
    resume_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
    )
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class PeerFeedbackRecord(Base):
    __tablename__ = "peer_review_feedback"
    __table_args__ = (
        ForeignKeyConstraint(
            ["share_id", "resume_version_id"],
            ["resume_shares.id", "resume_shares.resume_version_id"],
            name="fk_peer_feedback_share_version",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "share_id",
            "position",
            name="uq_peer_feedback_share_position",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    share_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    resume_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    reviewer_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
    )
    # Stable append order within one share. Timestamps are display/audit data,
    # not an insertion-order primitive: two writes can legitimately tie.
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
