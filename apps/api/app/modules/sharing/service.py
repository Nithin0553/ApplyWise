from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.applications.service import (
    ApplicationService,
    ResumeVersionNotFoundError,
)

from .models import PeerFeedbackRecord, ResumeShareRecord
from .schemas import (
    PeerFeedbackCreate,
    PeerFeedbackView,
    ShareCreate,
    ShareCreated,
    ShareGrantView,
    SharedResumeAccess,
)


class ShareTargetNotFoundError(LookupError):
    pass


class ShareNotFoundError(LookupError):
    pass


class InvalidShareExpiryError(ValueError):
    pass


def _generate_share_secret() -> str:
    return token_urlsafe(32)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class SharingService:
    """F14 boundary for immutable-version sharing and append-only peer feedback."""

    def __init__(
        self,
        session: Session,
        *,
        secret_factory: Callable[[], str] = _generate_share_secret,
    ):
        self.session = session
        self._secret_factory = secret_factory

    def create_share(
        self,
        *,
        owner_user_id: UUID,
        resume_version_id: UUID,
        data: ShareCreate,
    ) -> ShareCreated:
        try:
            ApplicationService(self.session).get_resume_version(
                user_id=owner_user_id,
                resume_version_id=resume_version_id,
            )
        except ResumeVersionNotFoundError as exc:
            raise ShareTargetNotFoundError("Resume version not found") from exc

        now = datetime.now(UTC)
        if data.expires_at is not None and _as_utc(data.expires_at) <= now:
            raise InvalidShareExpiryError("expires_at must be in the future")

        secret = self._secret_factory()
        record = ResumeShareRecord(
            owner_user_id=owner_user_id,
            resume_version_id=resume_version_id,
            token_digest=self._digest_secret(secret),
            expires_at=data.expires_at,
        )
        self.session.add(record)
        self.session.flush()
        return ShareCreated(
            grant=ShareGrantView.model_validate(record),
            secret=secret,
        )

    def list_owned_shares(self, *, owner_user_id: UUID) -> list[ShareGrantView]:
        records = self.session.scalars(
            select(ResumeShareRecord)
            .where(ResumeShareRecord.owner_user_id == owner_user_id)
            .order_by(ResumeShareRecord.created_at, ResumeShareRecord.id)
        ).all()
        return [ShareGrantView.model_validate(record) for record in records]

    def revoke_share(
        self,
        *,
        owner_user_id: UUID,
        share_id: UUID,
        revoked_at: datetime | None = None,
    ) -> ShareGrantView:
        record = self._get_owned_share_record(
            owner_user_id=owner_user_id,
            share_id=share_id,
        )
        if record.revoked_at is None:
            record.revoked_at = revoked_at or datetime.now(UTC)
            self.session.flush()
        return ShareGrantView.model_validate(record)

    def resolve_share(
        self,
        *,
        secret: str,
        at: datetime | None = None,
    ) -> SharedResumeAccess:
        digest = self._digest_secret(secret)
        record = self.session.scalar(
            select(ResumeShareRecord).where(ResumeShareRecord.token_digest == digest)
        )
        self._require_active_share(record, at=at)

        assert record is not None
        return SharedResumeAccess(
            share_id=record.id,
            resume_version_id=record.resume_version_id,
            created_at=record.created_at,
            expires_at=record.expires_at,
        )

    def add_feedback(
        self,
        *,
        secret: str,
        reviewer_user_id: UUID,
        data: PeerFeedbackCreate,
        at: datetime | None = None,
    ) -> PeerFeedbackView:
        access = self.resolve_share(secret=secret, at=at)
        record = PeerFeedbackRecord(
            share_id=access.share_id,
            resume_version_id=access.resume_version_id,
            reviewer_user_id=reviewer_user_id,
            comment=data.comment,
        )
        self.session.add(record)
        self.session.flush()
        return PeerFeedbackView.model_validate(record)

    def list_feedback(
        self,
        *,
        owner_user_id: UUID,
        share_id: UUID,
    ) -> list[PeerFeedbackView]:
        share = self._get_owned_share_record(
            owner_user_id=owner_user_id,
            share_id=share_id,
        )
        records = self.session.scalars(
            select(PeerFeedbackRecord)
            .where(PeerFeedbackRecord.share_id == share.id)
            .where(PeerFeedbackRecord.resume_version_id == share.resume_version_id)
            .order_by(PeerFeedbackRecord.created_at, PeerFeedbackRecord.id)
        ).all()
        return [PeerFeedbackView.model_validate(record) for record in records]

    def _get_owned_share_record(
        self,
        *,
        owner_user_id: UUID,
        share_id: UUID,
    ) -> ResumeShareRecord:
        record = self.session.scalar(
            select(ResumeShareRecord)
            .where(ResumeShareRecord.id == share_id)
            .where(ResumeShareRecord.owner_user_id == owner_user_id)
        )
        if record is None:
            raise ShareNotFoundError("Share not found")
        return record

    @staticmethod
    def _require_active_share(
        record: ResumeShareRecord | None,
        *,
        at: datetime | None,
    ) -> None:
        if record is None or record.revoked_at is not None:
            raise ShareNotFoundError("Share not found")

        current_time = _as_utc(at or datetime.now(UTC))
        if record.expires_at is not None and current_time >= _as_utc(record.expires_at):
            raise ShareNotFoundError("Share not found")

    @staticmethod
    def _digest_secret(secret: str) -> str:
        return sha256(secret.encode("utf-8")).hexdigest()
