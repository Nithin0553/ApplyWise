"""F09 row and append-only decision history.

Review is a user's decision, not a source of verification. A version token
points to the F08 decision the user saw; only F08 can issue a new one.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


class ReviewDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class StatementReviewRecord(Base):
    __tablename__ = "statement_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "statement_id", name="uq_statement_reviews_user_statement"),
        UniqueConstraint("id", "user_id", name="uq_statement_reviews_id_user"),
        CheckConstraint("event_count > 0", name="ck_statement_reviews_positive_event_count"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    statement_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    verification_revision: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[ReviewDecision] = mapped_column(
        Enum(
            ReviewDecision,
            name="statement_review_decision",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda values: [item.value for item in values],
        ),
        nullable=False,
    )
    event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)


class StatementReviewEventRecord(Base):
    __tablename__ = "statement_review_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["review_id", "user_id"],
            ["statement_reviews.id", "statement_reviews.user_id"],
            name="fk_statement_review_event_owned_review",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("review_id", "sequence", name="uq_statement_review_event_sequence"),
        CheckConstraint("sequence > 0", name="ck_statement_review_event_positive_sequence"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    review_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[ReviewDecision] = mapped_column(
        Enum(
            ReviewDecision,
            name="statement_review_decision",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda values: [item.value for item in values],
        ),
        nullable=False,
    )
    verification_revision: Mapped[str] = mapped_column(String(128), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
