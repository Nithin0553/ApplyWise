"""Public F08-to-F09 trust boundary.

F08 must resolve records and current approved F02 evidence for user_id before
returning them here. A statement is not trusted merely because its payload
contains the label VERIFIED. F09 never accepts text/status from browser input.

Integration: F08 implements CurrentVerificationProvider. Until then the
default provider raises VerificationUnavailableError and approval fails closed.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNSUPPORTED = "UNSUPPORTED"


class CurrentVerifiedStatement(BaseModel):
    """Authoritative F08 result, sourced from F08 storage/services only."""

    model_config = ConfigDict(frozen=True)

    statement_id: UUID
    user_id: UUID
    text: str = Field(min_length=1, max_length=500)
    evidence_ids: tuple[UUID, ...] = Field(min_length=1, max_length=20)
    status: VerificationStatus
    revision: str = Field(min_length=8, max_length=128, pattern=r"^[a-zA-Z0-9._:-]+$")

    @model_validator(mode="after")
    def unique_references(self) -> Self:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate evidence IDs")
        if not self.text.strip():
            raise ValueError("Verified statement cannot be blank")
        return self


class VerificationUnavailableError(RuntimeError):
    """The F08 source of truth cannot yet be queried or is unavailable."""


class CurrentVerificationProvider(Protocol):
    """F08's future adapter must re-check the current evidence/statement state.

    Missing or foreign ids return None identically. Edited/revoked evidence
    cannot retain an old valid revision. list_current is authoritative, not a
    saved snapshot: if verification is stale, it is omitted or reclassified.
    """

    def get_current(
        self, *, user_id: UUID, statement_id: UUID
    ) -> CurrentVerifiedStatement | None: ...

    def list_current(self, *, user_id: UUID) -> tuple[CurrentVerifiedStatement, ...]: ...


class UnavailableVerificationProvider:
    """Safe production default until F08 creates its authenticated adapter."""

    def get_current(
        self, *, user_id: UUID, statement_id: UUID
    ) -> CurrentVerifiedStatement | None:
        raise VerificationUnavailableError("Claim verification is not available.")

    def list_current(self, *, user_id: UUID) -> tuple[CurrentVerifiedStatement, ...]:
        raise VerificationUnavailableError("Claim verification is not available.")


def current_verification_provider() -> CurrentVerificationProvider:
    """FastAPI dependency override point for the future F08 adapter."""
    return UnavailableVerificationProvider()
