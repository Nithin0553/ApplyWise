"""F01: persistence model for authenticated users.

The ``users`` table is the single source of truth for identity and role.
Other modules must not read or write this table directly; they depend on
the auth module's public contracts (``get_current_user`` and
``require_role``) instead, per the dependency rule in
``docs/ARCHITECTURE.md``.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(enum.StrEnum):
    """RBAC roles enforced server-side (see docs/ARCHITECTURE.md: "Authorization
    is enforced server-side.").

    Self-registration (F01) only ever creates ``JOB_SEEKER`` accounts.
    ``ADMINISTRATOR`` accounts are provisioned out of band (e.g. a seed
    script or a direct database action by the Configuration Manager), never
    through the public registration endpoint, so a user can never grant
    themselves elevated access.
    """

    JOB_SEEKER = "job_seeker"
    ADMINISTRATOR = "administrator"


def _uuid_str() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=20),
        nullable=False,
        default=UserRole.JOB_SEEKER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
