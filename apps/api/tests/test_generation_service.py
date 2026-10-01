"""F07 unit tests: grounded generation with provenance.

Every test uses a fake provider and fixed UUIDs, so no network call is made
and results never change between runs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.modules.generation.errors import (
    GenerationUnavailableError,
    MalformedProviderResponseError,
)
from app.modules.generation.schemas import CandidateStatement, GenerationRequest, JobContext
from app.modules.generation.service import GenerationService
from app.services.ai.provider import RawStatement
from tests.fixtures.generation_fixtures import (
    EVIDENCE_ONE,
    EVIDENCE_ONE_ID,
    EVIDENCE_TWO_ID,
    JOB_CONTEXT,
    USER_ID,
    FakeAIProvider,
    build_request,
    response_with,
    unavailable_provider,
)

FIXED_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def make_service(provider: FakeAIProvider) -> GenerationService:
    """Service with predictable IDs and a frozen clock."""
    counter = count(1)
    return GenerationService(
        provider,
        id_factory=lambda: UUID(int=next(counter)),
        clock=lambda: FIXED_TIME,
    )


# --- happy path -----------------------------------------------------------


def test_statement_carries_provenance_to_source_evidence() -> None:
    provider = FakeAIProvider(
        response_with(RawStatement(text="Automated regression suites.", cited_refs=("E1",)))
    )

    result = make_service(provider).generate(build_request())

    assert len(result.statements) == 1
    statement = result.statements[0]
    assert statement.text == "Automated regression suites."
    assert statement.evidence_ids == (EVIDENCE_ONE_ID,)
    assert result.provider == "fake"
    assert result.generated_at == FIXED_TIME
    assert result.rejected == ()


def test_statement_may_cite_several_evidence_items() -> None:
    provider = FakeAIProvider(
        response_with(RawStatement(text="Python test automation.", cited_refs=("E1", "E2")))
    )

    result = make_service(provider).generate(build_request())

    assert result.statements[0].evidence_ids == (EVIDENCE_ONE_ID, EVIDENCE_TWO_ID)


def test_duplicate_citations_are_collapsed() -> None:
    provider = FakeAIProvider(
        response_with(RawStatement(text="Testing work.", cited_refs=("E1", "e1 ")))
    )

    result = make_service(provider).generate(build_request())

    assert result.statements[0].evidence_ids == (EVIDENCE_ONE_ID,)


# --- what the provider is allowed to see ----------------------------------


def test_provider_receives_short_refs_and_never_database_ids() -> None:
    provider = FakeAIProvider(response_with())

    make_service(provider).generate(build_request())

    sent = provider.last_request
    assert sent is not None
    assert [item.ref for item in sent.evidence] == ["E1", "E2"]
    prompt_text = " ".join(item.text for item in sent.evidence)
    assert str(EVIDENCE_ONE_ID) not in prompt_text
    assert "Model N" in prompt_text
    assert "Software Engineer in Test" in sent.job_context
    assert "Do not invent" in sent.instructions


# --- untrusted provider output --------------------------------------------


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        (RawStatement(text="No citation here.", cited_refs=()), "no evidence cited"),
        (RawStatement(text="   ", cited_refs=("E1",)), "empty text"),
        (RawStatement(text="Invented source.", cited_refs=("E9",)), "cites unknown"),
        (RawStatement(text="Mixed.", cited_refs=("E1", "E9")), "cites unknown"),
        (RawStatement(text="x" * 501, cited_refs=("E1",)), "text too long"),
    ],
)
def test_unsafe_statements_are_rejected_not_returned(raw: RawStatement, reason: str) -> None:
    provider = FakeAIProvider(response_with(raw))

    result = make_service(provider).generate(build_request())

    assert result.statements == ()
    assert len(result.rejected) == 1
    assert reason in result.rejected[0].reason


def test_good_statements_survive_alongside_rejected_ones() -> None:
    provider = FakeAIProvider(
        response_with(
            RawStatement(text="Valid statement.", cited_refs=("E2",)),
            RawStatement(text="Hallucinated source.", cited_refs=("E7",)),
        )
    )

    result = make_service(provider).generate(build_request())

    assert [s.text for s in result.statements] == ["Valid statement."]
    assert len(result.rejected) == 1


def test_max_statements_is_enforced() -> None:
    provider = FakeAIProvider(
        response_with(
            RawStatement(text="One.", cited_refs=("E1",)),
            RawStatement(text="Two.", cited_refs=("E2",)),
        )
    )

    result = make_service(provider).generate(build_request(max_statements=1))

    assert len(result.statements) == 1
    assert result.rejected[0].reason == "exceeds max_statements"


# --- failing safely -------------------------------------------------------


def test_provider_error_raises_generation_unavailable() -> None:
    with pytest.raises(GenerationUnavailableError):
        make_service(unavailable_provider()).generate(build_request())


def test_unexpected_provider_crash_raises_generation_unavailable() -> None:
    provider = FakeAIProvider(TimeoutError("network timeout"))

    with pytest.raises(GenerationUnavailableError):
        make_service(provider).generate(build_request())


@pytest.mark.parametrize("bad_response", [None, "some text", {"statements": []}])
def test_malformed_response_raises_malformed_error(bad_response: object) -> None:
    provider = FakeAIProvider(bad_response)

    with pytest.raises(MalformedProviderResponseError):
        make_service(provider).generate(build_request())


def test_garbage_inside_a_valid_response_is_rejected_per_statement() -> None:
    provider = FakeAIProvider(response_with("not a statement object"))  # type: ignore[arg-type]

    result = make_service(provider).generate(build_request())

    assert result.statements == ()
    assert result.rejected[0].reason == "malformed statement"


# --- the F07 hard rule ----------------------------------------------------


def test_generated_statements_are_never_verified_approved_or_exportable() -> None:
    provider = FakeAIProvider(
        response_with(RawStatement(text="Candidate text.", cited_refs=("E1",)))
    )

    statement = make_service(provider).generate(build_request()).statements[0]

    assert statement.status == "CANDIDATE"
    assert statement.verification_status == "PENDING"
    assert statement.approval_status == "UNREVIEWED"
    assert statement.export_eligible is False


def test_a_candidate_cannot_be_constructed_as_exportable() -> None:
    with pytest.raises(ValidationError):
        CandidateStatement(
            statement_id=UUID(int=99),
            text="Trying to skip verification.",
            evidence_ids=(EVIDENCE_ONE_ID,),
            export_eligible=True,  # type: ignore[arg-type]
        )


def test_a_statement_cannot_exist_without_provenance() -> None:
    with pytest.raises(ValidationError):
        CandidateStatement(
            statement_id=UUID(int=98),
            text="No source.",
            evidence_ids=(),
        )


# --- request validation ---------------------------------------------------


def test_request_requires_at_least_one_approved_evidence_item() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(user_id=USER_ID, job_context=JOB_CONTEXT, approved_evidence=())


def test_request_rejects_duplicate_evidence_ids() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(
            user_id=USER_ID,
            job_context=JOB_CONTEXT,
            approved_evidence=(EVIDENCE_ONE, EVIDENCE_ONE),
        )


def test_request_rejects_out_of_range_max_statements() -> None:
    with pytest.raises(ValidationError):
        build_request(max_statements=0)


def test_job_context_requires_a_description() -> None:
    with pytest.raises(ValidationError):
        JobContext(job_title="QA Engineer", description="")
