"""HTTP surface for F08.

Identity comes from the authenticated session (F01), never from the request
body, as in F07, F11 and F15. Evidence is not caller-supplied either: the
service resolves it from F02 for the authenticated user, so a claim is always
judged against material the user actually owns and has approved.

Unlike F11 and F15, this route needs no production gate. Nothing a client
sends can assert a verification outcome: the request carries a claim and some
evidence ids, and F08 computes the rest.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User, UserRole
from app.modules.evidence.service import EvidenceService

from .contracts import VerifiedStatement
from .schemas import StatementSubmission, VerifiedStatementView
from .service import (
    StatementNotFoundError,
    TooManyStatementsError,
    VerificationService,
    export_eligible,
)

router = APIRouter(prefix="/api/verification", tags=["verification"])
_job_seeker = require_role(UserRole.JOB_SEEKER)


def _service(db: Session) -> VerificationService:
    return VerificationService(db, EvidenceService(db))


def _view(item: VerifiedStatement) -> VerifiedStatementView:
    return VerifiedStatementView(
        statement_id=item.statement_id,
        text=item.text,
        evidence_ids=item.evidence_ids,
        status=item.status,
        revision=item.revision,
        findings=item.findings,
        export_eligible=export_eligible(item.status),
    )


def _not_found() -> HTTPException:
    # One response for missing and foreign-owned ids alike.
    return HTTPException(status_code=404, detail="Statement not found")


@router.post(
    "/statements",
    response_model=VerifiedStatementView,
    status_code=status.HTTP_201_CREATED,
)
def submit_statement(
    submission: StatementSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> VerifiedStatementView:
    """Submit a claim and get F08's verdict on it."""
    try:
        result = _service(db).submit(user_id=current_user.id, submission=submission)
    except TooManyStatementsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return _view(result)


@router.get("/statements", response_model=list[VerifiedStatementView])
def list_statements(
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> list[VerifiedStatementView]:
    """Every held claim, re-classified against the user's current evidence."""
    return [_view(item) for item in _service(db).list_current(user_id=current_user.id)]


@router.get("/statements/{statement_id}", response_model=VerifiedStatementView)
def get_statement(
    statement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> VerifiedStatementView:
    result = _service(db).get_current(user_id=current_user.id, statement_id=statement_id)
    if result is None:
        raise _not_found()
    return _view(result)


@router.delete("/statements/{statement_id}", status_code=status.HTTP_204_NO_CONTENT)
def withdraw_statement(
    statement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> None:
    try:
        _service(db).withdraw(user_id=current_user.id, statement_id=statement_id)
    except StatementNotFoundError as exc:
        raise _not_found() from exc
    db.commit()
