"""F08's HTTP shapes.

Note what no request model carries: ``status`` and ``revision``. A caller
submits a claim and the evidence it cites; F08 decides what the claim is worth.
There is no field through which a client could assert its own verification.
"""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import (
    MAX_EVIDENCE_PER_STATEMENT,
    MAX_STATEMENT_LENGTH,
    VerificationFinding,
    VerificationStatus,
)

MAX_STATEMENTS_PER_USER = 200


class StatementSubmission(BaseModel):
    """Submit one claim for verification against evidence the user owns."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1, max_length=MAX_STATEMENT_LENGTH)
    evidence_ids: tuple[UUID, ...] = Field(
        min_length=1, max_length=MAX_EVIDENCE_PER_STATEMENT
    )

    @model_validator(mode="after")
    def unique_and_non_blank(self) -> Self:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate evidence IDs are not allowed")
        if not self.text.strip():
            raise ValueError("Statement text cannot be blank")
        return self


class VerifiedStatementView(BaseModel):
    """What F08 returns: the claim, its current classification and why."""

    model_config = ConfigDict(frozen=True)

    statement_id: UUID
    text: str
    evidence_ids: tuple[UUID, ...]
    status: VerificationStatus
    revision: str
    findings: tuple[VerificationFinding, ...] = ()
    export_eligible: bool
