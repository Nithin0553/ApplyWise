from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import EvidenceStatus, EvidenceType


class EvidenceCreate(BaseModel):
    evidence_type: EvidenceType
    title: str = Field(min_length=1, max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = None
    skill_name: str | None = Field(default=None, max_length=200)
    proficiency: str | None = Field(default=None, max_length=100)
    credential: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=500)
    start_date: date | None = None
    end_date: date | None = None
    source: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")
        return self


class EvidenceUpdate(BaseModel):
    evidence_type: EvidenceType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = None
    skill_name: str | None = Field(default=None, max_length=200)
    proficiency: str | None = Field(default=None, max_length=100)
    credential: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=500)
    start_date: date | None = None
    end_date: date | None = None
    source: str | None = Field(default=None, max_length=100)


class EvidenceView(EvidenceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: EvidenceStatus
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ApprovedEvidence(EvidenceView):
    status: Literal[EvidenceStatus.APPROVED]


class EvidenceGroundingContext(BaseModel):
    """Approved F02 evidence normalized for F05/F07/F08 consumers."""

    evidence_id: UUID
    evidence_type: EvidenceType
    title: str
    organization: str | None = None
    role: str | None = None
    location: str | None = None
    description: str | None = None
    skill_name: str | None = None
    proficiency: str | None = None
    credential: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    source: str | None = None
    source_url: str | None = None
    approved_at: datetime

    @classmethod
    def from_approved(cls, evidence: ApprovedEvidence) -> Self:
        if evidence.approved_at is None:
            raise ValueError("Approved evidence must include approved_at")
        return cls(
            evidence_id=evidence.id,
            evidence_type=evidence.evidence_type,
            title=evidence.title,
            organization=evidence.organization,
            role=evidence.role,
            location=evidence.location,
            description=evidence.description,
            skill_name=evidence.skill_name,
            proficiency=evidence.proficiency,
            credential=evidence.credential,
            start_date=evidence.start_date,
            end_date=evidence.end_date,
            source=evidence.source,
            source_url=evidence.url,
            approved_at=evidence.approved_at,
        )
