from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User, UserRole
from app.modules.evidence.service import EvidenceService

from .models import ApplicationStatus
from .schemas import (
    ApplicationCreate,
    ApplicationStatusChange,
    ApplicationUpdate,
    ApplicationView,
    ResumeVersionContent,
    ResumeVersionView,
    ReviewedDraftCreate,
    ReviewedDraftView,
    EvidenceSnapshotItem,
    ProvenanceSnapshotItem,
    VerificationSnapshotStatus,
    ApprovalSnapshotStatus,
)
from .service import (
    ApplicationNotFoundError,
    ApplicationService,
    InvalidApplicationDatesError,
    InvalidApplicationTransitionError,
    ResumeVersionNotFoundError,
)

router = APIRouter(prefix="/api/applications", tags=["applications"])
_job_seeker = require_role(UserRole.JOB_SEEKER)


def _application_not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")


def _resume_not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")


@router.post(
    "/reviewed-drafts",
    response_model=ReviewedDraftView,
    status_code=status.HTTP_201_CREATED,
)
def save_reviewed_draft(
    payload: ReviewedDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> ReviewedDraftView:
    """Atomically save an unverified historical draft and its application.

    F02 is authoritative for approved evidence content. Client statements are
    explicit human-reviewed INFERRED drafts, never F08 VERIFIED results.
    This route is not eligible for F10 finalization/export.
    """
    evidence_ids = list(dict.fromkeys(
        evidence_id
        for statement in payload.statements
        for evidence_id in statement.evidence_ids
    ))
    approved = {
        item.id: item
        for item in EvidenceService(db).list_approved(user_id=current_user.id)
    }
    if any(evidence_id not in approved for evidence_id in evidence_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approved evidence not found",
        )
    if any(approved[evidence_id].approved_at is None for evidence_id in evidence_ids):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approved evidence is incomplete",
        )

    content = ResumeVersionContent(
        evidence=tuple(
            EvidenceSnapshotItem(
                evidence_id=evidence_id,
                evidence_type=approved[evidence_id].evidence_type,
                title=approved[evidence_id].title,
                organization=approved[evidence_id].organization,
                role=approved[evidence_id].role,
                description=approved[evidence_id].description,
                approved_at=approved[evidence_id].approved_at,
            )
            for evidence_id in evidence_ids
        ),
        statements=tuple(
            ProvenanceSnapshotItem(
                statement_id=item.statement_id,
                text=item.text,
                evidence_ids=item.evidence_ids,
                verification_status=VerificationSnapshotStatus.INFERRED,
                approval_status=ApprovalSnapshotStatus.APPROVED,
            )
            for item in payload.statements
        ),
    )

    service = ApplicationService(db)
    try:
        application = service.create_application(
            user_id=current_user.id,
            data=payload.application,
        )
        version = service.save_resume_version(
            user_id=current_user.id,
            application_id=application.id,
            content=content,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return ReviewedDraftView(application=application, resume_version=version)


@router.get("/resume-version-counts", response_model=dict[str, int])
def count_resume_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> dict[str, int]:
    """Return owned per-application version counts without exposing snapshots."""
    return ApplicationService(db).count_resume_versions(user_id=current_user.id)


@router.get("/resume-versions/{resume_version_id}", response_model=ResumeVersionView)
def get_resume_version(
    resume_version_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> ResumeVersionView:
    try:
        return ApplicationService(db).get_resume_version(
            user_id=current_user.id,
            resume_version_id=resume_version_id,
        )
    except ResumeVersionNotFoundError as exc:
        raise _resume_not_found(exc) from exc


@router.get("/", response_model=list[ApplicationView])
def list_applications(
    application_status: ApplicationStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> list[ApplicationView]:
    return ApplicationService(db).list_applications(
        user_id=current_user.id,
        status=application_status,
    )


@router.post("/", response_model=ApplicationView, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> ApplicationView:
    result = ApplicationService(db).create_application(user_id=current_user.id, data=payload)
    db.commit()
    return result


@router.get("/{application_id}", response_model=ApplicationView)
def get_application(
    application_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> ApplicationView:
    try:
        return ApplicationService(db).get_application(
            user_id=current_user.id,
            application_id=application_id,
        )
    except ApplicationNotFoundError as exc:
        raise _application_not_found(exc) from exc


@router.patch("/{application_id}", response_model=ApplicationView)
def update_application(
    application_id: UUID,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> ApplicationView:
    try:
        result = ApplicationService(db).update_application(
            user_id=current_user.id,
            application_id=application_id,
            data=payload,
        )
    except ApplicationNotFoundError as exc:
        raise _application_not_found(exc) from exc
    except InvalidApplicationDatesError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    db.commit()
    return result


@router.post("/{application_id}/status", response_model=ApplicationView)
def transition_application_status(
    application_id: UUID,
    payload: ApplicationStatusChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> ApplicationView:
    try:
        result = ApplicationService(db).transition_status(
            user_id=current_user.id,
            application_id=application_id,
            data=payload,
        )
    except ApplicationNotFoundError as exc:
        raise _application_not_found(exc) from exc
    except (InvalidApplicationTransitionError, InvalidApplicationDatesError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    return result


@router.get("/{application_id}/resume-versions", response_model=list[ResumeVersionView])
def list_resume_versions(
    application_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> list[ResumeVersionView]:
    try:
        return ApplicationService(db).list_resume_versions(
            user_id=current_user.id,
            application_id=application_id,
        )
    except ApplicationNotFoundError as exc:
        raise _application_not_found(exc) from exc


@router.post(
    "/{application_id}/resume-versions",
    response_model=ResumeVersionView,
    status_code=status.HTTP_201_CREATED,
)
def save_resume_version(
    application_id: UUID,
    payload: ResumeVersionContent,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
) -> ResumeVersionView:
    try:
        result = ApplicationService(db).save_resume_version(
            user_id=current_user.id,
            application_id=application_id,
            content=payload,
        )
    except ApplicationNotFoundError as exc:
        raise _application_not_found(exc) from exc
    db.commit()
    return result
