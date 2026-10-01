from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.applications.models import ApplicationStatus
from app.modules.applications.schemas import (
    ApplicationCreate,
    ApplicationStatusChange,
    ApplicationUpdate,
    ApprovalSnapshotStatus,
    EvidenceSnapshotItem,
    ProvenanceSnapshotItem,
    ResumeVersionContent,
    VerificationSnapshotStatus,
)
from app.modules.applications.service import (
    ApplicationNotFoundError,
    ApplicationService,
    InvalidApplicationDatesError,
    InvalidApplicationTransitionError,
    ResumeVersionNotFoundError,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    Base.metadata.drop_all(engine)
    engine.dispose()


def create_application(
    service: ApplicationService,
    user_id: UUID,
    *,
    company_name: str = "Example Robotics",
    role_title: str = "Software Engineer",
):
    return service.create_application(
        user_id=user_id,
        data=ApplicationCreate(
            company_name=company_name,
            role_title=role_title,
            location="Dallas, TX",
            job_url="https://example.invalid/jobs/123",
            source="synthetic-test",
        ),
    )


def make_resume_content(text: str = "Built a synthetic scheduling service.") -> ResumeVersionContent:
    evidence_id = uuid4()
    return ResumeVersionContent(
        evidence=(
            EvidenceSnapshotItem(
                evidence_id=evidence_id,
                evidence_type="project",
                title="Synthetic scheduling project",
                role="Backend developer",
                description="Built a synthetic scheduling service.",
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


def test_applications_are_created_and_listed_only_for_owner(session: Session) -> None:
    service = ApplicationService(session)
    owner_id = uuid4()
    other_user_id = uuid4()

    owned = create_application(service, owner_id)
    create_application(service, other_user_id, company_name="Other Synthetic Company")
    session.commit()

    applications = service.list_applications(user_id=owner_id)

    assert [application.id for application in applications] == [owned.id]
    assert applications[0].status == ApplicationStatus.DRAFT


def test_application_metadata_update_validates_date_order(session: Session) -> None:
    service = ApplicationService(session)
    user_id = uuid4()
    application = create_application(service, user_id)

    updated = service.update_application(
        user_id=user_id,
        application_id=application.id,
        data=ApplicationUpdate(
            notes="Synthetic follow-up note",
            applied_on=date(2026, 10, 1),
            next_action_on=date(2026, 10, 8),
        ),
    )

    assert updated.notes == "Synthetic follow-up note"
    assert updated.applied_on == date(2026, 10, 1)

    with pytest.raises(InvalidApplicationDatesError):
        service.update_application(
            user_id=user_id,
            application_id=application.id,
            data=ApplicationUpdate(closed_on=date(2026, 9, 30)),
        )


def test_application_status_lifecycle_and_terminal_state(session: Session) -> None:
    service = ApplicationService(session)
    user_id = uuid4()
    application = create_application(service, user_id)

    applied = service.transition_status(
        user_id=user_id,
        application_id=application.id,
        data=ApplicationStatusChange(
            status=ApplicationStatus.APPLIED,
            occurred_on=date(2026, 10, 2),
        ),
    )
    interviewing = service.transition_status(
        user_id=user_id,
        application_id=application.id,
        data=ApplicationStatusChange(status=ApplicationStatus.INTERVIEWING),
    )
    rejected = service.transition_status(
        user_id=user_id,
        application_id=application.id,
        data=ApplicationStatusChange(
            status=ApplicationStatus.REJECTED,
            occurred_on=date(2026, 10, 15),
        ),
    )

    assert applied.applied_on == date(2026, 10, 2)
    assert interviewing.status == ApplicationStatus.INTERVIEWING
    assert rejected.closed_on == date(2026, 10, 15)

    with pytest.raises(InvalidApplicationTransitionError):
        service.transition_status(
            user_id=user_id,
            application_id=application.id,
            data=ApplicationStatusChange(status=ApplicationStatus.APPLIED),
        )


def test_foreign_and_missing_application_ids_are_indistinguishable(session: Session) -> None:
    service = ApplicationService(session)
    owner_id = uuid4()
    other_user_id = uuid4()
    application = create_application(service, owner_id)

    with pytest.raises(ApplicationNotFoundError, match="Application not found"):
        service.get_application(user_id=other_user_id, application_id=application.id)

    with pytest.raises(ApplicationNotFoundError, match="Application not found"):
        service.get_application(user_id=other_user_id, application_id=uuid4())


def test_resume_version_numbers_increment_per_application(session: Session) -> None:
    service = ApplicationService(session)
    user_id = uuid4()
    first_application = create_application(service, user_id)
    second_application = create_application(
        service,
        user_id,
        company_name="Second Synthetic Company",
    )

    first = service.save_resume_version(
        user_id=user_id,
        application_id=first_application.id,
        content=make_resume_content("First synthetic version."),
    )
    second = service.save_resume_version(
        user_id=user_id,
        application_id=first_application.id,
        content=make_resume_content("Second synthetic version."),
    )
    other_application_first = service.save_resume_version(
        user_id=user_id,
        application_id=second_application.id,
        content=make_resume_content("Independent synthetic version."),
    )
    session.commit()

    assert (first.version_number, second.version_number) == (1, 2)
    assert other_application_first.version_number == 1
    assert first.snapshot.resume_version_id == first.id
    assert first.snapshot.application_id == first_application.id
    assert first.snapshot.user_id == user_id


def test_saved_resume_versions_preserve_historical_snapshot(session: Session) -> None:
    service = ApplicationService(session)
    user_id = uuid4()
    application = create_application(service, user_id)

    first = service.save_resume_version(
        user_id=user_id,
        application_id=application.id,
        content=make_resume_content("Original approved statement."),
    )
    service.save_resume_version(
        user_id=user_id,
        application_id=application.id,
        content=make_resume_content("Later revised statement."),
    )
    session.commit()

    reloaded = service.get_resume_version(
        user_id=user_id,
        resume_version_id=first.id,
    )

    assert reloaded.snapshot.statements[0].text == "Original approved statement."
    with pytest.raises(ValidationError):
        reloaded.snapshot.statements[0].text = "Mutated statement"


def test_resume_version_ownership_hides_foreign_and_missing_ids(session: Session) -> None:
    service = ApplicationService(session)
    owner_id = uuid4()
    other_user_id = uuid4()
    application = create_application(service, owner_id)
    version = service.save_resume_version(
        user_id=owner_id,
        application_id=application.id,
        content=make_resume_content(),
    )
    session.commit()

    with pytest.raises(ResumeVersionNotFoundError, match="Resume version not found"):
        service.get_resume_version(
            user_id=other_user_id,
            resume_version_id=version.id,
        )

    with pytest.raises(ResumeVersionNotFoundError, match="Resume version not found"):
        service.get_resume_version(
            user_id=other_user_id,
            resume_version_id=uuid4(),
        )


def test_listing_versions_requires_owned_application(session: Session) -> None:
    service = ApplicationService(session)
    owner_id = uuid4()
    other_user_id = uuid4()
    application = create_application(service, owner_id)
    service.save_resume_version(
        user_id=owner_id,
        application_id=application.id,
        content=make_resume_content(),
    )
    session.commit()

    with pytest.raises(ApplicationNotFoundError):
        service.list_resume_versions(
            user_id=other_user_id,
            application_id=application.id,
        )
