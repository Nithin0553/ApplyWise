"""F09 HTTP routes: users review verified server-held statements, never labels.

Every mutating request supplies only an ID, desired decision and expected
verification revision. An F08 outage returns 503, not a fabricated approval.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User, UserRole
from app.modules.generation.cover_letter_schemas import ApprovedStatement

from .contract import (
    CurrentVerificationProvider,
    VerificationUnavailableError,
    current_verification_provider,
)
from .schemas import ReviewDecisionRequest, ReviewHistoryItem, StatementReviewView
from .service import (
    ReviewNotEligibleError,
    ReviewNotFoundError,
    StaleVerificationError,
    StatementReviewService,
)

router = APIRouter(prefix="/api/statement-review", tags=["statement-review"])
_job_seeker = require_role(UserRole.JOB_SEEKER)


def _service(db: Session, verifier: CurrentVerificationProvider) -> StatementReviewService:
    return StatementReviewService(db, verifier)


def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, ReviewNotFoundError):
        return HTTPException(status_code=404, detail="Statement not found")
    if isinstance(exc, VerificationUnavailableError):
        return HTTPException(status_code=503, detail="Claim verification is not available.")
    if isinstance(exc, (ReviewNotEligibleError, StaleVerificationError)):
        return HTTPException(status_code=409, detail=str(exc))
    raise exc


@router.get("/approved", response_model=list[ApprovedStatement])
def list_approved(
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
    verifier: CurrentVerificationProvider = Depends(current_verification_provider),
) -> list[ApprovedStatement]:
    try:
        return list(_service(db, verifier).list_approved_statements(user_id=current_user.id))
    except VerificationUnavailableError as exc:
        raise _handle(exc) from exc


@router.get("/{statement_id}", response_model=StatementReviewView)
def get_review(
    statement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
    verifier: CurrentVerificationProvider = Depends(current_verification_provider),
) -> StatementReviewView:
    try:
        return _service(db, verifier).get_review(
            user_id=current_user.id, statement_id=statement_id
        )
    except (VerificationUnavailableError, ReviewNotFoundError) as exc:
        raise _handle(exc) from exc


@router.get("/{statement_id}/history", response_model=list[ReviewHistoryItem])
def get_history(
    statement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
    verifier: CurrentVerificationProvider = Depends(current_verification_provider),
) -> list[ReviewHistoryItem]:
    try:
        return list(_service(db, verifier).history(
            user_id=current_user.id, statement_id=statement_id
        ))
    except (VerificationUnavailableError, ReviewNotFoundError) as exc:
        raise _handle(exc) from exc


@router.post("/{statement_id}/decision", response_model=StatementReviewView)
def decide(
    statement_id: UUID,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
    verifier: CurrentVerificationProvider = Depends(current_verification_provider),
) -> StatementReviewView:
    try:
        result = _service(db, verifier).decide(
            user_id=current_user.id,
            statement_id=statement_id,
            decision=payload.decision,
            expected_revision=payload.expected_revision,
        )
        db.commit()
        return result
    except (VerificationUnavailableError, ReviewNotFoundError,
            StaleVerificationError, ReviewNotEligibleError) as exc:
        db.rollback()
        raise _handle(exc) from exc
    except IntegrityError as exc:
        # A concurrent first review may race on the (user, statement) key.
        # Never return a fabricated success or leak a DB constraint detail.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review was updated concurrently; reload and try again.",
        ) from exc
    except Exception:
        db.rollback()
        raise
