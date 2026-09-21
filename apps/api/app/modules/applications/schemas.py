from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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


class ResumeVersionSnapshot(BaseModel):
    """Immutable F13 contract captured when a resume version is saved."""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    application_id: UUID
    resume_version_id: UUID
    created_at: datetime
    evidence: tuple[EvidenceSnapshotItem, ...] = ()
    statements: tuple[ProvenanceSnapshotItem, ...] = ()
