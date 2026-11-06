from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User, UserRole

from .schemas import (
    PeerFeedbackCreate,
    PeerFeedbackView,
    ReviewerPeerFeedbackCreate,
    ReviewerShareResolve,
    ShareCreate,
    ShareCreated,
    SharedResumeAccess,
    ShareGrantView,
)
from .service import (
    InvalidShareExpiryError,
    ShareNotFoundError,
    ShareTargetNotFoundError,
    SharingService,
)

router = APIRouter(prefix="/api/shares", tags=["sharing"])
_job_seeker = require_role(UserRole.JOB_SEEKER)
_reviewer = require_role(UserRole.REVIEWER)


def _share_not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")


@router.post("/reviewer/resolve", response_model=SharedResumeAccess)
def resolve_share(
    payload: ReviewerShareResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(_reviewer),
) -> SharedResumeAccess:
    del current_user
    try:
        return SharingService(db).resolve_share(secret=payload.secret)
    except ShareNotFoundError as exc:
        raise _share_not_found(exc) from exc


@router.post(
    "/reviewer/feedback",
    response_model=PeerFeedbackView,
    status_code=status.HTTP_201_CREATED,
)
def add_peer_feedback(
    payload: ReviewerPeerFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_reviewer),
) -> PeerFeedbackView:
    try:
        result = SharingService(db).add_feedback(
            secret=payload.secret,
            reviewer_user_id=current_user.id,
            data=PeerFeedbackCreate(comment=payload.comment),
        )
    except ShareNotFoundError as exc:
        raise _share_not_found(exc) from exc
    db.commit()
    return result


@router.get("/", response_model=list[ShareGrantView])
def list_owned_shares(
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> list[ShareGrantView]:
    return SharingService(db).list_owned_shares(owner_user_id=current_user.id)


@router.post(
    "/resume-versions/{resume_version_id}",
    response_model=ShareCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_share(
    resume_version_id: UUID,
    payload: ShareCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> ShareCreated:
    try:
        result = SharingService(db).create_share(
            owner_user_id=current_user.id,
            resume_version_id=resume_version_id,
            data=payload,
        )
    except ShareTargetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume version not found",
        ) from exc
    except InvalidShareExpiryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    db.commit()
    return result


@router.post("/{share_id}/revoke", response_model=ShareGrantView)
def revoke_share(
    share_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> ShareGrantView:
    try:
        result = SharingService(db).revoke_share(
            owner_user_id=current_user.id,
            share_id=share_id,
        )
    except ShareNotFoundError as exc:
        raise _share_not_found(exc) from exc
    db.commit()
    return result


@router.get("/{share_id}/feedback", response_model=list[PeerFeedbackView])
def list_peer_feedback(
    share_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> list[PeerFeedbackView]:
    try:
        return SharingService(db).list_feedback(
            owner_user_id=current_user.id,
            share_id=share_id,
        )
    except ShareNotFoundError as exc:
        raise _share_not_found(exc) from exc
