"""A failing network provider must not take generation down with it.

The point of the fallback is availability, not trust: whatever the backup
returns still goes through the generation service's citation validation and
F08's classification, so these tests check substitution and logging rather
than anything about the content.
"""

from __future__ import annotations

import logging

import pytest

from app.services.ai.fallback import FallbackAIProvider
from app.services.ai.provider import (
    AIProviderError,
    CoverLetterRequest,
    CoverLetterResponse,
    GroundedGenerationRequest,
    GroundedGenerationResponse,
    PromptEvidence,
    PromptStatement,
    RawParagraph,
    RawStatement,
)

GENERATION = GroundedGenerationRequest(
    job_context="Software Engineer in Test",
    evidence=(PromptEvidence(ref="E1", text="Built regression suites."),),
    instructions="",
    max_statements=3,
)
COVER_LETTER = CoverLetterRequest(
    job_context="Software Engineer in Test",
    statements=(PromptStatement(ref="S1", text="Built regression suites."),),
    instructions="",
    tone="professional",
    max_paragraphs=2,
)


class Working:
    name = "primary"

    def generate_grounded(self, request):  # noqa: ANN001, ARG002
        return GroundedGenerationResponse(
            statements=(RawStatement(text="from primary", cited_refs=("E1",)),)
        )

    def generate_cover_letter(self, request):  # noqa: ANN001, ARG002
        return CoverLetterResponse(
            paragraphs=(RawParagraph(text="from primary", cited_refs=("S1",)),)
        )


class Failing:
    name = "anthropic"

    def generate_grounded(self, request):  # noqa: ANN001, ARG002
        raise AIProviderError("timed out")

    def generate_cover_letter(self, request):  # noqa: ANN001, ARG002
        raise AIProviderError("timed out")


class Backup:
    name = "stub"

    def generate_grounded(self, request):  # noqa: ANN001, ARG002
        return GroundedGenerationResponse(
            statements=(RawStatement(text="from backup", cited_refs=("E1",)),)
        )

    def generate_cover_letter(self, request):  # noqa: ANN001, ARG002
        return CoverLetterResponse(
            paragraphs=(RawParagraph(text="from backup", cited_refs=("S1",)),)
        )


def test_a_working_primary_is_used_unchanged() -> None:
    provider = FallbackAIProvider(Working(), Backup())

    result = provider.generate_grounded(GENERATION)

    assert result.statements[0].text == "from primary"


def test_a_failing_primary_falls_back_for_generation() -> None:
    provider = FallbackAIProvider(Failing(), Backup())

    result = provider.generate_grounded(GENERATION)

    assert result.statements[0].text == "from backup"


def test_a_failing_primary_falls_back_for_cover_letters() -> None:
    provider = FallbackAIProvider(Failing(), Backup())

    result = provider.generate_cover_letter(COVER_LETTER)

    assert result.paragraphs[0].text == "from backup"


def test_the_substitution_is_logged_so_it_cannot_pass_as_model_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A silent fallback would let scripted text be mistaken for a real model."""
    provider = FallbackAIProvider(Failing(), Backup())

    with caplog.at_level(logging.WARNING, logger="app.services.ai.fallback"):
        provider.generate_grounded(GENERATION)

    # getMessage() interpolates the args; record.message is already formatted.
    messages = [record.getMessage() for record in caplog.records]
    assert any("anthropic" in text and "stub" in text for text in messages), messages


def test_the_declared_name_is_the_provider_that_was_asked_for() -> None:
    assert FallbackAIProvider(Failing(), Backup()).name == "anthropic"


def test_a_backup_failure_is_not_swallowed() -> None:
    """If both fail the caller must see it, not receive empty output."""
    provider = FallbackAIProvider(Failing(), Failing())

    with pytest.raises(AIProviderError):
        provider.generate_grounded(GENERATION)
