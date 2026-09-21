from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import EvidenceRecord, EvidenceStatus
from .schemas import ApprovedEvidence, EvidenceCreate, EvidenceView


class EvidenceNotFoundError(LookupError):
    pass


class EvidenceOwnershipError(PermissionError):
    pass


class InvalidEvidenceTransitionError(ValueError):
    pass


class EvidenceService:
    """F02 domain boundary; callers never need direct evidence-table access."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, *, user_id: UUID, data: EvidenceCreate) -> EvidenceView:
        record = EvidenceRecord(
            user_id=user_id,
            status=EvidenceStatus.UNCONFIRMED,
            **data.model_dump(),
        )
        self.session.add(record)
        self.session.flush()
        return EvidenceView.model_validate(record)

    def get_owned(self, *, user_id: UUID, evidence_id: UUID) -> EvidenceView:
        return EvidenceView.model_validate(
            self._get_owned_record(user_id=user_id, evidence_id=evidence_id)
        )

    def list_owned(self, *, user_id: UUID) -> list[EvidenceView]:
        records = self.session.scalars(
            select(EvidenceRecord)
            .where(EvidenceRecord.user_id == user_id)
            .order_by(EvidenceRecord.created_at, EvidenceRecord.id)
        ).all()
        return [EvidenceView.model_validate(record) for record in records]

    def approve(self, *, user_id: UUID, evidence_id: UUID) -> ApprovedEvidence:
        record = self._get_owned_record(user_id=user_id, evidence_id=evidence_id)
        if record.status == EvidenceStatus.APPROVED:
            raise InvalidEvidenceTransitionError("Evidence is already approved")

        record.status = EvidenceStatus.APPROVED
        record.approved_at = datetime.now(UTC)
        self.session.flush()
        return ApprovedEvidence.model_validate(record)

    def unconfirm(self, *, user_id: UUID, evidence_id: UUID) -> EvidenceView:
        record = self._get_owned_record(user_id=user_id, evidence_id=evidence_id)
        if record.status == EvidenceStatus.UNCONFIRMED:
            raise InvalidEvidenceTransitionError("Evidence is already unconfirmed")

        record.status = EvidenceStatus.UNCONFIRMED
        record.approved_at = None
        self.session.flush()
        return EvidenceView.model_validate(record)

    def list_approved(self, *, user_id: UUID) -> list[ApprovedEvidence]:
        records = self.session.scalars(
            select(EvidenceRecord)
            .where(EvidenceRecord.user_id == user_id)
            .where(EvidenceRecord.status == EvidenceStatus.APPROVED)
            .order_by(EvidenceRecord.created_at, EvidenceRecord.id)
        ).all()
        return [ApprovedEvidence.model_validate(record) for record in records]

    def _get_owned_record(self, *, user_id: UUID, evidence_id: UUID) -> EvidenceRecord:
        record = self.session.get(EvidenceRecord, evidence_id)
        if record is None:
            raise EvidenceNotFoundError(str(evidence_id))
        if record.user_id != user_id:
            raise EvidenceOwnershipError("Evidence belongs to another user")
        return record
