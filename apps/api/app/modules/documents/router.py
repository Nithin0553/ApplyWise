"""F10 document export API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.applications.finalization import (
    FinalizationNotEligibleError,
    TrustedFinalizationService,
)
from app.modules.applications.service import (
    ApplicationNotFoundError,
    ApplicationService,
    ResumeVersionNotFoundError,
)
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User, UserRole
from app.modules.statement_review.contract import (
    CurrentVerificationProvider,
    VerificationUnavailableError,
)
from app.modules.statement_review.dependencies import current_verification_provider
from app.modules.statement_review.service import StatementReviewService

from .adapter import build_resume_document
from .renderer import render_resume
from .schemas import DocumentFormat, ResumeTemplate

router = APIRouter(prefix="/api/documents", tags=["documents"])
_job_seeker = require_role(UserRole.JOB_SEEKER)


@router.get("/resume-versions/{resume_version_id}/export")
def export_resume(
    resume_version_id: UUID,
    format: DocumentFormat,
    template: ResumeTemplate = ResumeTemplate.STANDARD,
    db: Session = Depends(get_db),
    current_user: User = Depends(_job_seeker),
    verifier: CurrentVerificationProvider = Depends(current_verification_provider),
) -> Response:
    """Export a resume only after current F13 trusted validation."""

    applications = ApplicationService(db)
    trusted = TrustedFinalizationService(
        db,
        StatementReviewService(db, verifier),
    )

    try:
        # F13 revalidates ownership, F09 approval, F08 verification
        # revisions, and F02 evidence before allowing export.
        content = trusted.current_export_content(
            user_id=current_user.id,
            resume_version_id=resume_version_id,
        )

        version = applications.get_resume_version(
            user_id=current_user.id,
            resume_version_id=resume_version_id,
        )

        application = applications.get_application(
            user_id=current_user.id,
            application_id=version.application_id,
        )

    except (ResumeVersionNotFoundError, ApplicationNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume version not found",
        ) from exc

    except VerificationUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claim verification is not available.",
        ) from exc

    except FinalizationNotEligibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    document = build_resume_document(
        full_name=current_user.full_name,
        target_role=application.role_title,
        company=application.company_name,
        content=content,
        template=template,
    )

    data = render_resume(document, format)

    if format == DocumentFormat.PDF:
        media_type = "application/pdf"
        extension = "pdf"
    else:
        media_type = (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
        extension = "docx"

    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="applywise-resume.{extension}"'
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )
