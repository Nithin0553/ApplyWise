"""HTTP surface for F07.

Identity comes from the authenticated session (F01), never from the request
body: the route depends on ``require_role(UserRole.JOB_SEEKER)`` and builds the
generation request with ``current_user.id``. A caller therefore cannot generate
against another user's account by editing a payload.

Evidence is still supplied by the caller. The F07 contract requires it to come
from F02's ``ApprovedEvidenceProvider.list_grounding_contexts(...)``; once F02
is on main that selection moves server-side (see the follow-up in
docs/contracts/F07_GENERATION_CONTRACT.md), so the approved-evidence guarantee
becomes enforced rather than merely contractual.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.modules.auth.dependencies import require_role
from app.modules.auth.models import User, UserRole
from app.services.ai.factory import UnknownAIProviderError, get_ai_provider

from .errors import GenerationUnavailableError, MalformedProviderResponseError
from .schemas import GenerationRequest, GenerationResult
from .service import GenerationService

router = APIRouter(prefix="/api/generation", tags=["generation"])

# Built once at import time: ruff flags calling a dependency factory inside an
# argument default (B008), and a single instance is cheaper per request.
require_job_seeker = require_role(UserRole.JOB_SEEKER)


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


@router.get("/providers")
def list_providers(
    current_user: User = Depends(require_job_seeker),
) -> dict[str, object]:
    """Which providers this build can use, and which one is configured."""
    return {"configured": settings.ai_provider, "available": ["stub", "demo"]}
