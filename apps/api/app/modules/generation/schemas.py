"""F07 public contract: what generation accepts and what it returns.

See docs/contracts/F07_GENERATION_CONTRACT.md for the full description.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_STATEMENT_LENGTH = 500


class GenerationEvidence(BaseModel):
    """One APPROVED evidence item supplied to F07.

    Callers must build these from F02's
    ``ApprovedEvidenceProvider.list_grounding_contexts(user_id=...)`` seam, via
    ``app.modules.generation.adapters.from_grounding_context``. That seam keeps
    the structured approved fields, which matters for SKILL and CERTIFICATION
    evidence whose meaning lives in ``skill_name``, ``proficiency`` or
    ``credential`` rather than in ``description``.

    Provenance metadata on the F02 context (``source``, ``source_url``,
    ``approved_at``) is deliberately not carried here: it is not content the
    provider should write from, and provenance is tracked by ``evidence_id``.
    """

    model_config = ConfigDict(frozen=True)

    evidence_id: UUID
    evidence_type: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = None
    skill_name: str | None = Field(default=None, max_length=200)
    proficiency: str | None = Field(default=None, max_length=100)
    credential: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None

    def to_prompt_text(self) -> str:
        """Flatten to one labelled line. Description always comes last."""
        parts = [f"[{self.evidence_type}] {self.title}"]
        if self.role:
            parts.append(f"role: {self.role}")
        if self.organization:
            parts.append(f"organization: {self.organization}")
        if self.location:
            parts.append(f"location: {self.location}")
        if self.skill_name:
            parts.append(f"skill: {self.skill_name}")
        if self.proficiency:
            parts.append(f"proficiency: {self.proficiency}")
        if self.credential:
            parts.append(f"credential: {self.credential}")
        if self.start_date or self.end_date:
            start = self.start_date.isoformat() if self.start_date else "unknown"
            end = self.end_date.isoformat() if self.end_date else "present"
            parts.append(f"dates: {start} to {end}")
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


class GenerationPreviewRequest(BaseModel):
    """What a caller may ask for over HTTP.

    Note what is absent, and why each absence matters.

    The user's identity is absent: it comes from the authenticated session
    (F01), so a caller cannot generate against another user's account by
    editing a payload.

    The evidence *content* is absent too. A caller selects which of its own
    approved evidence to draw on by id; the records themselves are read
    server-side from F02 and can therefore neither be fabricated nor altered
    in transit. This is what makes the "only approved evidence" guarantee
    enforced rather than merely contractual.
    """

    model_config = ConfigDict(frozen=True)

    job_context: JobContext
    evidence_ids: tuple[UUID, ...] = Field(min_length=1, max_length=20)
    max_statements: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def evidence_ids_are_unique(self) -> Self:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence_ids contains duplicate values")
        return self


class GenerationRequest(BaseModel):
    """What ``GenerationService`` consumes, after evidence has been resolved.

    This is an internal model, built by the route from a
    ``GenerationPreviewRequest`` plus the records read from F02. It is not a
    shape any client can send: keeping it separate is what stops
    caller-supplied evidence reaching the service.
    """

    model_config = ConfigDict(frozen=True)

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
