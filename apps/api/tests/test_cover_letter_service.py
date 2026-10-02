"""F11 unit tests: cover letters drafted only from approved statements."""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.modules.generation.cover_letter_schemas import (
    ApprovedStatement,
    CoverLetterParagraph,
    CoverLetterRequest,
)
from app.modules.generation.cover_letter_service import CoverLetterService
from app.modules.generation.errors import (
    GenerationUnavailableError,
    MalformedProviderResponseError,
)
from app.services.ai.demo import DemoAIProvider
from app.services.ai.provider import RawParagraph
from app.services.ai.stub import StubAIProvider
from tests.fixtures.cover_letter_fixtures import (
    EVIDENCE_ONE_ID,
    EVIDENCE_TWO_ID,
    JOB_CONTEXT,
    STATEMENT_ONE,
    STATEMENT_ONE_ID,
    STATEMENT_TWO_ID,
    USER_ID,
    FakeCoverLetterProvider,
    build_request,
    paragraphs,
    unavailable_provider,
)

FIXED_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def make_service(provider: object) -> CoverLetterService:
    counter = count(1)
    return CoverLetterService(
        provider,  # type: ignore[arg-type]
        id_factory=lambda: UUID(int=next(counter)),
        clock=lambda: FIXED_TIME,
    )


# --- happy path -----------------------------------------------------------


def test_paragraph_carries_both_statement_and_evidence_provenance() -> None:
    provider = FakeCoverLetterProvider(
        paragraphs(RawParagraph(text="I test Python backends.", cited_refs=("S1",)))
    )

    draft = make_service(provider).generate(build_request())

    assert len(draft.paragraphs) == 1
    paragraph = draft.paragraphs[0]
    assert paragraph.statement_ids == (STATEMENT_ONE_ID,)
    assert paragraph.evidence_ids == (EVIDENCE_ONE_ID,)
    assert draft.provider == "fake"
    assert draft.generated_at == FIXED_TIME
    assert draft.tone == "professional"


def test_evidence_ids_are_merged_without_duplicates() -> None:
    provider = FakeCoverLetterProvider(
        paragraphs(RawParagraph(text="Testing and automation.", cited_refs=("S1", "S2")))
    )

    draft = make_service(provider).generate(build_request())

    paragraph = draft.paragraphs[0]
    assert paragraph.statement_ids == (STATEMENT_ONE_ID, STATEMENT_TWO_ID)
    # S1 and S2 share evidence E1; it appears once.
    assert paragraph.evidence_ids == (EVIDENCE_ONE_ID, EVIDENCE_TWO_ID)


def test_provider_sees_statement_refs_and_tone_but_no_identifiers() -> None:
    provider = FakeCoverLetterProvider(paragraphs())

    make_service(provider).generate(build_request(tone="warm"))

    sent = provider.last_request
    assert sent is not None
    assert [item.ref for item in sent.statements] == ["S1", "S2", "S3"]
    assert sent.tone == "warm"
    assert "Software Engineer in Test" in sent.job_context
    assert "already approved" in sent.instructions
    body = " ".join(item.text for item in sent.statements)
    assert str(STATEMENT_ONE_ID) not in body
    assert str(EVIDENCE_ONE_ID) not in body


# --- untrusted provider output --------------------------------------------


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        (RawParagraph(text="No citation.", cited_refs=()), "no approved statement cited"),
        (RawParagraph(text="  ", cited_refs=("S1",)), "empty text"),
        (RawParagraph(text="Invented.", cited_refs=("S9",)), "cites unknown"),
        (RawParagraph(text="Half true.", cited_refs=("S1", "S9")), "cites unknown"),
        (RawParagraph(text="x" * 801, cited_refs=("S1",)), "text too long"),
    ],
)
def test_ungrounded_paragraphs_are_rejected(raw: RawParagraph, reason: str) -> None:
    provider = FakeCoverLetterProvider(paragraphs(raw))

    draft = make_service(provider).generate(build_request())

    assert draft.paragraphs == ()
    assert len(draft.rejected) == 1
    assert reason in draft.rejected[0].reason


def test_good_paragraphs_survive_alongside_rejected_ones() -> None:
    provider = FakeCoverLetterProvider(
        paragraphs(
            RawParagraph(text="Grounded paragraph.", cited_refs=("S2",)),
            RawParagraph(text="Flattering invention.", cited_refs=("S7",)),
        )
    )

    draft = make_service(provider).generate(build_request())

    assert [item.text for item in draft.paragraphs] == ["Grounded paragraph."]
    assert len(draft.rejected) == 1


def test_max_paragraphs_is_enforced() -> None:
    provider = FakeCoverLetterProvider(
        paragraphs(
            RawParagraph(text="One.", cited_refs=("S1",)),
            RawParagraph(text="Two.", cited_refs=("S2",)),
            RawParagraph(text="Three.", cited_refs=("S3",)),
        )
    )

    draft = make_service(provider).generate(build_request(max_paragraphs=2))

    assert len(draft.paragraphs) == 2
    assert draft.rejected[0].reason == "exceeds max_paragraphs"


# --- failing safely -------------------------------------------------------


def test_provider_error_raises_generation_unavailable() -> None:
    with pytest.raises(GenerationUnavailableError):
        make_service(unavailable_provider()).generate(build_request())


def test_unexpected_provider_crash_raises_generation_unavailable() -> None:
    with pytest.raises(GenerationUnavailableError):
        make_service(FakeCoverLetterProvider(TimeoutError("slow"))).generate(build_request())


@pytest.mark.parametrize("bad", [None, "text", {"paragraphs": []}])
def test_malformed_response_raises_malformed_error(bad: object) -> None:
    with pytest.raises(MalformedProviderResponseError):
        make_service(FakeCoverLetterProvider(bad)).generate(build_request())


# --- the F11 hard rules ---------------------------------------------------


def test_drafted_paragraphs_are_candidates_and_not_exportable() -> None:
    provider = FakeCoverLetterProvider(
        paragraphs(RawParagraph(text="Grounded.", cited_refs=("S1",)))
    )

    paragraph = make_service(provider).generate(build_request()).paragraphs[0]

    assert paragraph.status == "CANDIDATE"
    assert paragraph.verification_status == "PENDING"
    assert paragraph.approval_status == "UNREVIEWED"
    assert paragraph.export_eligible is False


def test_an_unsupported_statement_cannot_enter_a_cover_letter() -> None:
    with pytest.raises(ValidationError):
        ApprovedStatement(
            statement_id=STATEMENT_ONE_ID,
            text="Improved release quality by 40%.",
            evidence_ids=(EVIDENCE_ONE_ID,),
            verification_status="UNSUPPORTED",  # type: ignore[arg-type]
        )


def test_an_unapproved_statement_cannot_enter_a_cover_letter() -> None:
    with pytest.raises(ValidationError):
        ApprovedStatement(
            statement_id=STATEMENT_ONE_ID,
            text="Waiting for the user.",
            evidence_ids=(EVIDENCE_ONE_ID,),
            verification_status="VERIFIED",
            approval_status="UNREVIEWED",  # type: ignore[arg-type]
        )


def test_a_paragraph_cannot_exist_without_provenance() -> None:
    with pytest.raises(ValidationError):
        CoverLetterParagraph(
            paragraph_id=UUID(int=9),
            text="Floating prose.",
            statement_ids=(),
            evidence_ids=(),
        )


# --- request validation ---------------------------------------------------


def test_request_requires_at_least_one_approved_statement() -> None:
    with pytest.raises(ValidationError):
        CoverLetterRequest(user_id=USER_ID, job_context=JOB_CONTEXT, approved_statements=())


def test_request_rejects_duplicate_statements() -> None:
    with pytest.raises(ValidationError):
        CoverLetterRequest(
            user_id=USER_ID,
            job_context=JOB_CONTEXT,
            approved_statements=(STATEMENT_ONE, STATEMENT_ONE),
        )


def test_request_rejects_out_of_range_paragraph_counts() -> None:
    with pytest.raises(ValidationError):
        build_request(max_paragraphs=1)


# --- bundled providers ----------------------------------------------------


def test_stub_provider_drafts_deterministically() -> None:
    service = CoverLetterService(StubAIProvider())
    request = build_request()

    first = service.generate(request)
    second = service.generate(request)

    assert [p.text for p in first.paragraphs] == [p.text for p in second.paragraphs]
    assert first.provider == "stub"
    assert first.rejected == ()


def test_demo_provider_is_job_aware_and_its_ungrounded_flattery_is_rejected() -> None:
    draft = CoverLetterService(DemoAIProvider()).generate(build_request())

    opening = draft.paragraphs[0].text
    assert "Software Engineer in Test" in opening
    assert "Example Corp" in opening
    reasons = " ".join(item.reason for item in draft.rejected)
    assert "cites unknown statement reference" in reasons
    assert "no approved statement cited" in reasons
    for paragraph in draft.paragraphs:
        assert paragraph.statement_ids and paragraph.evidence_ids


def test_demo_provider_tone_changes_the_opening() -> None:
    service = CoverLetterService(DemoAIProvider())

    professional = service.generate(build_request(tone="professional")).paragraphs[0].text
    warm = service.generate(build_request(tone="warm")).paragraphs[0].text

    assert professional != warm
