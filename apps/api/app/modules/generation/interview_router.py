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

from .interview_schemas import InterviewPrep, InterviewPrepRequest
from .interview_service import InterviewPreparationService
from .resolution import EvidenceNotApprovedError, resolve_approved_evidence
from .router import require_prototype_environment
from .schemas import GenerationEvidence

router = APIRouter(prefix="/api/interview", tags=["interview"])

require_job_seeker = require_role(UserRole.JOB_SEEKER)


@router.post(
    "/preparation",
    response_model=InterviewPrep,
    dependencies=[Depends(require_prototype_environment)],
)
def prepare_for_interview(
    request: InterviewPrepRequest,
    current_user: User = Depends(require_job_seeker),
    db: Session = Depends(get_db),
) -> InterviewPrep:
    """Return interview questions and defensibility advice for the signed-in user.

    The response is advice. It carries no verification or approval state and
    cannot change whether anything is exportable.
    """
    cited_ids: tuple[UUID, ...] = tuple(
        dict.fromkeys(
            evidence_id
            for statement in request.approved_statements
            for evidence_id in statement.evidence_ids
        )
    )

    try:
        resolved = resolve_approved_evidence(
            EvidenceService(db),
            user_id=current_user.id,
            evidence_ids=cited_ids,
        )
    except EvidenceNotApprovedError as exc:
        # 404 rather than 403, for the same reason as F07: the response must
        # not reveal whether an evidence id exists for some other user.
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    evidence_by_id: dict[UUID, GenerationEvidence] = {
        item.evidence_id: item for item in resolved
    }
    return InterviewPreparationService().prepare(
        request, user_id=current_user.id, evidence_by_id=evidence_by_id
    )
