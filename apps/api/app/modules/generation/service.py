"""F07 grounded generation service.

Flow:
1. Receive approved evidence + job context (``GenerationRequest``).
2. Give each evidence item a short reference ("E1", "E2", ...).
3. Ask the AI provider for statements that cite those references.
4. Treat everything the provider returns as untrusted and validate it.
5. Map valid citations back to real evidence IDs (provenance).
6. Return CANDIDATE statements only. F08 verifies, F09 approves.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.services.ai.provider import (
    AIProvider,
    AIProviderError,
    GroundedGenerationRequest,
    GroundedGenerationResponse,
    PromptEvidence,
    RawStatement,
)

from .errors import GenerationUnavailableError, MalformedProviderResponseError
from .schemas import (
    MAX_STATEMENT_LENGTH,
    CandidateStatement,
    GenerationRequest,
    GenerationResult,
    RejectedCandidate,
)

GROUNDING_INSTRUCTIONS = (
    "Write concise resume statements for the job below. "
    "Use ONLY facts from the numbered evidence items. "
    "Do not invent employers, dates, numbers, tools, or results. "
    "Every statement must cite the evidence references it relies on, e.g. E1."
)


class GenerationService:
    def __init__(
        self,
        provider: AIProvider,
        *,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._provider = provider
        self._new_id = id_factory
        self._now = clock

    def generate(self, request: GenerationRequest, *, user_id: UUID) -> GenerationResult:
        # Step 2: short references -> real evidence IDs.
        ref_to_id: dict[str, UUID] = {
            f"E{index}": item.evidence_id
            for index, item in enumerate(request.approved_evidence, start=1)
        }
        prompt_evidence = tuple(
            PromptEvidence(ref=f"E{index}", text=item.to_prompt_text())
            for index, item in enumerate(request.approved_evidence, start=1)
        )
        provider_request = GroundedGenerationRequest(
            job_context=request.job_context.to_prompt_text(),
            evidence=prompt_evidence,
            instructions=GROUNDING_INSTRUCTIONS,
            max_statements=request.max_statements,
        )

        # Step 3: call the provider, failing safely on any provider problem.
        try:
            response = self._provider.generate_grounded(provider_request)
        except AIProviderError as exc:
            raise GenerationUnavailableError("AI provider is unavailable") from exc
        except Exception as exc:  # noqa: BLE001 - never leak provider internals
            raise GenerationUnavailableError("AI provider failed unexpectedly") from exc

        # Step 4: the response as a whole must have the expected shape.
        if not isinstance(response, GroundedGenerationResponse) or not isinstance(
            response.statements, tuple | list
        ):
            raise MalformedProviderResponseError("AI provider returned an invalid response")

        accepted: list[CandidateStatement] = []
        rejected: list[RejectedCandidate] = []
        for raw in response.statements:
            candidate, reason = self._validate_statement(raw, ref_to_id)
            if candidate is None:
                rejected.append(RejectedCandidate(text=_safe_text(raw), reason=reason))
            elif len(accepted) >= request.max_statements:
                rejected.append(
                    RejectedCandidate(text=candidate.text, reason="exceeds max_statements")
                )
            else:
                accepted.append(candidate)

        return GenerationResult(
            generation_id=self._new_id(),
            user_id=user_id,
            provider=getattr(self._provider, "name", "unknown"),
            generated_at=self._now(),
            statements=tuple(accepted),
            rejected=tuple(rejected),
        )

    def _validate_statement(
        self, raw: object, ref_to_id: dict[str, UUID]
    ) -> tuple[CandidateStatement | None, str]:
        """Return (candidate, "") if valid, otherwise (None, reason)."""
        if not isinstance(raw, RawStatement):
            return None, "malformed statement"
        if not isinstance(raw.text, str) or not raw.text.strip():
            return None, "empty text"
        text = raw.text.strip()
        if len(text) > MAX_STATEMENT_LENGTH:
            return None, "text too long"
        if not isinstance(raw.cited_refs, tuple | list) or not raw.cited_refs:
            return None, "no evidence cited"

        evidence_ids: list[UUID] = []
        for ref in raw.cited_refs:
            key = ref.strip().upper() if isinstance(ref, str) else None
            if key not in ref_to_id:
                # A made-up citation means we cannot trust this statement at all.
                return None, f"cites unknown evidence reference {ref!r}"
            if ref_to_id[key] not in evidence_ids:
                evidence_ids.append(ref_to_id[key])

        candidate = CandidateStatement(
            statement_id=self._new_id(),
            text=text,
            evidence_ids=tuple(evidence_ids),
        )
        return candidate, ""


def _safe_text(raw: object) -> str:
    text = getattr(raw, "text", "")
    return text[:MAX_STATEMENT_LENGTH] if isinstance(text, str) else ""
