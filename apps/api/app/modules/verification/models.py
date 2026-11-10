"""F08 persistence.

Only the *claim* is stored: its text and which approved evidence it cites.
Classification and revision are deliberately **not** columns. They are derived
on every read from the statement plus the current state of its evidence, which
is what makes ``list_current`` authoritative rather than a snapshot: editing a
cited evidence record changes the answer immediately, with no job to run and
no cache to invalidate.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class VerifiedStatementRecord(Base):
    __tablename__ = "verification_statements"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    # Cited evidence ids, comma-separated in the caller's order. A child table
    # would buy ordering and referential integrity, but F02 owns those records
    # and F08 must not hold a foreign key into another module's tables.
    evidence_ids: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    def cited_ids(self) -> tuple[UUID, ...]:
        return tuple(UUID(part) for part in self.evidence_ids.split(",") if part)

    @staticmethod
    def pack_ids(evidence_ids: tuple[UUID, ...]) -> str:
        return ",".join(str(item) for item in evidence_ids)
