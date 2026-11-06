"""F09 request/response models; no caller-supplied verification authority."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .contract import VerificationStatus
from .models import ReviewDecision


class EffectiveReviewStatus(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STALE = "STALE"


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: ReviewDecision
    expected_revision: str = Field(
        min_length=8, max_length=128, pattern=r"^[a-zA-Z0-9._:-]+$"
    )


class StatementReviewView(BaseModel):
    model_config = ConfigDict(frozen=True)

    statement_id: UUID
    text: str
    evidence_ids: tuple[UUID, ...]
    verification_status: VerificationStatus
    verification_revision: str
    review_status: EffectiveReviewStatus
    finalization_eligible: bool
    reviewed_revision: str | None = None


class ReviewHistoryItem(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    sequence: int = Field(gt=0)
    decision: ReviewDecision
    verification_revision: str
    decided_at: datetime
