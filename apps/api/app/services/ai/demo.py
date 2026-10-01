"""Scripted provider for UI demos (``AI_PROVIDER=demo``).

It behaves like a real language model that was asked to write grounded resume
statements: the wording is realistic, and one statement deliberately cites an
evidence reference that was never supplied, so the generation service's
rejection path can be demonstrated in the UI.

It is offline and deterministic, so a demo never depends on a network call,
an API key, or a model's mood.
"""

from __future__ import annotations

from .provider import GroundedGenerationRequest, GroundedGenerationResponse, RawStatement


def _title(text: str) -> str:
    """The evidence item's title, from the flattened prompt line."""
    head = text.split("|")[0].strip()
    if head.startswith("["):
        head = head.split("]", 1)[-1].strip()
    return head or "the work described"


def _statement_from(text: str) -> str:
    """A resume-style sentence that stays close to the evidence it cites."""
    segments = [part.strip() for part in text.split("|") if part.strip()]
    detail = segments[-1] if len(segments) > 1 else ""
    detail = detail.removeprefix("description:").strip()

    title = _title(text)
    if not detail or detail.startswith(("role:", "organization:")):
        return f"Applied {title} in day-to-day engineering work."

    sentence = detail[0].upper() + detail[1:]
    if not sentence.endswith("."):
        sentence += "."
    return sentence


class DemoAIProvider:
    name = "demo"

    def generate_grounded(
        self, request: GroundedGenerationRequest
    ) -> GroundedGenerationResponse:
        statements: list[RawStatement] = []

        for item in request.evidence[: request.max_statements]:
            statements.append(
                RawStatement(text=_statement_from(item.text), cited_refs=(item.ref,))
            )

        # A statement combining two real sources, when there are two to combine.
        if len(request.evidence) >= 2:
            first, second = request.evidence[0], request.evidence[1]
            statements.append(
                RawStatement(
                    text=(
                        f"Combined {_title(first.text)} with {_title(second.text)} "
                        "to deliver tested, reviewable work."
                    ),
                    cited_refs=(first.ref, second.ref),
                )
            )

        # The teaching case: a confident, attractive, UNGROUNDED claim that cites
        # a source nobody supplied. The generation service must reject it.
        unknown_ref = f"E{len(request.evidence) + 7}"
        statements.append(
            RawStatement(
                text="Reduced production incidents by 40% through an automated release gate.",
                cited_refs=(unknown_ref,),
            )
        )

        # A second failure mode: fluent text with no citation at all.
        statements.append(
            RawStatement(
                text="Recognised across the organisation as a quality champion.",
                cited_refs=(),
            )
        )

        return GroundedGenerationResponse(statements=tuple(statements))
