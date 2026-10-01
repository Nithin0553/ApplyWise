from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.modules.applications.schemas import (
    ApprovalSnapshotStatus,
    EvidenceSnapshotItem,
    ProvenanceSnapshotItem,
    ResumeVersionContent,
    ResumeVersionSnapshot,
    VerificationSnapshotStatus,
)


def make_evidence(evidence_id: UUID) -> EvidenceSnapshotItem:
    return EvidenceSnapshotItem(
        evidence_id=evidence_id,
        evidence_type="project",
        title="Synthetic project",
        approved_at=datetime.now(UTC),
    )


def make_statement(
    *,
    statement_id: UUID,
    evidence_ids: tuple[UUID, ...] = (),
) -> ProvenanceSnapshotItem:
    return ProvenanceSnapshotItem(
        statement_id=statement_id,
        text="Built a synthetic project.",
        evidence_ids=evidence_ids,
        verification_status=VerificationSnapshotStatus.VERIFIED,
        approval_status=ApprovalSnapshotStatus.APPROVED,
    )


def test_resume_version_snapshot_is_immutable() -> None:
    evidence_id = uuid4()
    snapshot = ResumeVersionSnapshot(
        user_id=uuid4(),
        application_id=uuid4(),
        resume_version_id=uuid4(),
        created_at=datetime.now(UTC),
        evidence=(make_evidence(evidence_id),),
        statements=(
            make_statement(
                statement_id=uuid4(),
                evidence_ids=(evidence_id,),
            ),
        ),
    )

    with pytest.raises(ValidationError):
        snapshot.user_id = uuid4()

    assert isinstance(snapshot.evidence, tuple)
    assert isinstance(snapshot.statements[0].evidence_ids, tuple)


def test_snapshot_rejects_unknown_provenance_evidence() -> None:
    evidence_id = uuid4()

    with pytest.raises(
        ValidationError,
        match="provenance references evidence outside this snapshot",
    ):
        ResumeVersionContent(
            evidence=(make_evidence(evidence_id),),
            statements=(
                make_statement(
                    statement_id=uuid4(),
                    evidence_ids=(uuid4(),),
                ),
            ),
        )


def test_snapshot_rejects_duplicate_evidence_ids() -> None:
    evidence_id = uuid4()

    with pytest.raises(ValidationError, match="evidence snapshot IDs must be unique"):
        ResumeVersionContent(
            evidence=(make_evidence(evidence_id), make_evidence(evidence_id)),
        )


def test_snapshot_rejects_duplicate_statement_ids() -> None:
    statement_id = uuid4()

    with pytest.raises(ValidationError, match="statement snapshot IDs must be unique"):
        ResumeVersionContent(
            statements=(
                make_statement(statement_id=statement_id),
                make_statement(statement_id=statement_id),
            ),
        )
