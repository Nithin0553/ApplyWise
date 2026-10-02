"""Deterministic stub provider used for local development (``AI_PROVIDER=stub``).

It never calls a network service. For each evidence item (up to
``max_statements``) it returns one statement citing exactly that item, so the
output is always the same for the same input.
"""

from __future__ import annotations

from .provider import GroundedGenerationRequest, GroundedGenerationResponse, RawStatement


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
