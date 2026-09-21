from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.evidence.models import EvidenceRecord, EvidenceStatus, EvidenceType
from app.modules.evidence.schemas import EvidenceCreate
from app.modules.evidence.service import (
    EvidenceOwnershipError,
    EvidenceService,
    InvalidEvidenceTransitionError,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    Base.metadata.drop_all(engine)
    engine.dispose()


def create_project(service: EvidenceService, user_id: UUID):
    return service.create(
        user_id=user_id,
        data=EvidenceCreate(
            evidence_type=EvidenceType.PROJECT,
            title="Synthetic course scheduling API",
            role="Backend developer",
            description="Built a REST API for a synthetic class project.",
            url="https://example.invalid/project",
            source="manual",
        ),
    )


def test_new_evidence_is_persisted_unconfirmed(session: Session) -> None:
    user_id = uuid4()
    service = EvidenceService(session)

    created = create_project(service, user_id)
    session.commit()

    persisted = session.get(EvidenceRecord, created.id)
    assert persisted is not None
    assert persisted.user_id == user_id
    assert persisted.status == EvidenceStatus.UNCONFIRMED
    assert persisted.approved_at is None


def test_owner_can_approve_and_unconfirm_persisted_evidence(session: Session) -> None:
    user_id = uuid4()
    service = EvidenceService(session)
    created = create_project(service, user_id)

    approved = service.approve(user_id=user_id, evidence_id=created.id)
    session.commit()
    assert approved.status == EvidenceStatus.APPROVED
    assert approved.approved_at is not None

    unconfirmed = service.unconfirm(user_id=user_id, evidence_id=created.id)
    session.commit()
    assert unconfirmed.status == EvidenceStatus.UNCONFIRMED
    assert unconfirmed.approved_at is None


def test_list_approved_filters_state_and_owner(session: Session) -> None:
    owner_id = uuid4()
    other_user_id = uuid4()
    service = EvidenceService(session)

    approved_record = create_project(service, owner_id)
    create_project(service, owner_id)
    other_record = create_project(service, other_user_id)

    service.approve(user_id=owner_id, evidence_id=approved_record.id)
    service.approve(user_id=other_user_id, evidence_id=other_record.id)
    session.commit()

    approved = service.list_approved(user_id=owner_id)

    assert [item.id for item in approved] == [approved_record.id]
    assert all(item.user_id == owner_id for item in approved)
    assert all(item.status == EvidenceStatus.APPROVED for item in approved)


def test_cross_user_access_is_rejected(session: Session) -> None:
    owner_id = uuid4()
    other_user_id = uuid4()
    service = EvidenceService(session)
    created = create_project(service, owner_id)

    with pytest.raises(EvidenceOwnershipError):
        service.approve(user_id=other_user_id, evidence_id=created.id)


def test_duplicate_transition_is_rejected(session: Session) -> None:
    user_id = uuid4()
    service = EvidenceService(session)
    created = create_project(service, user_id)

    service.approve(user_id=user_id, evidence_id=created.id)

    with pytest.raises(InvalidEvidenceTransitionError):
        service.approve(user_id=user_id, evidence_id=created.id)
