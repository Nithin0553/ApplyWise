"""HTTP surface for F07 and F11.

Identity comes from the authenticated session (F01), never from the request
body: every route here depends on ``require_role(UserRole.JOB_SEEKER)`` and
passes ``current_user.id`` to the service. A caller therefore cannot generate
statements, or draft a cover letter, against another user's account by editing
a payload.

Evidence is not supplied by the caller either. The F07 request carries
evidence **ids**; the route reads the records themselves from F02 through
``list_grounding_contexts(current_user.id)``, which returns only evidence that
is persisted, owned by that user and APPROVED. An id that does not resolve is
refused before anything reaches the AI provider, so the approved-evidence
guarantee is enforced rather than merely contractual.

F11's cover-letter route still has that gap one step further along: it accepts
approved statements from the client rather than resolving them against what F09
persisted, because no such store exists yet. Until it does, the route is
prototype-only and is not served in production — see
``require_prototype_environment`` below, and ``cover_letter_contracts`` for the
selection logic that will close it the same way F07's is closed here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User, UserRole
from app.modules.evidence.service import EvidenceService
from app.services.ai.factory import UnknownAIProviderError, get_ai_provider

from .cover_letter_schemas import CoverLetterDraft, CoverLetterRequest
from .cover_letter_service import CoverLetterService
from .errors import GenerationUnavailableError, MalformedProviderResponseError
from .resolution import EvidenceNotApprovedError, resolve_approved_evidence
from .schemas import GenerationPreviewRequest, GenerationRequest, GenerationResult
from .service import GenerationService

router = APIRouter(prefix="/api/generation", tags=["generation"])

# Built once at import time: ruff flags calling a dependency factory inside an
# argument default (B008), and a single instance is cheaper per request.
require_job_seeker = require_role(UserRole.JOB_SEEKER)


def require_prototype_environment() -> None:
    """Refuse F11's endpoint outside development.

    The cover-letter route still accepts approved statements from the client,
    which proves their labels are well formed but not that F08 verified and F09
    approved them. Until there is a server-side store to resolve ids against
    (see ``cover_letter_contracts.select_approved_statements``), serving this
    route in production would mean treating client-supplied approval state as
    authoritative. So it does not exist there: the response is a plain 404,
    which leaks nothing about why.
    """
    if settings.app_env == "production":
        raise HTTPException(status_code=404, detail="Not Found")


@router.post("/preview", response_model=GenerationResult)
def preview_generation(
    request: GenerationPreviewRequest,
    current_user: User = Depends(require_job_seeker),
    db: Session = Depends(get_db),
    provider: str | None = Query(
        default=None,
        description="Override the configured AI provider for this call (e.g. stub, demo).",
    ),
) -> GenerationResult:
    """Generate candidate statements for the signed-in job seeker.

    The caller selects evidence by id. The records are read from F02 for the
    authenticated user, so unknown, unapproved and foreign-owned ids are
    refused here and never reach the AI provider.
    """
    try:
        ai_provider = get_ai_provider(provider or settings.ai_provider)
    except UnknownAIProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        approved_evidence = resolve_approved_evidence(
            EvidenceService(db),
            user_id=current_user.id,
            evidence_ids=request.evidence_ids,
        )
    except EvidenceNotApprovedError as exc:
        # 404 rather than 403: the response must not reveal whether a given
        # evidence id exists for some other user.
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    resolved = GenerationRequest(
        job_context=request.job_context,
        approved_evidence=approved_evidence,
        max_statements=request.max_statements,
    )
    service = GenerationService(ai_provider)

    try:
        return service.generate(resolved, user_id=current_user.id)
    except GenerationUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="AI provider is unavailable. Try again."
        ) from exc
    except MalformedProviderResponseError as exc:
        raise HTTPException(
            status_code=502, detail="AI provider returned an unusable response."
        ) from exc


@router.post(
    "/cover-letter/preview",
    response_model=CoverLetterDraft,
    dependencies=[Depends(require_prototype_environment)],
)
def preview_cover_letter(
    request: CoverLetterRequest,
    current_user: User = Depends(require_job_seeker),
    provider: str | None = Query(
        default=None,
        description="Override the configured AI provider for this call (e.g. stub, demo).",
    ),
) -> CoverLetterDraft:
    """Draft cover letter paragraphs for the signed-in job seeker."""
    try:
        ai_provider = get_ai_provider(provider or settings.ai_provider)
    except UnknownAIProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return CoverLetterService(ai_provider).generate(request, user_id=current_user.id)
    except GenerationUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="AI provider is unavailable. Try again."
        ) from exc
    except MalformedProviderResponseError as exc:
        raise HTTPException(
            status_code=502, detail="AI provider returned an unusable response."
        ) from exc


@router.get("/providers")
def list_providers(
    current_user: User = Depends(require_job_seeker),
) -> dict[str, object]:
    """Which providers this build can use, and which one is configured."""
    return {"configured": settings.ai_provider, "available": ["stub", "demo"]}
