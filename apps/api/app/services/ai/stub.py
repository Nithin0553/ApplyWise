"""Deterministic stub provider used for local development (``AI_PROVIDER=stub``).

It never calls a network service. For each evidence item (up to
``max_statements``) it returns one statement citing exactly that item, so the
output is always the same for the same input.
"""

from __future__ import annotations

from .provider import (
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
