from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User, UserRole

from .models import ApplicationStatus
from .schemas import (
    ApplicationCreate,
    ApplicationStatusChange,
    ApplicationUpdate,
    ApplicationView,
    ResumeVersionContent,
    ResumeVersionView,
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
