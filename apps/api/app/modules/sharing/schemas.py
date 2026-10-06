from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ShareCreate(BaseModel):
    expires_at: datetime | None = None


class ShareGrantView(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    owner_user_id: UUID
    resume_version_id: UUID
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class ShareCreated(BaseModel):
    model_config = ConfigDict(frozen=True)

    grant: ShareGrantView
    secret: str


class SharedResumeAccess(BaseModel):
    """Reviewer-facing access reference with no Career Evidence Profile content."""

    model_config = ConfigDict(frozen=True)

    share_id: UUID
    resume_version_id: UUID
    created_at: datetime
    expires_at: datetime | None


class ReviewerShareResolve(BaseModel):
    """Carries the raw reviewer capability outside log-friendly URL fields."""

    secret: str = Field(min_length=20, max_length=200)


class PeerFeedbackCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=4000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("comment cannot be blank")
        return normalized


class ReviewerPeerFeedbackCreate(PeerFeedbackCreate):
    """Reviewer feedback request with the share capability in the body."""

    secret: str = Field(min_length=20, max_length=200)


class PeerFeedbackView(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    share_id: UUID
    resume_version_id: UUID
    reviewer_user_id: UUID
    comment: str
    created_at: datetime
