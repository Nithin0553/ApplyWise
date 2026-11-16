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
    AIProviderError,
    CoverLetterRequest,
    CoverLetterResponse,
    GroundedGenerationRequest,
    GroundedGenerationResponse,
    JobContextRequest,
    JobContextSuggestion,
    RawParagraph,
    RawStatement,
    RequirementAssessment,
    RequirementMatchRequest,
    RequirementMatchResponse,
)

MAX_REQUIREMENTS = 20
_COVERAGE = {"COVERED", "PARTIAL", "MISSING"}
_REQUIREMENT_MATCH_INSTRUCTIONS = (
    "Decide, for each requirement, how well the candidate's approved evidence "
    "answers it.\n"
    "Use COVERED when the evidence clearly shows it, PARTIAL when the evidence "
    "is related but thinner than the requirement asks, and MISSING when the "
    "evidence does not show it at all.\n"
    "Cite the evidence references that support your answer, and cite none for "
    "MISSING. Use only the references given; do not invent one.\n"
    "Judge only what the evidence says. Do not assume a skill because a related "
    "one is present, and do not reward keyword overlap on its own.\n"
    "Add a short note, at most 20 words, saying what is present or absent.\n"
    "Return one entry per requirement, identified by its number. Do not repeat "
    "the requirement text: the caller already has it, and echoing it wastes the "
    "reply budget and risks altering what was asked.\n"
    'Reply with JSON only, of the form {"assessments": [{"index": 1, '
    '"coverage": "COVERED", "cited_refs": ["E1"], "note": "..."}]}'
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

_JOB_CONTEXT_INSTRUCTIONS = (
    "Read this job posting and return the advertised role title and the hiring "
    "organisation.\n"
    "Give the title as advertised, without the sentence around it: for "
    '"Acme is seeking a talented Senior Systems Engineer (Angular)" the title is '
    '"Senior Systems Engineer (Angular)" and the company is "Acme".\n'
    "If the posting does not state one of them, return an empty string for it. "
    "Do not guess, and do not use a department, location or job board as the "
    "company.\n"
    "Also list what the posting actually asks a candidate to have or do: "
    "skills, technologies, experience and responsibilities. Read the whole "
    "posting, not only the opening. Each item must be one specific requirement "
    "in the posting's own words, trimmed of bullet characters.\n"
    "Do not include section headings such as "
    '"Essential Duties and Responsibilities", and do not include administrative '
    "details such as department, location, salary, clearance level, employment "
    "type or equal-opportunity text. Those describe the posting, not the "
    "candidate.\n"
    "Return at most 20 requirements, most important first.\n"
    'Reply with JSON only, of the form {"role_title": "...", "company_name": "...", '
    '"requirements": ["...", "..."]}'
)

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



def _error_message(response: httpx.Response) -> str:
    """The provider's stated reason, or a placeholder when it gives none."""
    try:
        body = response.json()
    except ValueError:
        return "no message supplied"
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])[:300]
    return "no message supplied"


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
            # The status alone is not actionable: a wrong model name, an
            # unsupported parameter and an exhausted quota all arrive as 4xx.
            # The provider's own message names the cause and describes the
            # request rather than echoing its content, so it is included,
            # truncated, while the body itself still is not. The key lives in
            # the headers and never appears here.
            raise AIProviderError(
                f"The AI provider rejected the request "
                f"(HTTP {response.status_code}): {_error_message(response)}"
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
            RawStatement(
                text=str(item.get("text", "")).strip(),
                cited_refs=_refs(item.get("cited_refs")),
            )
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
            RawParagraph(
                text=str(item.get("text", "")).strip(),
                cited_refs=_refs(item.get("cited_refs")),
            )
            for item in items
            if isinstance(item, dict) and str(item.get("text", "")).strip()
        )
        return CoverLetterResponse(paragraphs=paragraphs[: request.max_paragraphs])

    def suggest_job_context(self, request: JobContextRequest) -> JobContextSuggestion:
        """Read the role title and employer out of a pasted job description.

        This only pre-fills two editable fields, so it is the one place a model
        answer is used without anything checking it. That is acceptable because
        of where it stops: a wrong title costs a correction and reaches neither
        evidence, verification nor approval. An empty string is explicitly
        allowed so the model is not pushed into guessing.
        """
        prompt = _JOB_CONTEXT_INSTRUCTIONS + f"\n\nJob posting:\n{request.description}"
        parsed = _extract_json(self._post(prompt, max_tokens=2048))
        raw = parsed.get("requirements")
        requirements = tuple(
            str(item).strip()[:300]
            for item in (raw if isinstance(raw, list) else [])
            if str(item).strip()
        )[:MAX_REQUIREMENTS]
        return JobContextSuggestion(
            role_title=str(parsed.get("role_title", "")).strip()[:200],
            company_name=str(parsed.get("company_name", "")).strip()[:200],
            requirements=requirements,
        )

    def assess_requirements(
        self, request: RequirementMatchRequest
    ) -> RequirementMatchResponse:
        """Gap analysis against the user's approved evidence.

        Advisory, and deliberately kept away from the trust boundary: it says
        what the user can currently speak to, not whether anything they write
        is supported. F08 answers that, deterministically, and nothing here
        feeds into it.
        """
        evidence = "\n".join(f"{item.ref}: {item.text}" for item in request.evidence)
        numbered = "\n".join(
            f"{index}. {text}" for index, text in enumerate(request.requirements, start=1)
        )
        prompt = (
            _REQUIREMENT_MATCH_INSTRUCTIONS
            + f"\n\nRequirements:\n{numbered}"
            + f"\n\nApproved evidence:\n{evidence}"
        )
        parsed = _extract_json(self._post(prompt, max_tokens=4000))
        raw = parsed.get("assessments")
        if not isinstance(raw, list):
            raise AIProviderError("The model returned no assessments.")
        assessments = []
        for item in raw[:MAX_REQUIREMENTS]:
            if not isinstance(item, dict):
                continue
            # The requirement comes from the caller's own list, looked up by
            # the index the model returned, so the text cannot drift from what
            # was asked and an out-of-range index is dropped rather than
            # inventing a requirement nobody listed.
            try:
                position = int(item.get("index", 0)) - 1
            except (TypeError, ValueError):
                continue
            if not 0 <= position < len(request.requirements):
                continue
            coverage = str(item.get("coverage", "")).strip().upper()
            assessments.append(
                RequirementAssessment(
                    requirement=request.requirements[position],
                    # An unrecognised verdict is treated as MISSING rather than
                    # dropped: silently losing a requirement would overstate
                    # coverage, which is the failure this feature exists to fix.
                    coverage=coverage if coverage in _COVERAGE else "MISSING",
                    cited_refs=_refs(item.get("cited_refs")),
                    note=str(item.get("note", "")).strip()[:200],
                )
            )
        if not assessments:
            raise AIProviderError("The model returned no usable assessments.")
        return RequirementMatchResponse(assessments=tuple(assessments))
