"""Real provider backed by the Anthropic Messages API (``AI_PROVIDER=anthropic``).

Unlike ``stub`` and ``demo`` this calls a network service, so its output is not
reproducible and may be wrong. That is the point rather than a drawback: F08
verification is deterministic and runs on whatever comes back, so a model that
invents a figure is caught by exactly the same check that catches demo's
scripted fabrications. Demonstrating the guard against a real model is worth
more than demonstrating it against one written to fail on cue.

No vendor SDK is imported. The call is a single httpx POST, which keeps the
dependency surface small and the failure modes visible -- consistent with the
note in factory.py.

The provider still never sees database UUIDs. Evidence arrives as short refs
(E1, E2, ...) and the model is asked to cite those; the generation service
resolves them and rejects any citation that does not. A hallucinated ref is
therefore rejected upstream of this module, not trusted.
"""

from __future__ import annotations

import json
import re

import httpx

from .provider import (
    JobContextRequest,
    JobContextSuggestion,
    AIProviderError,
    CoverLetterRequest,
    CoverLetterResponse,
    GroundedGenerationRequest,
    GroundedGenerationResponse,
    RawParagraph,
    RawStatement,
)

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_TIMEOUT_SECONDS = 30.0

_STATEMENT_INSTRUCTIONS = """\
You write resume statements that are strictly grounded in supplied evidence.

Rules:
- Use ONLY the evidence given. Never add an employer, tool, figure, date or
  ranking that does not appear in it.
- Each statement must cite the refs of the evidence it draws on.
- Write at most {max_statements} statements, one sentence each.

Return ONLY JSON of this exact shape, with no prose and no code fence:
{{"statements": [{{"text": "...", "cited_refs": ["E1"]}}]}}
"""

_COVER_LETTER_INSTRUCTIONS = """\
You write cover letter paragraphs grounded in supplied approved statements.

Rules:
- Use ONLY the statements given. Never introduce a new fact.
- Each paragraph must cite the refs of the statements it draws on.
- Write at most {max_paragraphs} paragraphs. Tone: {tone}.

Return ONLY JSON of this exact shape, with no prose and no code fence:
{{"paragraphs": [{{"text": "...", "cited_refs": ["S1"]}}]}}
"""


def _extract_json(raw: str) -> dict:
    """Parse the model's reply, tolerating a code fence around the JSON.

    Models wrap JSON in ```json fences often enough that failing on it would
    make the provider look broken when it is merely chatty. Anything else
    malformed is an error: this module does not guess at intent.
    """
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIProviderError("The model did not return usable JSON.") from exc
    if not isinstance(parsed, dict):
        raise AIProviderError("The model returned JSON that was not an object.")
    return parsed


def _refs(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


class AnthropicAIProvider:
    """Calls the Anthropic Messages API for grounded drafting."""

    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise AIProviderError("AI_API_KEY is not set, so the anthropic provider cannot run.")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._client = client

    def _post(self, prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }
        try:
            if self._client is not None:
                response = self._client.post(API_URL, json=payload, headers=headers)
            else:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(API_URL, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            # The key is in the headers, never in the message.
            raise AIProviderError("The AI provider could not be reached.") from exc
        if response.status_code != 200:
            raise AIProviderError(
                f"The AI provider rejected the request (HTTP {response.status_code})."
            )
        try:
            blocks = response.json()["content"]
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except (KeyError, TypeError, ValueError) as exc:
            raise AIProviderError("The AI provider returned an unexpected response.") from exc

    def generate_grounded(
        self, request: GroundedGenerationRequest
    ) -> GroundedGenerationResponse:
        evidence = "\n".join(f"{item.ref}: {item.text}" for item in request.evidence)
        prompt = (
            _STATEMENT_INSTRUCTIONS.format(max_statements=request.max_statements)
            + f"\n\nTarget role / job context:\n{request.job_context}"
            + f"\n\nAdditional instructions:\n{request.instructions}"
            + f"\n\nEvidence:\n{evidence}"
        )
        parsed = _extract_json(self._post(prompt, max_tokens=1024))
        items = parsed.get("statements")
        if not isinstance(items, list):
            raise AIProviderError("The model returned no statements.")
        statements = tuple(
            RawStatement(text=str(item.get("text", "")).strip(), cited_refs=_refs(item.get("cited_refs")))
            for item in items
            if isinstance(item, dict) and str(item.get("text", "")).strip()
        )
        return GroundedGenerationResponse(statements=statements[: request.max_statements])

    def generate_cover_letter(self, request: CoverLetterRequest) -> CoverLetterResponse:
        statements = "\n".join(f"{item.ref}: {item.text}" for item in request.statements)
        prompt = (
            _COVER_LETTER_INSTRUCTIONS.format(
                max_paragraphs=request.max_paragraphs, tone=request.tone
            )
            + f"\n\nTarget role / job context:\n{request.job_context}"
            + f"\n\nAdditional instructions:\n{request.instructions}"
            + f"\n\nApproved statements:\n{statements}"
        )
        parsed = _extract_json(self._post(prompt, max_tokens=1536))
        items = parsed.get("paragraphs")
        if not isinstance(items, list):
            raise AIProviderError("The model returned no paragraphs.")
        paragraphs = tuple(
            RawParagraph(text=str(item.get("text", "")).strip(), cited_refs=_refs(item.get("cited_refs")))
            for item in items
            if isinstance(item, dict) and str(item.get("text", "")).strip()
        )
        return CoverLetterResponse(paragraphs=paragraphs[: request.max_paragraphs])

    def suggest_job_context(self, request: JobContextRequest) -> JobContextSuggestion:
        """Read the role title and employer out of a pasted job description.

        This only pre-fills two editable fields, so it is the one place a model
        answer is used without anything checking it. That is acceptable because
        a wrong title costs a correction and reaches nothing else; an empty
        string is explicitly allowed so the model is not pushed into guessing.
        """
        system = (
            "You read job postings and return the advertised role title and the "
            "hiring organisation.\n"
            "Return the role title as advertised, without the sentence around it: "
            'for "Acme is seeking a talented Senior Systems Engineer (Angular)" the '
            'title is "Senior Systems Engineer (Angular)" and the company is "Acme".\n'
            "If the posting does not state one of them, return an empty string for "
            "it. Do not guess, and do not use a department, location or job board "
            "as the company.\n"
            "Reply with JSON only. No prose before or after it."
        )
        user = (
            f"Job posting:\n{request.description}\n\n"
            'Reply with JSON of the form {"role_title": "...", "company_name": "..."}'
        )
        parsed = self._post(system, user)
        return JobContextSuggestion(
            role_title=str(parsed.get("role_title", "")).strip()[:200],
            company_name=str(parsed.get("company_name", "")).strip()[:200],
        )
