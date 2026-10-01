from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
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


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApplicationRecord(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "user_id",
            name="uq_applications_id_user",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role_title: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    job_url: Mapped[str | None] = mapped_column(String(1000))
    source: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(
            ApplicationStatus,
            name="application_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=ApplicationStatus.DRAFT,
    )
    applied_on: Mapped[date | None] = mapped_column(Date)
    next_action_on: Mapped[date | None] = mapped_column(Date)
    closed_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class ResumeVersionRecord(Base):
    __tablename__ = "resume_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_id", "user_id"],
            ["applications.id", "applications.user_id"],
            name="fk_resume_versions_application_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "application_id",
            "version_number",
            name="uq_resume_versions_application_version",
        ),
        CheckConstraint("version_number > 0", name="ck_resume_versions_positive_version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    application_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
