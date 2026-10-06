"""F11 cover letter service.

Same shape as F07, one link further down the chain:

1. Receive approved statements (F09 output) plus job context.
2. Label each statement S1, S2, ... and keep the mapping private.
3. Ask the provider for paragraphs that cite those labels.
4. Distrust everything it returns and validate paragraph by paragraph.
5. Map citations back to statement IDs, and carry each statement's evidence
   IDs through, so a paragraph still points at the original evidence.
6. Return CANDIDATE paragraphs only. Verification and approval come after.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.services.ai.provider import (
    AIProvider,
    AIProviderError,
    CoverLetterResponse,
    PromptStatement,
    RawParagraph,
)
from app.services.ai.provider import (
    CoverLetterRequest as ProviderCoverLetterRequest,
)

from .cover_letter_schemas import (
    MAX_PARAGRAPH_LENGTH,
    CoverLetterDraft,
    CoverLetterParagraph,
    CoverLetterRequest,
    RejectedParagraph,
)
from .errors import GenerationUnavailableError, MalformedProviderResponseError

COVER_LETTER_INSTRUCTIONS = (
    "Draft a short cover letter for the job below. "
    "Use ONLY the numbered statements, which the applicant has already approved. "
    "Do not invent employers, dates, numbers, tools, or results, and do not "
    "restate a claim the statements do not make. "
    "Every paragraph must cite the statement references it draws on, e.g. S1."
)


class CoverLetterService:
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

    def generate(self, request: CoverLetterRequest, *, user_id: UUID) -> CoverLetterDraft:
        """Draft paragraphs for ``user_id``.

        Identity is a keyword argument rather than a request field so that the
        only way to supply it is from the authenticated session.
        """
        ref_to_statement = {
            f"S{index}": item
            for index, item in enumerate(request.approved_statements, start=1)
        }
        prompt_statements = tuple(
            PromptStatement(ref=ref, text=item.text)
            for ref, item in ref_to_statement.items()
        )

        provider_request = ProviderCoverLetterRequest(
            job_context=request.job_context.to_prompt_text(),
            statements=prompt_statements,
            instructions=COVER_LETTER_INSTRUCTIONS,
            tone=request.tone,
            max_paragraphs=request.max_paragraphs,
        )

        try:
            response = self._provider.generate_cover_letter(provider_request)
        except AIProviderError as exc:
            raise GenerationUnavailableError("AI provider is unavailable") from exc
        except Exception as exc:  # noqa: BLE001 - never leak provider internals
            raise GenerationUnavailableError("AI provider failed unexpectedly") from exc

        if not isinstance(response, CoverLetterResponse) or not isinstance(
            response.paragraphs, tuple | list
        ):
            raise MalformedProviderResponseError("AI provider returned an invalid response")

        accepted: list[CoverLetterParagraph] = []
        rejected: list[RejectedParagraph] = []

        for raw in response.paragraphs:
            paragraph, reason = self._validate_paragraph(raw, ref_to_statement)
            if paragraph is None:
                rejected.append(RejectedParagraph(text=_safe_text(raw), reason=reason))
            elif len(accepted) >= request.max_paragraphs:
                rejected.append(
                    RejectedParagraph(text=paragraph.text, reason="exceeds max_paragraphs")
                )
            else:
                accepted.append(paragraph)

        return CoverLetterDraft(
            draft_id=self._new_id(),
            user_id=user_id,
            provider=getattr(self._provider, "name", "unknown"),
            generated_at=self._now(),
            tone=request.tone,
            paragraphs=tuple(accepted),
            rejected=tuple(rejected),
        )

    def _validate_paragraph(
        self, raw: object, ref_to_statement: dict[str, object]
    ) -> tuple[CoverLetterParagraph | None, str]:
        if not isinstance(raw, RawParagraph):
            return None, "malformed paragraph"
        if not isinstance(raw.text, str) or not raw.text.strip():
            return None, "empty text"
        text = raw.text.strip()
        if len(text) > MAX_PARAGRAPH_LENGTH:
            return None, "text too long"
        if not isinstance(raw.cited_refs, tuple | list) or not raw.cited_refs:
            return None, "no approved statement cited"

        statement_ids: list[UUID] = []
        evidence_ids: list[UUID] = []
        for ref in raw.cited_refs:
            key = ref.strip().upper() if isinstance(ref, str) else None
            statement = ref_to_statement.get(key) if key is not None else None
            if statement is None:
                # A made-up citation means the paragraph is not grounded at all.
                return None, f"cites unknown statement reference {ref!r}"
            if statement.statement_id not in statement_ids:  # type: ignore[attr-defined]
                statement_ids.append(statement.statement_id)  # type: ignore[attr-defined]
            for evidence_id in statement.evidence_ids:  # type: ignore[attr-defined]
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)

        paragraph = CoverLetterParagraph(
            paragraph_id=self._new_id(),
            text=text,
            statement_ids=tuple(statement_ids),
            evidence_ids=tuple(evidence_ids),
        )
        return paragraph, ""


def _safe_text(raw: object) -> str:
    text = getattr(raw, "text", "")
    return text[:MAX_PARAGRAPH_LENGTH] if isinstance(text, str) else ""
