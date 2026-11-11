from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MarketSkillStatus(StrEnum):
    STRONGLY_SUPPORTED = "Strongly Supported"
    PARTIALLY_SUPPORTED = "Partially Supported"
    UNSUPPORTED = "Unsupported"


class SkillFrequency(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    canonical_name: str
    original_terms: tuple[str, ...]
    posting_count: int
    posting_percentage: float
    recurring: bool
    priority: tuple[str, ...] = ()


class SkillComparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    canonical_name: str
    classification: MarketSkillStatus
    explanation: str
    evidence_ids: tuple[UUID, ...] = ()
    evidence_approved_at: tuple[datetime, ...] = ()


class MarketSkillDemandResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    analysis_id: str
    target_role: str
    taxonomy_version: str
    recurrence_threshold: int = Field(gt=0)
    submitted_count: int
    duplicate_count: int
    excluded_count: int
    analyzed_count: int
    skills: tuple[SkillFrequency, ...]
    comparisons: tuple[SkillComparison, ...] = ()
    warnings: tuple[str, ...] = ()
