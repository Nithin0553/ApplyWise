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
