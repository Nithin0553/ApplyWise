from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import ApplicationStatus


class VerificationSnapshotStatus(StrEnum):
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNSUPPORTED = "UNSUPPORTED"


class ApprovalSnapshotStatus(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class EvidenceSnapshotItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: UUID
    evidence_type: str
    title: str
    organization: str | None = None
    role: str | None = None
    description: str | None = None
    approved_at: datetime


class ProvenanceSnapshotItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    statement_id: UUID
    text: str
    evidence_ids: tuple[UUID, ...] = ()
    verification_status: VerificationSnapshotStatus
    approval_status: ApprovalSnapshotStatus


def _validate_snapshot_links(
    evidence: tuple[EvidenceSnapshotItem, ...],
    statements: tuple[ProvenanceSnapshotItem, ...],
) -> None:
    evidence_ids = [item.evidence_id for item in evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("evidence snapshot IDs must be unique")

    statement_ids = [item.statement_id for item in statements]
    if len(statement_ids) != len(set(statement_ids)):
        raise ValueError("statement snapshot IDs must be unique")

    known_evidence_ids = set(evidence_ids)
    referenced_evidence_ids = {
        evidence_id
        for statement in statements
        for evidence_id in statement.evidence_ids
    }
    if not referenced_evidence_ids.issubset(known_evidence_ids):
        raise ValueError("statement provenance references evidence outside this snapshot")


class ResumeVersionContent(BaseModel):
    """Immutable content supplied when F13 saves a new resume version."""

    model_config = ConfigDict(frozen=True)

    evidence: tuple[EvidenceSnapshotItem, ...] = ()
    statements: tuple[ProvenanceSnapshotItem, ...] = ()

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:
        _validate_snapshot_links(self.evidence, self.statements)
        return self


class ResumeVersionSnapshot(ResumeVersionContent):
    """Immutable F13 contract captured when a resume version is saved."""

    user_id: UUID
    application_id: UUID
    resume_version_id: UUID
    created_at: datetime


class ApplicationCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    role_title: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    job_url: str | None = Field(default=None, max_length=1000)
    source: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    status: ApplicationStatus = ApplicationStatus.DRAFT
    applied_on: date | None = None
    next_action_on: date | None = None
    closed_on: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.applied_on and self.closed_on and self.closed_on < self.applied_on:
            raise ValueError("closed_on cannot be earlier than applied_on")
        return self


class ApplicationUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    role_title: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    job_url: str | None = Field(default=None, max_length=1000)
    source: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    applied_on: date | None = None
    next_action_on: date | None = None
    closed_on: date | None = None

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self) -> Self:
        for field_name in ("company_name", "role_title"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ApplicationStatusChange(BaseModel):
    status: ApplicationStatus
    occurred_on: date | None = None


class ApplicationView(ApplicationCreate):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class ResumeVersionView(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    user_id: UUID
    application_id: UUID
    version_number: int = Field(gt=0)
    snapshot: ResumeVersionSnapshot
    created_at: datetime
