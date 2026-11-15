"""The real provider is exercised against a stubbed transport, never the network.

What matters here is not that the model is clever but that this module is
honest about what came back: it must not invent statements when the reply is
malformed, must not leak the API key into an error, and must pass citation
refs through unchanged so the generation service can reject the ones that do
not resolve.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.ai.anthropic import API_URL, AnthropicAIProvider
from app.services.ai.provider import (
    AIProviderError,
    CoverLetterRequest,
    JobContextRequest,
    RequirementMatchRequest,
    GroundedGenerationRequest,
    PromptEvidence,
    PromptStatement,
)

KEY = "sk-ant-test-key-never-real"


def _provider(handler) -> AnthropicAIProvider:
    transport = httpx.MockTransport(handler)
    return AnthropicAIProvider(
        api_key=KEY, model="test-model", client=httpx.Client(transport=transport)
    )


def _reply(text: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json={"content": [{"type": "text", "text": text}]})


def _request() -> GroundedGenerationRequest:
    return GroundedGenerationRequest(
        job_context="Software Engineer in Test",
        evidence=(
            PromptEvidence(ref="E1", text="Built automated regression suites."),
            PromptEvidence(ref="E2", text="Advanced Python."),
        ),
        instructions="Be concise.",
        max_statements=3,
    )


def test_statements_and_their_citations_are_passed_through() -> None:
    body = json.dumps({"statements": [
        {"text": "Built automated regression suites.", "cited_refs": ["E1"]},
        {"text": "Used Python throughout.", "cited_refs": ["E2", "E1"]},
    ]})
    result = _provider(lambda request: _reply(body)).generate_grounded(_request())

    assert [s.text for s in result.statements] == [
        "Built automated regression suites.", "Used Python throughout."]
    assert result.statements[1].cited_refs == ("E2", "E1")


def test_a_fenced_reply_is_still_parsed() -> None:
    """Models wrap JSON in code fences often enough to tolerate it."""
    body = "```json\n" + json.dumps({"statements": [
        {"text": "Built suites.", "cited_refs": ["E1"]}]}) + "\n```"

    result = _provider(lambda request: _reply(body)).generate_grounded(_request())

    assert result.statements[0].text == "Built suites."


def test_an_unknown_ref_is_passed_through_rather_than_dropped() -> None:
    """Rejecting a hallucinated citation is the generation service's job.

    Silently dropping it here would hide a fabrication from the layer whose
    purpose is to catch it.
    """
    body = json.dumps({"statements": [{"text": "Worked at Google.", "cited_refs": ["E9"]}]})

    result = _provider(lambda request: _reply(body)).generate_grounded(_request())

    assert result.statements[0].cited_refs == ("E9",)


def test_more_statements_than_asked_for_are_truncated() -> None:
    body = json.dumps({"statements": [
        {"text": f"Statement {i}", "cited_refs": ["E1"]} for i in range(10)]})

    result = _provider(lambda request: _reply(body)).generate_grounded(_request())

    assert len(result.statements) == 3


@pytest.mark.parametrize("body", ["not json at all", json.dumps(["a", "list"]), json.dumps({})])
def test_a_malformed_reply_raises_rather_than_inventing_output(body: str) -> None:
    with pytest.raises(AIProviderError):
        _provider(lambda request: _reply(body)).generate_grounded(_request())


def test_an_http_error_is_reported_without_leaking_the_key() -> None:
    with pytest.raises(AIProviderError) as caught:
        _provider(lambda request: _reply("", status=401)).generate_grounded(_request())

    assert KEY not in str(caught.value)
    assert "401" in str(caught.value)


def test_a_network_failure_is_reported_without_leaking_the_key() -> None:
    def explode(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    with pytest.raises(AIProviderError) as caught:
        _provider(explode).generate_grounded(_request())

    assert KEY not in str(caught.value)


def test_a_missing_key_fails_at_construction_not_at_request_time() -> None:
    with pytest.raises(AIProviderError):
        AnthropicAIProvider(api_key="", model="test-model")


def test_the_key_and_version_are_sent_as_headers_and_the_url_is_the_messages_api() -> None:
    seen: dict[str, object] = {}

    def capture(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-api-key")
        seen["version"] = request.headers.get("anthropic-version")
        seen["model"] = json.loads(request.content)["model"]
        return _reply(json.dumps({"statements": [{"text": "x", "cited_refs": ["E1"]}]}))

    _provider(capture).generate_grounded(_request())

    assert seen == {"url": API_URL, "key": KEY, "version": "2023-06-01", "model": "test-model"}


def test_cover_letter_paragraphs_are_parsed() -> None:
    body = json.dumps({"paragraphs": [{"text": "I tested things.", "cited_refs": ["S1"]}]})
    request = CoverLetterRequest(
        job_context="QA Engineer",
        statements=(PromptStatement(ref="S1", text="Built suites."),),
        instructions="Be warm.", tone="professional", max_paragraphs=2,
    )

    result = _provider(lambda r: _reply(body)).generate_cover_letter(request)

    assert result.paragraphs[0].text == "I tested things."
    assert result.paragraphs[0].cited_refs == ("S1",)


# --- job context ----------------------------------------------------------
#
# This is the one call whose answer nothing downstream checks, so what it sends
# matters as much as what it returns. The payload assertion below exists
# because a first version passed the prompt positionally into max_tokens and
# the API rejected every request with "max_tokens: Input should be a valid
# integer" -- a mistake no amount of asserting on the parsed result would have
# caught.

POSTING = (
    "Syms Strategic Group (SSG) is seeking a talented Senior Systems Engineer (Angular)\n"
    "Location: Remote\n"
)


def test_the_outgoing_request_is_well_formed() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return _reply(json.dumps({"role_title": "Senior Systems Engineer (Angular)",
                                  "company_name": "Syms Strategic Group"}))

    _provider(handler).suggest_job_context(JobContextRequest(description=POSTING))

    assert isinstance(seen["max_tokens"], int)
    assert seen["model"] == "test-model"
    assert isinstance(seen["messages"], list)


def test_the_advertised_title_is_separated_from_the_sentence_around_it() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return _reply(json.dumps({"role_title": "Senior Systems Engineer (Angular)",
                                  "company_name": "Syms Strategic Group"}))

    suggestion = _provider(handler).suggest_job_context(JobContextRequest(description=POSTING))

    assert suggestion.role_title == "Senior Systems Engineer (Angular)"
    assert suggestion.company_name == "Syms Strategic Group"


def test_an_unstated_company_comes_back_empty_rather_than_guessed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return _reply(json.dumps({"role_title": "Data Analyst", "company_name": ""}))

    suggestion = _provider(handler).suggest_job_context(JobContextRequest(description=POSTING))

    assert suggestion.role_title == "Data Analyst"
    assert suggestion.company_name == ""


def test_a_malformed_reply_raises_rather_than_inventing_a_title() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return _reply("sorry, I could not read that posting")

    with pytest.raises(AIProviderError):
        _provider(handler).suggest_job_context(JobContextRequest(description=POSTING))


def test_a_rejected_request_reports_the_provider_reason_without_the_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return httpx.Response(400, json={"type": "error", "error": {
            "type": "invalid_request_error", "message": "max_tokens: Input should be a valid integer"}})

    with pytest.raises(AIProviderError) as raised:
        _provider(handler).suggest_job_context(JobContextRequest(description=POSTING))

    assert "max_tokens" in str(raised.value)
    assert KEY not in str(raised.value)


def test_requirements_are_read_from_the_whole_posting_and_bounded() -> None:
    """The heuristic this replaces stopped after ten lines of metadata."""
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return _reply(json.dumps({
            "role_title": "Senior Systems Engineer (Angular)",
            "company_name": "Syms Strategic Group",
            "requirements": [f"Requirement {n}" for n in range(30)],
        }))

    suggestion = _provider(handler).suggest_job_context(JobContextRequest(description=POSTING))

    assert len(suggestion.requirements) == 20
    assert suggestion.requirements[0] == "Requirement 0"


def test_blank_and_oversized_requirements_are_cleaned_up() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return _reply(json.dumps({
            "role_title": "", "company_name": "",
            "requirements": ["  Hands-on Angular experience  ", "   ", "x" * 400],
        }))

    suggestion = _provider(handler).suggest_job_context(JobContextRequest(description=POSTING))

    assert suggestion.requirements[0] == "Hands-on Angular experience"
    assert len(suggestion.requirements) == 2
    assert len(suggestion.requirements[1]) == 300


def test_no_requirements_is_an_acceptable_answer() -> None:
    """The caller falls back to its own heuristic rather than showing none."""
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return _reply(json.dumps({"role_title": "Data Analyst", "company_name": ""}))

    suggestion = _provider(handler).suggest_job_context(JobContextRequest(description=POSTING))

    assert suggestion.requirements == ()


# --- requirement assessment ------------------------------------------------
#
# Assessments are returned by index, not by echoing the requirement back. A
# first version asked for the text and the reply was truncated past
# max_tokens, so every live call failed with unparseable JSON. Indexes also
# mean the text cannot drift from what the caller asked about.

MATCH_REQUEST = RequirementMatchRequest(
    requirements=("Hands-on Angular experience", "Strong Java back-end development"),
    evidence=(PromptEvidence(ref="E1", text="Built automated regression suites."),),
)


def test_assessments_take_their_text_from_the_caller_not_the_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return _reply(json.dumps({"assessments": [
            {"index": 1, "coverage": "MISSING", "cited_refs": [], "note": "No Angular work."},
            {"index": 2, "coverage": "PARTIAL", "cited_refs": ["E1"], "note": "Testing only."},
        ]}))

    result = _provider(handler).assess_requirements(MATCH_REQUEST)

    assert [item.requirement for item in result.assessments] == [
        "Hands-on Angular experience", "Strong Java back-end development",
    ]
    assert [item.coverage for item in result.assessments] == ["MISSING", "PARTIAL"]
    assert result.assessments[1].cited_refs == ("E1",)


def test_an_index_outside_the_list_is_dropped() -> None:
    """Better to return fewer rows than a requirement nobody asked about."""
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return _reply(json.dumps({"assessments": [
            {"index": 1, "coverage": "COVERED", "cited_refs": ["E1"], "note": "ok"},
            {"index": 9, "coverage": "COVERED", "cited_refs": ["E1"], "note": "invented"},
            {"index": "x", "coverage": "COVERED", "cited_refs": [], "note": "bad"},
        ]}))

    result = _provider(handler).assess_requirements(MATCH_REQUEST)

    assert len(result.assessments) == 1
    assert result.assessments[0].requirement == "Hands-on Angular experience"


def test_an_unrecognised_verdict_is_read_as_missing_not_dropped() -> None:
    """Dropping it would overstate coverage, which is what this replaced."""
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return _reply(json.dumps({"assessments": [
            {"index": 1, "coverage": "probably fine", "cited_refs": [], "note": ""},
        ]}))

    result = _provider(handler).assess_requirements(MATCH_REQUEST)

    assert result.assessments[0].coverage == "MISSING"


def test_an_unparseable_reply_raises_so_the_caller_can_fall_back() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return _reply('{"assessments": [{"index": 1, "coverage": "COV')

    with pytest.raises(AIProviderError):
        _provider(handler).assess_requirements(MATCH_REQUEST)
