from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupportClassification(StrEnum):
    STRONGLY_SUPPORTED = "Strongly Supported"
    PARTIALLY_SUPPORTED = "Partially Supported"
    UNSUPPORTED = "Unsupported"


class GapAssessment(StrEnum):
    PRESENTATION_GAP = "presentation_gap"
    QUALIFICATION_GAP = "qualification_gap"
    UNCERTAIN = "uncertain"


class EvidenceReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: UUID
    approved_at: datetime
    title: str
    summary: str | None = None


class RequirementMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    requirement_id: str
    requirement_text: str
    classification: SupportClassification
    evidence: tuple[EvidenceReference, ...] = ()
    explanation: str
    unmet_conditions: tuple[str, ...] = ()
    gap_assessment: GapAssessment | None = None
    review_warnings: tuple[str, ...] = ()


class MatchingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    matches: tuple[RequirementMatch, ...]
    warnings: tuple[str, ...] = ()


class SelectionExplanation(BaseModel):
    model_config = ConfigDict(frozen=True)

    requirement_id: str
    reason: str


class ContentSelectionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    template_id: str
    max_evidence: int = Field(default=20, ge=1, le=20)
    requirement_matches: tuple[RequirementMatch, ...] = ()
    explicit_evidence_ids: tuple[UUID, ...] = ()
    excluded_evidence_ids: tuple[UUID, ...] = ()


class ContentSelectionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    template_id: str
    selected_evidence_ids: tuple[UUID, ...]
    explanations: tuple[SelectionExplanation, ...] = ()
    warnings: tuple[str, ...] = ()
