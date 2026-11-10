"""F08's public contract: what verification promises, and to whom.

Two seams meet here.

**Downstream (F09).** ``VerificationProvider`` is the shape F09 consumes. It is
restated here structurally rather than imported from
``app.modules.statement_review``, for the same reason F07's ``resolution``
restates F02's provider: F08 carries no build-time dependency on the module
that consumes it, the rule can be tested with a fake in microseconds, and the
two modules integrate through a documented contract rather than an import.
``test_verification_contract_compatibility`` proves the shapes still match.

**Upstream (F02).** ``ApprovedEvidenceProvider`` is F02's grounding seam, read
structurally for the same reason.

The guarantee F09 and F13 rest on is ``revision``. It is **derived** from
everything material about a statement — its text, its cited evidence ids, the
current content of that evidence, and the resulting classification — rather
than stored and bumped by hand. Rotation is therefore structural: there is no
code path that can change what a statement claims, or what backs it, and leave
the revision untouched. A guarantee that depends on remembering to increment a
counter is not a guarantee.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_STATEMENT_LENGTH = 500
MAX_EVIDENCE_PER_STATEMENT = 20
REVISION_PATTERN = r"^[a-zA-Z0-9._:-]+$"


class VerificationStatus(StrEnum):
    """F08's classification of one claim against the evidence behind it.

    The values match F09's ``VerificationStatus`` exactly. Both are StrEnum, so
    members compare equal across the two modules without either importing the
    other.
    """

    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNSUPPORTED = "UNSUPPORTED"


class VerificationReason(StrEnum):
    """Why a claim was classified as it was. One code per detectable pattern."""

    FIGURE_NOT_IN_EVIDENCE = "FIGURE_NOT_IN_EVIDENCE"
    ENTITY_NOT_IN_EVIDENCE = "ENTITY_NOT_IN_EVIDENCE"
    DATE_OUTSIDE_EVIDENCE = "DATE_OUTSIDE_EVIDENCE"
    RANKING_NOT_IN_EVIDENCE = "RANKING_NOT_IN_EVIDENCE"
    SCOPE_NOT_IN_EVIDENCE = "SCOPE_NOT_IN_EVIDENCE"
    EVIDENCE_NOT_AVAILABLE = "EVIDENCE_NOT_AVAILABLE"
    BEYOND_EVIDENCE_WORDING = "BEYOND_EVIDENCE_WORDING"
    FULLY_COVERED = "FULLY_COVERED"


class VerificationFinding(BaseModel):
    """One concrete reason behind a classification, quoting what triggered it."""

    model_config = ConfigDict(frozen=True)

    reason: VerificationReason
    detail: str = Field(min_length=1, max_length=160)


class VerifiedStatement(BaseModel):
    """F08's authoritative answer about one statement.

    This is the shape F09's ``CurrentVerifiedStatement`` declares, plus
    ``findings``, which F09 ignores and the verification UI displays. Field
    names, types and bounds are kept identical on purpose.

    Note what a caller cannot supply: ``status`` and ``revision`` are computed
    by F08 from the statement and its current evidence. No request model in
    this module accepts either one.
    """

    model_config = ConfigDict(frozen=True)

    statement_id: UUID
    user_id: UUID
    text: str = Field(min_length=1, max_length=MAX_STATEMENT_LENGTH)
    evidence_ids: tuple[UUID, ...] = Field(min_length=1, max_length=MAX_EVIDENCE_PER_STATEMENT)
    status: VerificationStatus
    revision: str = Field(min_length=8, max_length=128, pattern=REVISION_PATTERN)
    findings: tuple[VerificationFinding, ...] = ()

    @model_validator(mode="after")
    def unique_references(self) -> Self:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate evidence IDs")
        if not self.text.strip():
            raise ValueError("Verified statement cannot be blank")
        return self


class VerificationProvider(Protocol):
    """What F09 calls. Restated structurally; see the module docstring.

    Both methods re-resolve current F02 evidence and re-classify on every call.
    Neither returns a stored snapshot, so a statement whose evidence changed
    comes back reclassified — or, if its evidence is gone, omitted from
    ``list_current`` rather than served stale.

    ``get_current`` returns ``None`` identically for a statement that does not
    exist and one owned by somebody else, so a caller cannot use the answer to
    learn which.
    """

    def get_current(
        self, *, user_id: UUID, statement_id: UUID
    ) -> VerifiedStatement | None: ...

    def list_current(self, *, user_id: UUID) -> tuple[VerifiedStatement, ...]: ...


class EvidenceFacts(Protocol):
    """The shape F08 reads from F02's ``EvidenceGroundingContext``.

    ``approved_at`` matters as much as the content: it is part of the material
    fingerprint, so re-approving evidence rotates the revision even when the
    words are unchanged.
    """

    evidence_id: UUID
    evidence_type: object
    title: str
    organization: str | None
    role: str | None
    location: str | None
    description: str | None
    skill_name: str | None
    proficiency: str | None
    credential: str | None
    start_date: date | None
    end_date: date | None
    approved_at: datetime


class ApprovedEvidenceProvider(Protocol):
    """F02's seam, as F08 consumes it.

    The implementation returns only evidence that is persisted, owned by
    ``user_id`` and APPROVED. F08 never queries the evidence tables and cannot
    itself confirm approval state.
    """

    def list_grounding_contexts(self, *, user_id: UUID) -> Sequence[EvidenceFacts]: ...
