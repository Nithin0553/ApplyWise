"""Deterministic stub provider used for local development (``AI_PROVIDER=stub``).

It never calls a network service. For each evidence item (up to
``max_statements``) it returns one statement citing exactly that item, so the
output is always the same for the same input.
"""

from __future__ import annotations

from .provider import (
    JobContextRequest,
    JobContextSuggestion,
    CoverLetterRequest,
    CoverLetterResponse,
    GroundedGenerationRequest,
    GroundedGenerationResponse,
    RawParagraph,
    RawStatement,
)


class StubAIProvider:
    name = "stub"

    def generate_grounded(
        self, request: GroundedGenerationRequest
    ) -> GroundedGenerationResponse:
        statements = tuple(
            RawStatement(text=f"Applied experience: {item.text}", cited_refs=(item.ref,))
            for item in request.evidence[: request.max_statements]
        )
        return GroundedGenerationResponse(statements=statements)

    def generate_cover_letter(self, request: CoverLetterRequest) -> CoverLetterResponse:
        paragraphs = tuple(
            RawParagraph(text=f"Relevant to this role: {item.text}", cited_refs=(item.ref,))
            for item in request.statements[: request.max_paragraphs]
        )
        return CoverLetterResponse(paragraphs=paragraphs)

    def suggest_job_context(self, request: JobContextRequest) -> JobContextSuggestion:
        """Deterministic best effort: the first non-empty line, no employer.

        Deliberately weak. It exists so this provider still satisfies the
        protocol and can stand in for a real one, and it reproduces the
        behaviour the UI had before any model was involved.
        """
        first = next(
            (line.strip() for line in request.description.splitlines() if line.strip()), ""
        )
        return JobContextSuggestion(role_title=first[:120], company_name="")
