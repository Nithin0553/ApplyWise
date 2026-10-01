"""HTTP surface for F07, used by the tailoring UI prototype.

Scope note: this endpoint has no authentication. F01 owns authentication and
role resolution; once it lands, the authenticated user id replaces the
``user_id`` carried in the request body. Until then this route is intended for
local development and demos only, and it is not mounted when APP_ENV is
``production``.

Evidence is supplied by the caller. The F07 contract requires that it comes
from F02's ``ApprovedEvidenceProvider.list_approved(user_id=...)``; while F02
is unmerged, the UI supplies it directly.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.services.ai.factory import UnknownAIProviderError, get_ai_provider

from .errors import GenerationUnavailableError, MalformedProviderResponseError
from .schemas import GenerationRequest, GenerationResult
from .service import GenerationService

router = APIRouter(prefix="/api/generation", tags=["generation"])


@router.post("/preview", response_model=GenerationResult)
def preview_generation(
    request: GenerationRequest,
    provider: str | None = Query(
        default=None,
        description="Override the configured AI provider for this call (e.g. stub, demo).",
    ),
) -> GenerationResult:
    """Generate candidate statements from approved evidence and job context."""
    try:
        ai_provider = get_ai_provider(provider or settings.ai_provider)
    except UnknownAIProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = GenerationService(ai_provider)

    try:
        return service.generate(request)
    except GenerationUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="AI provider is unavailable. Try again."
        ) from exc
    except MalformedProviderResponseError as exc:
        raise HTTPException(
            status_code=502, detail="AI provider returned an unusable response."
        ) from exc


@router.get("/providers")
def list_providers() -> dict[str, object]:
    """Which providers this build can use, and which one is configured."""
    return {"configured": settings.ai_provider, "available": ["stub", "demo"]}
