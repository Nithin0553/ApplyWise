from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.applications.schemas import (
    ApplicationCreate,
    ApprovalSnapshotStatus,
    EvidenceSnapshotItem,
    ProvenanceSnapshotItem,
    ResumeVersionContent,
    VerificationSnapshotStatus,
)
from app.modules.applications.service import ApplicationService
from app.modules.sharing.models import ResumeShareRecord
from app.modules.sharing.schemas import PeerFeedbackCreate, ShareCreate
from app.modules.sharing.service import (
    InvalidShareExpiryError,
    ShareNotFoundError,
    ShareTargetNotFoundError,
    SharingService,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    Base.metadata.drop_all(engine)
    engine.dispose()


def make_resume_content(
    text: str = "Built a synthetic review workflow.",
) -> ResumeVersionContent:
    evidence_id = uuid4()
    return ResumeVersionContent(
        evidence=(
            EvidenceSnapshotItem(
                evidence_id=evidence_id,
                evidence_type="project",
                title="Synthetic peer review project",
                role="Backend developer",
                description="Built a synthetic review workflow.",
                approved_at=datetime.now(UTC),
            ),
        ),
        statements=(
            ProvenanceSnapshotItem(
                statement_id=uuid4(),
                text=text,
                evidence_ids=(evidence_id,),
                verification_status=VerificationSnapshotStatus.VERIFIED,
                approval_status=ApprovalSnapshotStatus.APPROVED,
            ),
        ),
    )


def create_resume_version(
    session: Session,
    *,
    user_id: UUID,
    company_name: str = "Synthetic Review Labs",
    text: str = "Built a synthetic review workflow.",
):
    applications = ApplicationService(session)
    application = applications.create_application(
        user_id=user_id,
        data=ApplicationCreate(
            company_name=company_name,
            role_title="Software Engineer",
        ),
    )
    return applications.save_resume_version(
        user_id=user_id,
        application_id=application.id,
        content=make_resume_content(text),
    )


def test_share_secret_is_only_returned_raw_at_creation(session: Session) -> None:
    owner_id = uuid4()
    version = create_resume_version(session, user_id=owner_id)
    sharing = SharingService(session)

    created = sharing.create_share(
        owner_user_id=owner_id,
        resume_version_id=version.id,
        data=ShareCreate(),
    )

    record = session.scalar(
        select(ResumeShareRecord).where(ResumeShareRecord.id == created.grant.id)
    )
    assert record is not None
    assert len(created.secret) >= 40
    assert record.token_digest == sha256(created.secret.encode("utf-8")).hexdigest()
    assert record.token_digest != created.secret
    assert not hasattr(record, "secret")


def test_share_target_hides_foreign_and_missing_resume_versions(session: Session) -> None:
    owner_id = uuid4()
    other_user_id = uuid4()
    version = create_resume_version(session, user_id=owner_id)
    sharing = SharingService(session)

    with pytest.raises(ShareTargetNotFoundError, match="Resume version not found"):
        sharing.create_share(
            owner_user_id=other_user_id,
            resume_version_id=version.id,
            data=ShareCreate(),
        )

    with pytest.raises(ShareTargetNotFoundError, match="Resume version not found"):
        sharing.create_share(
            owner_user_id=other_user_id,
            resume_version_id=uuid4(),
            data=ShareCreate(),
        )


def test_owner_can_list_and_revoke_only_owned_shares(session: Session) -> None:
    owner_id = uuid4()
    other_user_id = uuid4()
    owned_version = create_resume_version(session, user_id=owner_id)
    other_version = create_resume_version(
        session,
        user_id=other_user_id,
        company_name="Other Synthetic Review Labs",
    )
    sharing = SharingService(session)
    owned_share = sharing.create_share(
        owner_user_id=owner_id,
        resume_version_id=owned_version.id,
        data=ShareCreate(),
    )
    sharing.create_share(
        owner_user_id=other_user_id,
        resume_version_id=other_version.id,
        data=ShareCreate(),
    )

    assert [share.id for share in sharing.list_owned_shares(owner_user_id=owner_id)] == [
        owned_share.grant.id
    ]

    with pytest.raises(ShareNotFoundError, match="Share not found"):
        sharing.revoke_share(
            owner_user_id=other_user_id,
            share_id=owned_share.grant.id,
        )

    revoked = sharing.revoke_share(
        owner_user_id=owner_id,
        share_id=owned_share.grant.id,
    )
    assert revoked.revoked_at is not None


def test_active_share_resolution_exposes_only_safe_reference(session: Session) -> None:
    owner_id = uuid4()
    version = create_resume_version(session, user_id=owner_id)
    sharing = SharingService(session)
    created = sharing.create_share(
        owner_user_id=owner_id,
        resume_version_id=version.id,
        data=ShareCreate(),
    )

    access = sharing.resolve_share(secret=created.secret)

    assert access.resume_version_id == version.id
    assert set(access.model_dump()) == {
        "share_id",
        "resume_version_id",
        "created_at",
        "expires_at",
    }


def test_missing_expired_and_revoked_shares_are_indistinguishable(session: Session) -> None:
    owner_id = uuid4()
    version = create_resume_version(session, user_id=owner_id)
    sharing = SharingService(session)
    now = datetime.now(UTC)
    expiring = sharing.create_share(
        owner_user_id=owner_id,
        resume_version_id=version.id,
        data=ShareCreate(expires_at=now + timedelta(hours=1)),
    )
    revoked = sharing.create_share(
        owner_user_id=owner_id,
        resume_version_id=version.id,
        data=ShareCreate(),
    )
    sharing.revoke_share(
        owner_user_id=owner_id,
        share_id=revoked.grant.id,
        revoked_at=now,
    )

    secrets = [
        "synthetic-missing-secret",
        expiring.secret,
        revoked.secret,
    ]
    times = [
        now,
        now + timedelta(hours=2),
        now,
    ]
    for secret, at in zip(secrets, times, strict=True):
        with pytest.raises(ShareNotFoundError, match="Share not found"):
            sharing.resolve_share(secret=secret, at=at)


def test_peer_feedback_is_append_only_and_version_scoped(session: Session) -> None:
    owner_id = uuid4()
    reviewer_id = uuid4()
    version = create_resume_version(
        session,
        user_id=owner_id,
        text="Original synthetic resume statement.",
    )
    sharing = SharingService(session)
    created = sharing.create_share(
        owner_user_id=owner_id,
        resume_version_id=version.id,
        data=ShareCreate(),
    )

    first = sharing.add_feedback(
        secret=created.secret,
        reviewer_user_id=reviewer_id,
        data=PeerFeedbackCreate(comment="Clarify the synthetic outcome."),
    )
    second = sharing.add_feedback(
        secret=created.secret,
        reviewer_user_id=reviewer_id,
        data=PeerFeedbackCreate(comment="The structure is easy to scan."),
    )

    feedback = sharing.list_feedback(
        owner_user_id=owner_id,
        share_id=created.grant.id,
    )
    assert [item.id for item in feedback] == [first.id, second.id]
    assert all(item.resume_version_id == version.id for item in feedback)

    reloaded = ApplicationService(session).get_resume_version(
        user_id=owner_id,
        resume_version_id=version.id,
    )
    assert reloaded.snapshot.statements[0].text == "Original synthetic resume statement."


def test_share_resolution_stays_bound_to_each_resume_version(session: Session) -> None:
    owner_id = uuid4()
    applications = ApplicationService(session)
    application = applications.create_application(
        user_id=owner_id,
        data=ApplicationCreate(
            company_name="Synthetic Versioned Reviews",
            role_title="Engineer",
        ),
    )
    first_version = applications.save_resume_version(
        user_id=owner_id,
        application_id=application.id,
        content=make_resume_content("First synthetic version."),
    )
    second_version = applications.save_resume_version(
        user_id=owner_id,
        application_id=application.id,
        content=make_resume_content("Second synthetic version."),
    )
    sharing = SharingService(session)
    first_share = sharing.create_share(
        owner_user_id=owner_id,
        resume_version_id=first_version.id,
        data=ShareCreate(),
    )
    second_share = sharing.create_share(
        owner_user_id=owner_id,
        resume_version_id=second_version.id,
        data=ShareCreate(),
    )

    assert sharing.resolve_share(secret=first_share.secret).resume_version_id == first_version.id
    assert sharing.resolve_share(secret=second_share.secret).resume_version_id == second_version.id


def test_invalid_expiry_and_blank_feedback_are_rejected(session: Session) -> None:
    owner_id = uuid4()
    version = create_resume_version(session, user_id=owner_id)
    sharing = SharingService(session)

    with pytest.raises(InvalidShareExpiryError):
        sharing.create_share(
            owner_user_id=owner_id,
            resume_version_id=version.id,
            data=ShareCreate(expires_at=datetime.now(UTC) - timedelta(minutes=1)),
        )

    with pytest.raises(ValidationError):
        PeerFeedbackCreate(comment="   ")


def test_database_rejects_share_owner_mismatch(session: Session) -> None:
    owner_id = uuid4()
    other_user_id = uuid4()
    version = create_resume_version(session, user_id=owner_id)

    session.add(
        ResumeShareRecord(
            owner_user_id=other_user_id,
            resume_version_id=version.id,
            token_digest="a" * 64,
        )
    )

    with pytest.raises(IntegrityError):
        session.flush()

    session.rollback()
