"""Tests for the AI provider seam: the stub provider and provider selection."""

from __future__ import annotations

import pytest

from app.modules.generation.service import GenerationService
from app.services.ai.factory import UnknownAIProviderError, get_ai_provider
from app.services.ai.stub import StubAIProvider
from tests.fixtures.generation_fixtures import EVIDENCE_ONE_ID, USER_ID, build_request


def test_get_ai_provider_returns_stub_for_stub_setting() -> None:
    assert isinstance(get_ai_provider("stub"), StubAIProvider)
    assert isinstance(get_ai_provider(" STUB "), StubAIProvider)


def test_get_ai_provider_rejects_unknown_provider() -> None:
    with pytest.raises(UnknownAIProviderError):
        get_ai_provider("mystery-ai")


def test_stub_provider_is_deterministic_and_grounded() -> None:
    service = GenerationService(StubAIProvider())
    request = build_request()

    first = service.generate(request, user_id=USER_ID)
    second = service.generate(request, user_id=USER_ID)

    assert [s.text for s in first.statements] == [s.text for s in second.statements]
    assert first.statements[0].evidence_ids == (EVIDENCE_ONE_ID,)
    assert first.provider == "stub"
    assert first.rejected == ()


def test_stub_provider_respects_max_statements() -> None:
    result = GenerationService(StubAIProvider()).generate(
        build_request(max_statements=1), user_id=USER_ID
    )

    assert len(result.statements) == 1


# --- the demo provider is job-aware ---------------------------------------


def test_demo_provider_orders_and_frames_statements_by_the_job() -> None:
    """Different job requirements must produce different output."""
    from app.services.ai.demo import DemoAIProvider
    from app.services.ai.provider import GroundedGenerationRequest, PromptEvidence

    evidence = (
        PromptEvidence(ref="E1", text="[SKILL] Python | Used for backend services."),
        PromptEvidence(
            ref="E2",
            text="[WORK_EXPERIENCE] QA Engineer | Built automated regression suites.",
        ),
    )

    def run(requirements: str) -> list[str]:
        response = DemoAIProvider().generate_grounded(
            GroundedGenerationRequest(
                job_context=f"Job title: Engineer\nRequirements: {requirements}",
                evidence=evidence,
                instructions="",
                max_statements=3,
            )
        )
        return [statement.text for statement in response.statements]

    python_job = run("Python; backend services")
    testing_job = run("automated regression suites")

    assert python_job != testing_job
    assert python_job[0].lower().startswith("python")
    assert "regression" in testing_job[0].lower()
