from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User, UserRole

from .schemas import ApprovedEvidence, EvidenceCreate, EvidenceUpdate, EvidenceView
from .service import EvidenceNotFoundError, EvidenceService, InvalidEvidenceTransitionError

router = APIRouter(prefix="/api/evidence", tags=["evidence"])
_job_seeker = require_role(UserRole.JOB_SEEKER)


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")


@router.get("/approved", response_model=list[ApprovedEvidence])
def list_approved_evidence(
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> list[ApprovedEvidence]:
    return EvidenceService(db).list_approved(user_id=current_user.id)


@router.get("/", response_model=list[EvidenceView])
def list_evidence(
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> list[EvidenceView]:
    return EvidenceService(db).list_owned(user_id=current_user.id)


@router.post("/", response_model=EvidenceView, status_code=status.HTTP_201_CREATED)
def create_evidence(
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> EvidenceView:
    result = EvidenceService(db).create(user_id=current_user.id, data=payload)
    db.commit()
    return result


@router.get("/{evidence_id}", response_model=EvidenceView)
def get_evidence(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> EvidenceView:
    try:
        return EvidenceService(db).get_owned(user_id=current_user.id, evidence_id=evidence_id)
    except EvidenceNotFoundError as exc:
        raise _not_found(exc) from exc


@router.patch("/{evidence_id}", response_model=EvidenceView)
def update_evidence(
    evidence_id: UUID,
    payload: EvidenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> EvidenceView:
    try:
        result = EvidenceService(db).update(
            user_id=current_user.id,
            evidence_id=evidence_id,
            data=payload,
        )
    except EvidenceNotFoundError as exc:
        raise _not_found(exc) from exc
    db.commit()
    return result


@router.post("/{evidence_id}/approve", response_model=ApprovedEvidence)
def approve_evidence(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> ApprovedEvidence:
    try:
        result = EvidenceService(db).approve(user_id=current_user.id, evidence_id=evidence_id)
    except EvidenceNotFoundError as exc:
        raise _not_found(exc) from exc
    except InvalidEvidenceTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    return result


@router.post("/{evidence_id}/unconfirm", response_model=EvidenceView)
def unconfirm_evidence(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> EvidenceView:
    try:
        result = EvidenceService(db).unconfirm(user_id=current_user.id, evidence_id=evidence_id)
    except EvidenceNotFoundError as exc:
        raise _not_found(exc) from exc
    except InvalidEvidenceTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    return result
