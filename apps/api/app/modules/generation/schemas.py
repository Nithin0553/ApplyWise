"""F07 public contract: what generation accepts and what it returns.

See docs/contracts/F07_GENERATION_CONTRACT.md for the full description.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_STATEMENT_LENGTH = 500


class GenerationEvidence(BaseModel):
    """One APPROVED evidence item supplied to F07.

    Callers must build these only from F02's
    ``ApprovedEvidenceProvider.list_approved(user_id=...)`` result.
    """

    model_config = ConfigDict(frozen=True)

    evidence_id: UUID
    evidence_type: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    description: str | None = None

    def to_prompt_text(self) -> str:
        parts = [f"[{self.evidence_type}] {self.title}"]
        if self.role:
            parts.append(f"role: {self.role}")
        if self.organization:
            parts.append(f"organization: {self.organization}")
        if self.description:
            parts.append(self.description)
        return " | ".join(parts)


class JobContext(BaseModel):
    """The target job. F04 will later supply normalized requirements here."""

    model_config = ConfigDict(frozen=True)

    job_title: str = Field(min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    description: str = Field(min_length=1)
    requirements: tuple[str, ...] = ()

    def to_prompt_text(self) -> str:
        lines = [f"Job title: {self.job_title}"]
        if self.company:
            lines.append(f"Company: {self.company}")
        lines.append(f"Description: {self.description}")
        if self.requirements:
            lines.append("Requirements: " + "; ".join(self.requirements))
        return "\n".join(lines)


class GenerationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    job_context: JobContext
    approved_evidence: tuple[GenerationEvidence, ...] = Field(min_length=1)
    max_statements: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def evidence_ids_are_unique(self) -> Self:
        ids = [item.evidence_id for item in self.approved_evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("approved_evidence contains duplicate evidence_id values")
        return self


class CandidateStatement(BaseModel):
    """A generated statement. NOT verified, NOT approved, NOT exportable.

    The Literal types make it impossible to create a candidate that claims to
    be verified, approved, or export-eligible. F08 and F09 own those decisions.
    """

    model_config = ConfigDict(frozen=True)

    statement_id: UUID
    text: str = Field(min_length=1, max_length=MAX_STATEMENT_LENGTH)
    evidence_ids: tuple[UUID, ...] = Field(min_length=1)
    status: Literal["CANDIDATE"] = "CANDIDATE"
    verification_status: Literal["PENDING"] = "PENDING"
    approval_status: Literal["UNREVIEWED"] = "UNREVIEWED"
    export_eligible: Literal[False] = False


class RejectedCandidate(BaseModel):
    """Provider output that failed F07's safety checks and was discarded."""

    model_config = ConfigDict(frozen=True)

    text: str
    reason: str


class GenerationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    generation_id: UUID
    user_id: UUID
    provider: str
    generated_at: datetime
    statements: tuple[CandidateStatement, ...]
    rejected: tuple[RejectedCandidate, ...] = ()
