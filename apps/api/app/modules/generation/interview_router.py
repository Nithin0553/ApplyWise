"""HTTP surface for F15.

Identity comes from the authenticated session (F01), never from the request
body, exactly as in F07 and F11.

The evidence a statement cites is not caller-supplied either: this route
collects every cited id and reads the records from F02 through
``resolve_approved_evidence``, which returns only evidence that is persisted,
owned by the caller and APPROVED. That matters more here than anywhere else
in the codebase, because F15's whole job is to compare a claim against the
material behind it. If a caller could supply that material, it could also
supply material that appears to justify any claim at all.

The statements themselves are still caller-supplied, because F09 has no store
to resolve ids against. That is the same gap F11 has, and it is handled the
same way: the route does not exist in production. See
``require_prototype_environment``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User, UserRole
from app.modules.evidence.service import EvidenceService
from app.modules.statement_review.contract import (
    CurrentVerificationProvider,
    VerificationUnavailableError,
)
from app.modules.statement_review.dependencies import current_verification_provider
from app.modules.statement_review.service import StatementReviewService

from .cover_letter_contracts import StatementNotApprovedError, select_approved_statements
from .interview_schemas import (
    MAX_CITED_EVIDENCE_PER_REQUEST,
    InterviewPrep,
    InterviewPrepRequest,
    InterviewSelectionRequest,
)
from .interview_service import InterviewPreparationService
from .resolution import EvidenceNotApprovedError, resolve_approved_evidence
from .schemas import GenerationEvidence

router = APIRouter(prefix="/api/interview", tags=["interview"])

require_job_seeker = require_role(UserRole.JOB_SEEKER)


@router.post("/preparation", response_model=InterviewPrep)
def prepare_for_interview(
    request: InterviewSelectionRequest,
    current_user: User = Depends(require_job_seeker),
    db: Session = Depends(get_db),
    verifier: CurrentVerificationProvider = Depends(current_verification_provider),
) -> InterviewPrep:
    """Advisory-only preparation from owned, currently approved F08/F09 claims."""
    try:
        approved = select_approved_statements(
            StatementReviewService(db, verifier),
            user_id=current_user.id,
            statement_ids=request.statement_ids,
        )
    except StatementNotApprovedError as exc:
        raise HTTPException(
            status_code=404, detail="Selected statements are not currently approved."
        ) from exc
    except VerificationUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Verification is unavailable.") from exc

    cited_ids: tuple[UUID, ...] = tuple(dict.fromkeys(
        evidence_id
        for statement in approved
        for evidence_id in statement.evidence_ids
    ))
    if len(cited_ids) > MAX_CITED_EVIDENCE_PER_REQUEST:
        raise HTTPException(status_code=422, detail="Too many cited evidence records.")

    try:
        resolved = resolve_approved_evidence(
            EvidenceService(db), user_id=current_user.id, evidence_ids=cited_ids
        )
    except EvidenceNotApprovedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    evidence_by_id: dict[UUID, GenerationEvidence] = {
        item.evidence_id: item for item in resolved
    }
    trusted_request = InterviewPrepRequest(approved_statements=approved)
    return InterviewPreparationService().prepare(
        trusted_request, user_id=current_user.id, evidence_by_id=evidence_by_id
    )
