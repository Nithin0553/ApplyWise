from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.applications.schemas import (
    ApprovalSnapshotStatus,
    EvidenceSnapshotItem,
    ProvenanceSnapshotItem,
    ResumeVersionSnapshot,
    VerificationSnapshotStatus,
)


def test_resume_version_snapshot_is_immutable() -> None:
    evidence_id = uuid4()
    snapshot = ResumeVersionSnapshot(
        user_id=uuid4(),
        application_id=uuid4(),
        resume_version_id=uuid4(),
        created_at=datetime.now(UTC),
        evidence=(
            EvidenceSnapshotItem(
                evidence_id=evidence_id,
                evidence_type="project",
                title="Synthetic project",
                approved_at=datetime.now(UTC),
            ),
        ),
        statements=(
            ProvenanceSnapshotItem(
                statement_id=uuid4(),
                text="Built a synthetic project.",
                evidence_ids=(evidence_id,),
                verification_status=VerificationSnapshotStatus.VERIFIED,
                approval_status=ApprovalSnapshotStatus.APPROVED,
            ),
        ),
    )

    with pytest.raises(ValidationError):
        snapshot.user_id = uuid4()

    assert isinstance(snapshot.evidence, tuple)
    assert isinstance(snapshot.statements[0].evidence_ids, tuple)
