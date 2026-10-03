"""HTTP surface for F07 and F11.

Identity comes from the authenticated session (F01), never from the request
body: every route here depends on ``require_role(UserRole.JOB_SEEKER)`` and
passes ``current_user.id`` to the service. A caller therefore cannot generate
statements, or draft a cover letter, against another user's account by editing
a payload.

Evidence is still supplied by the caller. The F07 contract requires it to come
from F02's ``ApprovedEvidenceProvider.list_grounding_contexts(...)``; once F02
is on main that selection moves server-side (see the follow-up in
docs/contracts/F07_GENERATION_CONTRACT.md), so the approved-evidence guarantee
becomes enforced rather than merely contractual.

F11's cover-letter route has the same gap one step further along: it accepts
approved statements from the client rather than resolving them against what
F09 persisted. Until that store exists the route is prototype-only and is not
served in production — see ``require_prototype_environment`` below and
``cover_letter_contracts`` for the selection logic that will close it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User, UserRole
from app.services.ai.factory import UnknownAIProviderError, get_ai_provider

from .cover_letter_schemas import CoverLetterDraft, CoverLetterRequest
from .cover_letter_service import CoverLetterService
from .errors import GenerationUnavailableError, MalformedProviderResponseError
from .schemas import GenerationRequest, GenerationResult
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
    request: GenerationRequest,
    current_user: User = Depends(require_job_seeker),
    provider: str | None = Query(
        default=None,
        description="Override the configured AI provider for this call (e.g. stub, demo).",
    ),
) -> GenerationResult:
    """Generate candidate statements for the signed-in job seeker."""
    try:
        ai_provider = get_ai_provider(provider or settings.ai_provider)
    except UnknownAIProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = GenerationService(ai_provider)

    try:
        return service.generate(request, user_id=current_user.id)
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
