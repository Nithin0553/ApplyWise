from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import ApplicationRecord, ApplicationStatus, ResumeVersionRecord
from .schemas import (
    ApplicationCreate,
    ApplicationStatusChange,
    ApplicationUpdate,
    ApplicationView,
    ResumeVersionContent,
    ResumeVersionSnapshot,
    ResumeVersionView,
)


class ApplicationNotFoundError(LookupError):
    pass


class ResumeVersionNotFoundError(LookupError):
    pass


class InvalidApplicationTransitionError(ValueError):
    pass


class InvalidApplicationDatesError(ValueError):
    pass


TERMINAL_APPLICATION_STATUSES = frozenset(
    {
        ApplicationStatus.ACCEPTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }
)

ALLOWED_APPLICATION_TRANSITIONS = {
    ApplicationStatus.DRAFT: frozenset(
        {
            ApplicationStatus.APPLIED,
            ApplicationStatus.INTERVIEWING,
            ApplicationStatus.OFFER,
            ApplicationStatus.ACCEPTED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.APPLIED: frozenset(
        {
            ApplicationStatus.INTERVIEWING,
            ApplicationStatus.OFFER,
            ApplicationStatus.ACCEPTED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.INTERVIEWING: frozenset(
        {
            ApplicationStatus.OFFER,
            ApplicationStatus.ACCEPTED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.OFFER: frozenset(
        {
            ApplicationStatus.ACCEPTED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.ACCEPTED: frozenset(),
    ApplicationStatus.REJECTED: frozenset(),
    ApplicationStatus.WITHDRAWN: frozenset(),
}


class ApplicationService:
    """F13 boundary for application tracking and immutable resume versions."""

    def __init__(self, session: Session):
        self.session = session

    def create_application(
        self,
        *,
        user_id: UUID,
        data: ApplicationCreate,
    ) -> ApplicationView:
        record = ApplicationRecord(user_id=user_id, **data.model_dump())
        self.session.add(record)
        self.session.flush()
        return ApplicationView.model_validate(record)

    def get_application(self, *, user_id: UUID, application_id: UUID) -> ApplicationView:
        record = self._get_owned_application_record(
            user_id=user_id,
            application_id=application_id,
        )
        return ApplicationView.model_validate(record)

    def list_applications(
        self,
        *,
        user_id: UUID,
        status: ApplicationStatus | None = None,
    ) -> list[ApplicationView]:
        statement = select(ApplicationRecord).where(ApplicationRecord.user_id == user_id)
        if status is not None:
            statement = statement.where(ApplicationRecord.status == status)

        records = self.session.scalars(
            statement.order_by(ApplicationRecord.created_at, ApplicationRecord.id)
        ).all()
        return [ApplicationView.model_validate(record) for record in records]

    def update_application(
        self,
        *,
        user_id: UUID,
        application_id: UUID,
        data: ApplicationUpdate,
    ) -> ApplicationView:
        record = self._get_owned_application_record(
            user_id=user_id,
            application_id=application_id,
        )
        updates = data.model_dump(exclude_unset=True)

        proposed_applied_on = (
            updates["applied_on"] if "applied_on" in updates else record.applied_on
        )
        proposed_closed_on = updates["closed_on"] if "closed_on" in updates else record.closed_on
        self._validate_date_order(proposed_applied_on, proposed_closed_on)

        for field_name, value in updates.items():
            setattr(record, field_name, value)

        self.session.flush()
        return ApplicationView.model_validate(record)

    def transition_status(
        self,
        *,
        user_id: UUID,
        application_id: UUID,
        data: ApplicationStatusChange,
    ) -> ApplicationView:
        record = self._get_owned_application_record(
            user_id=user_id,
            application_id=application_id,
        )
        target_status = data.status

        if target_status == record.status:
            return ApplicationView.model_validate(record)

        allowed_targets = ALLOWED_APPLICATION_TRANSITIONS[record.status]
        if target_status not in allowed_targets:
            raise InvalidApplicationTransitionError(
                f"Cannot move application from {record.status.value} to {target_status.value}"
            )

        occurred_on = data.occurred_on or date.today()
        if target_status == ApplicationStatus.APPLIED and record.applied_on is None:
            record.applied_on = occurred_on
        if target_status in TERMINAL_APPLICATION_STATUSES:
            self._validate_date_order(record.applied_on, occurred_on)
            record.closed_on = occurred_on

        record.status = target_status
        self.session.flush()
        return ApplicationView.model_validate(record)

    def save_resume_version(
        self,
        *,
        user_id: UUID,
        application_id: UUID,
        content: ResumeVersionContent,
    ) -> ResumeVersionView:
        application = self.session.scalar(
            select(ApplicationRecord)
            .where(ApplicationRecord.id == application_id)
            .where(ApplicationRecord.user_id == user_id)
            .with_for_update()
        )
        if application is None:
            raise ApplicationNotFoundError("Application not found")

        max_version = self.session.scalar(
            select(func.max(ResumeVersionRecord.version_number))
            .where(ResumeVersionRecord.application_id == application_id)
            .where(ResumeVersionRecord.user_id == user_id)
        )
        version_number = (max_version or 0) + 1
        resume_version_id = uuid4()
        created_at = datetime.now(UTC)
        snapshot = ResumeVersionSnapshot(
            user_id=user_id,
            application_id=application_id,
            resume_version_id=resume_version_id,
            created_at=created_at,
            evidence=content.evidence,
            statements=content.statements,
        )

        record = ResumeVersionRecord(
            id=resume_version_id,
            user_id=user_id,
            application_id=application_id,
            version_number=version_number,
            snapshot=snapshot.model_dump(mode="json"),
            created_at=created_at,
        )
        self.session.add(record)
        self.session.flush()
        return ResumeVersionView.model_validate(record)

    def get_resume_version(
        self,
        *,
        user_id: UUID,
        resume_version_id: UUID,
    ) -> ResumeVersionView:
        record = self._get_owned_resume_version_record(
            user_id=user_id,
            resume_version_id=resume_version_id,
        )
        return ResumeVersionView.model_validate(record)

    def list_resume_versions(
        self,
        *,
        user_id: UUID,
        application_id: UUID,
    ) -> list[ResumeVersionView]:
        self._get_owned_application_record(
            user_id=user_id,
            application_id=application_id,
        )
        records = self.session.scalars(
            select(ResumeVersionRecord)
            .where(ResumeVersionRecord.user_id == user_id)
            .where(ResumeVersionRecord.application_id == application_id)
            .order_by(ResumeVersionRecord.version_number)
        ).all()
        return [ResumeVersionView.model_validate(record) for record in records]

    def _get_owned_application_record(
        self,
        *,
        user_id: UUID,
        application_id: UUID,
    ) -> ApplicationRecord:
        record = self.session.scalar(
            select(ApplicationRecord)
            .where(ApplicationRecord.id == application_id)
            .where(ApplicationRecord.user_id == user_id)
        )
        if record is None:
            raise ApplicationNotFoundError("Application not found")
        return record

    def _get_owned_resume_version_record(
        self,
        *,
        user_id: UUID,
        resume_version_id: UUID,
    ) -> ResumeVersionRecord:
        record = self.session.scalar(
            select(ResumeVersionRecord)
            .where(ResumeVersionRecord.id == resume_version_id)
            .where(ResumeVersionRecord.user_id == user_id)
        )
        if record is None:
            raise ResumeVersionNotFoundError("Resume version not found")
        return record

    @staticmethod
    def _validate_date_order(applied_on: date | None, closed_on: date | None) -> None:
        if applied_on and closed_on and closed_on < applied_on:
            raise InvalidApplicationDatesError("closed_on cannot be earlier than applied_on")
