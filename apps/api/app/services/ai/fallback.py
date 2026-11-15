"""Keep generation working when the network provider does not.

A provider that leaves the machine can time out, rate-limit, or return
something unparseable, and none of those are the user's fault. Without a
fallback each one surfaces as a 503 and the whole flow stops, which is a poor
trade when a deterministic provider is sitting right there.

This weakens no guarantee. Whatever the backup returns is validated by the
generation service and classified by F08 in exactly the same way the primary's
output would be: the fallback changes who drafted the text, never what the
system is willing to certify about it.

The substitution is logged at WARNING, so a run that quietly used the scripted
provider can still be identified afterwards rather than being mistaken for
real model output.
"""

from __future__ import annotations

import logging

from .provider import (
    AIProvider,
    AIProviderError,
    CoverLetterRequest,
    CoverLetterResponse,
    GroundedGenerationRequest,
    GroundedGenerationResponse,
    JobContextRequest,
    JobContextSuggestion,
    RequirementMatchRequest,
    RequirementMatchResponse,
)

logger = logging.getLogger(__name__)


class FallbackAIProvider:
    """Tries ``primary``; uses ``backup`` when primary raises AIProviderError."""

    def __init__(self, primary: AIProvider, backup: AIProvider) -> None:
        self._primary = primary
        self._backup = backup
        # Reports the provider that was asked for, not the one that answered;
        # the log records any substitution.
        self.name = primary.name

    def _report(self, exc: AIProviderError) -> None:
        logger.warning(
            "AI provider %r failed (%s); falling back to %r.",
            self._primary.name, exc, self._backup.name,
        )

    def generate_grounded(
        self, request: GroundedGenerationRequest
    ) -> GroundedGenerationResponse:
        try:
            return self._primary.generate_grounded(request)
        except AIProviderError as exc:
            self._report(exc)
            return self._backup.generate_grounded(request)

    def generate_cover_letter(self, request: CoverLetterRequest) -> CoverLetterResponse:
        try:
            return self._primary.generate_cover_letter(request)
        except AIProviderError as exc:
            self._report(exc)
            return self._backup.generate_cover_letter(request)

    def suggest_job_context(self, request: JobContextRequest) -> JobContextSuggestion:
        try:
            return self._primary.suggest_job_context(request)
        except AIProviderError as exc:
            self._report(exc)
            return self._backup.suggest_job_context(request)

    def assess_requirements(
        self, request: RequirementMatchRequest
    ) -> RequirementMatchResponse:
        try:
            return self._primary.assess_requirements(request)
        except AIProviderError as exc:
            self._report(exc)
            return self._backup.assess_requirements(request)
