"""F15 unit tests: defensibility signals and interview questions.

The service takes no provider and no database, so every test here is a pure
comparison between a statement and the evidence it cites.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from uuid import UUID

import pytest

from app.modules.generation.interview_schemas import (
    MAX_QUESTIONS_PER_STATEMENT,
    DefensibilityRisk,
    InterviewPrepRequest,
    SignalCode,
)
from app.modules.generation.interview_service import (
    InterviewPreparationService,
    MissingEvidenceForStatementError,
)
from tests.fixtures.interview_fixtures import (
    EVIDENCE_BY_ID,
    INFERRED_THIN,
    SOURCED_FIGURE,
    UNSOURCED_FIGURE,
    UNSOURCED_LEADERSHIP,
    UNSOURCED_SUPERLATIVE,
    USER_ID,
    WELL_SUPPORTED,
    WORK_EVIDENCE_ID,
    statement,
)

FIXED_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def make_service() -> InterviewPreparationService:
    counter = count(1)
    return InterviewPreparationService(
        id_factory=lambda: UUID(int=next(counter)),
        clock=lambda: FIXED_TIME,
    )


def prepare_one(approved):  # type: ignore[no-untyped-def]
    request = InterviewPrepRequest(approved_statements=(approved,))
    result = make_service().prepare(
        request, user_id=USER_ID, evidence_by_id=EVIDENCE_BY_ID
    )
    return result.items[0]


def codes(item) -> set[SignalCode]:  # type: ignore[no-untyped-def]
    return {signal.code for signal in item.signals}


# --- risk classification --------------------------------------------------


def test_a_claim_the_evidence_covers_is_supported() -> None:
    item = prepare_one(WELL_SUPPORTED)

    assert item.risk is DefensibilityRisk.SUPPORTED
    assert item.signals == ()


def test_a_figure_absent_from_the_evidence_is_hard_to_defend() -> None:
    item = prepare_one(UNSOURCED_FIGURE)

    assert item.risk is DefensibilityRisk.HARD_TO_DEFEND
    assert SignalCode.UNSOURCED_NUMBER in codes(item)
    assert any("85%" in signal.detail for signal in item.signals)


def test_a_figure_the_evidence_records_is_not_flagged() -> None:
    """The check must not punish a user for quoting their own evidence."""
    item = prepare_one(SOURCED_FIGURE)

    assert SignalCode.UNSOURCED_NUMBER not in codes(item)
    assert item.risk is DefensibilityRisk.SUPPORTED


def test_a_leadership_claim_without_a_stated_role_is_hard_to_defend() -> None:
    item = prepare_one(UNSOURCED_LEADERSHIP)

    assert item.risk is DefensibilityRisk.HARD_TO_DEFEND
    assert SignalCode.UNSOURCED_LEADERSHIP in codes(item)


def test_a_leadership_claim_backed_by_a_role_is_not_flagged() -> None:
    """Evidence that names a role and an employer answers "led" on its own."""
    backed = statement(20, "Led the regression effort", (WORK_EVIDENCE_ID,))

    assert SignalCode.UNSOURCED_LEADERSHIP not in codes(prepare_one(backed))


def test_a_superlative_the_evidence_does_not_make_is_hard_to_defend() -> None:
    item = prepare_one(UNSOURCED_SUPERLATIVE)

    assert item.risk is DefensibilityRisk.HARD_TO_DEFEND
    assert SignalCode.UNSOURCED_SUPERLATIVE in codes(item)


def test_thin_inferred_single_source_claims_only_need_detail() -> None:
    """None of these are fabrication, so none of them is HARD_TO_DEFEND."""
    item = prepare_one(INFERRED_THIN)

    assert item.risk is DefensibilityRisk.NEEDS_DETAIL
    assert codes(item) == {
        SignalCode.THIN_EVIDENCE,
        SignalCode.INFERRED_STATEMENT,
        SignalCode.SINGLE_SOURCE,
    }


# --- questions ------------------------------------------------------------


def test_every_statement_gets_questions_even_when_fully_supported() -> None:
    item = prepare_one(WELL_SUPPORTED)

    assert len(item.questions) >= 1
    assert all(question.statement_id == item.statement_id for question in item.questions)


def test_a_flagged_figure_produces_a_question_about_its_source() -> None:
    item = prepare_one(UNSOURCED_FIGURE)

    asked = " ".join(question.text for question in item.questions)
    assert "85%" in asked
    assert "where does the figure" in asked.lower()


def test_question_count_is_bounded() -> None:
    """A statement that trips every rule must not produce an endless list."""
    everything = statement(
        21,
        "Led the only team to cut cost by 99% and by 12345 hours",
        (EVIDENCE_BY_ID[WORK_EVIDENCE_ID].evidence_id,),
    )

    item = prepare_one(everything)

    assert len(item.questions) <= MAX_QUESTIONS_PER_STATEMENT


# --- supporting points ----------------------------------------------------


def test_supporting_points_come_from_the_cited_evidence() -> None:
    item = prepare_one(WELL_SUPPORTED)

    joined = " ".join(item.supporting_points)
    assert "Associate QA Engineer" in joined
    assert "Model N" in joined


# --- guarantees -----------------------------------------------------------


def test_the_result_is_advisory_and_carries_no_approval_state() -> None:
    result = make_service().prepare(
        InterviewPrepRequest(approved_statements=(UNSOURCED_FIGURE,)),
        user_id=USER_ID,
        evidence_by_id=EVIDENCE_BY_ID,
    )

    assert result.advisory_only is True
    dumped = result.model_dump()
    assert "approval_status" not in dumped
    assert "export_eligible" not in dumped
    assert "verification_status" not in str(dumped)


def test_unresolved_evidence_is_refused_rather_than_analysed_partially() -> None:
    orphan = statement(22, "Claim with no resolved evidence", (UUID(int=999),))

    with pytest.raises(MissingEvidenceForStatementError):
        prepare_one(orphan)


def test_results_follow_the_order_the_caller_listed() -> None:
    request = InterviewPrepRequest(
        approved_statements=(UNSOURCED_FIGURE, WELL_SUPPORTED)
    )

    result = make_service().prepare(
        request, user_id=USER_ID, evidence_by_id=EVIDENCE_BY_ID
    )

    assert [item.statement_id for item in result.items] == [
        UNSOURCED_FIGURE.statement_id,
        WELL_SUPPORTED.statement_id,
    ]
    assert result.hard_to_defend_count == 1
