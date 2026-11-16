"""F09 carry-forward: reuse an approval the user already made.

Regenerating a resume mints new statement ids for claims whose wording did
not change, so the user was asked to approve the same sentence, backed by the
same evidence, again and again. The revision is derived from the material, so
identical material produces an identical revision whatever the id; carrying an
approval across that boundary reuses a decision rather than inventing one.

What these tests pin is the boundary itself: one character of difference in
the claim, in the evidence it cites, or in the classification, and nothing is
carried.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from app.modules.statement_review.contract import (
    CurrentVerifiedStatement,
    VerificationStatus,
)
from app.modules.statement_review.models import ReviewDecision
from app.modules.statement_review.schemas import EffectiveReviewStatus
from app.modules.statement_review.service import StatementReviewService


@dataclass
class _Verifier:
    """Stands in for F08, returning whatever revision the test sets."""

    items: dict[UUID, CurrentVerifiedStatement]

    def get_current(
        self, *, user_id: UUID, statement_id: UUID
    ) -> CurrentVerifiedStatement | None:
        return self.items.get(statement_id)


def _statement(
    user_id: UUID,
    statement_id: UUID,
    *,
    text: str,
    revision: str,
    evidence_id: UUID,
    status: VerificationStatus = VerificationStatus.VERIFIED,
) -> CurrentVerifiedStatement:
    return CurrentVerifiedStatement(
        user_id=user_id,
        statement_id=statement_id,
        text=text,
        evidence_ids=(evidence_id,),
        status=status,
        revision=revision,
    )


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def evidence_id() -> UUID:
    return uuid4()


def _approve(service: StatementReviewService, user_id: UUID, statement_id: UUID, revision: str):
    return service.decide(
        user_id=user_id,
        statement_id=statement_id,
        decision=ReviewDecision.APPROVED,
        expected_revision=revision,
    )


def test_identical_material_carries_the_approval(db_session, user_id, evidence_id):
    old_id, new_id = uuid4(), uuid4()
    revision = "v1-" + ("a" * 32)
    verifier = _Verifier({
        old_id: _statement(user_id, old_id, text="Built regression suites.",
                           revision=revision, evidence_id=evidence_id),
        new_id: _statement(user_id, new_id, text="Built regression suites.",
                           revision=revision, evidence_id=evidence_id),
    })
    service = StatementReviewService(db_session, verifier)

    _approve(service, user_id, old_id, revision)

    # A regenerated resume: same sentence, same evidence, brand new id.
    result = service.carry_forward(user_id=user_id, statement_id=new_id)

    assert result.review_status == EffectiveReviewStatus.APPROVED
    assert result.finalization_eligible is True
    assert result.reviewed_revision == revision

    # Immutable history differentiates the click that gave approval from a
    # later identical claim's inherited approval.
    clicked = service.history(user_id=user_id, statement_id=old_id)
    carried = service.history(user_id=user_id, statement_id=new_id)
    assert len(clicked) == len(carried) == 1
    assert clicked[0].carried_from_statement_id is None
    assert carried[0].carried_from_statement_id == old_id


def test_changed_wording_is_not_carried(db_session, user_id, evidence_id):
    old_id, new_id = uuid4(), uuid4()
    verifier = _Verifier({
        old_id: _statement(user_id, old_id, text="Built regression suites.",
                           revision="v1-" + ("a" * 32), evidence_id=evidence_id),
        # Different wording means a different derived revision.
        new_id: _statement(user_id, new_id, text="Built extensive regression suites.",
                           revision="v1-" + ("b" * 32), evidence_id=evidence_id),
    })
    service = StatementReviewService(db_session, verifier)

    _approve(service, user_id, old_id, "v1-" + ("a" * 32))

    result = service.carry_forward(user_id=user_id, statement_id=new_id)

    assert result.review_status == EffectiveReviewStatus.UNREVIEWED
    assert result.finalization_eligible is False


def test_another_users_approval_is_never_carried(db_session, user_id, evidence_id):
    stranger = uuid4()
    their_id, mine = uuid4(), uuid4()
    revision = "v1-" + ("c" * 32)
    verifier = _Verifier({
        their_id: _statement(stranger, their_id, text="Built regression suites.",
                             revision=revision, evidence_id=evidence_id),
        mine: _statement(user_id, mine, text="Built regression suites.",
                         revision=revision, evidence_id=evidence_id),
    })
    service = StatementReviewService(db_session, verifier)

    _approve(service, stranger, their_id, revision)

    result = service.carry_forward(user_id=user_id, statement_id=mine)

    assert result.review_status == EffectiveReviewStatus.UNREVIEWED
    assert result.finalization_eligible is False


def test_a_rejection_is_not_carried_as_an_approval(db_session, user_id, evidence_id):
    old_id, new_id = uuid4(), uuid4()
    revision = "v1-" + ("d" * 32)
    verifier = _Verifier({
        old_id: _statement(user_id, old_id, text="Built regression suites.",
                           revision=revision, evidence_id=evidence_id),
        new_id: _statement(user_id, new_id, text="Built regression suites.",
                           revision=revision, evidence_id=evidence_id),
    })
    service = StatementReviewService(db_session, verifier)

    service.decide(user_id=user_id, statement_id=old_id,
                   decision=ReviewDecision.REJECTED, expected_revision=revision)

    result = service.carry_forward(user_id=user_id, statement_id=new_id)

    assert result.review_status == EffectiveReviewStatus.UNREVIEWED
    assert result.finalization_eligible is False


def test_carrying_twice_does_not_stack_events(db_session, user_id, evidence_id):
    old_id, new_id = uuid4(), uuid4()
    revision = "v1-" + ("e" * 32)
    verifier = _Verifier({
        old_id: _statement(user_id, old_id, text="Built regression suites.",
                           revision=revision, evidence_id=evidence_id),
        new_id: _statement(user_id, new_id, text="Built regression suites.",
                           revision=revision, evidence_id=evidence_id),
    })
    service = StatementReviewService(db_session, verifier)
    _approve(service, user_id, old_id, revision)

    service.carry_forward(user_id=user_id, statement_id=new_id)
    history_after_first = service.history(user_id=user_id, statement_id=new_id)
    service.carry_forward(user_id=user_id, statement_id=new_id)
    history_after_second = service.history(user_id=user_id, statement_id=new_id)

    assert len(history_after_first) == 1
    assert len(history_after_second) == 1
    assert history_after_second[0].carried_from_statement_id == old_id


def test_direct_review_after_a_carry_has_no_inherited_origin(
    db_session, user_id, evidence_id
):
    old_id, new_id = uuid4(), uuid4()
    revision = "v1-" + ("f" * 32)
    verifier = _Verifier({
        old_id: _statement(user_id, old_id, text="Automated quality checks.",
                           revision=revision, evidence_id=evidence_id),
        new_id: _statement(user_id, new_id, text="Automated quality checks.",
                           revision=revision, evidence_id=evidence_id),
    })
    service = StatementReviewService(db_session, verifier)
    _approve(service, user_id, old_id, revision)
    service.carry_forward(user_id=user_id, statement_id=new_id)
    service.decide(user_id=user_id, statement_id=new_id,
                   decision=ReviewDecision.REJECTED, expected_revision=revision)
    events = service.history(user_id=user_id, statement_id=new_id)
    assert len(events) == 2
    assert events[0].carried_from_statement_id == old_id
    assert events[1].carried_from_statement_id is None
