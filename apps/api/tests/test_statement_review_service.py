"""F09 service tests: F08 is always authoritative, never caller-supplied labels."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.modules.statement_review.contract import (
    CurrentVerifiedStatement,
    VerificationStatus,
)
from app.modules.statement_review.models import ReviewDecision, StatementReviewEventRecord
from app.modules.statement_review.schemas import EffectiveReviewStatus
from app.modules.statement_review.service import (
    ReviewNotEligibleError,
    ReviewNotFoundError,
    StaleVerificationError,
    StatementReviewService,
)


class FakeF08:
    """Only test fixtures can mint verification objects; never HTTP clients."""

    def __init__(self) -> None:
        self.records: dict[tuple[UUID, UUID], CurrentVerifiedStatement] = {}

    def set(
        self, user: UUID, statement: UUID, *,
        revision: str = "version-one-verified",
        status: VerificationStatus = VerificationStatus.VERIFIED,
        text: str = "Built REST API tests in Python.",
        evidence_ids: tuple[UUID, ...] | None = None,
    ) -> CurrentVerifiedStatement:
        result = CurrentVerifiedStatement(
            user_id=user, statement_id=statement, text=text,
            evidence_ids=evidence_ids or (uuid4(),),
            status=status, revision=revision,
        )
        self.records[(user, statement)] = result
        return result

    def get_current(
        self, *, user_id: UUID, statement_id: UUID
    ) -> CurrentVerifiedStatement | None:
        return self.records.get((user_id, statement_id))

    def list_current(self, *, user_id: UUID) -> tuple[CurrentVerifiedStatement, ...]:
        return tuple(value for (owner, _), value in self.records.items() if owner == user_id)


def test_approving_current_verified_statement_is_durable_and_idempotent(
    db_session: Session,
) -> None:
    f08 = FakeF08()
    owner, statement = uuid4(), uuid4()
    f08.set(owner, statement)
    service = StatementReviewService(db_session, f08)

    assert service.get_review(
        user_id=owner, statement_id=statement
    ).review_status == EffectiveReviewStatus.UNREVIEWED

    approved = service.decide(
        user_id=owner, statement_id=statement,
        decision=ReviewDecision.APPROVED,
        expected_revision="version-one-verified",
    )
    db_session.commit()
    assert approved.finalization_eligible
    assert approved.review_status == EffectiveReviewStatus.APPROVED

    again = service.decide(
        user_id=owner, statement_id=statement,
        decision=ReviewDecision.APPROVED,
        expected_revision="version-one-verified",
    )
    db_session.commit()
    assert again.finalization_eligible
    assert len(service.history(user_id=owner, statement_id=statement)) == 1
    assert len(service.list_approved_statements(user_id=owner)) == 1
    assert service.list_approved_statements(user_id=owner)[0].text == (
        "Built REST API tests in Python."
    )


def test_reject_reapprove_history_preserves_append_order(db_session: Session) -> None:
    f08, owner, statement = FakeF08(), uuid4(), uuid4()
    f08.set(owner, statement)
    service = StatementReviewService(db_session, f08)

    for value in (ReviewDecision.REJECTED, ReviewDecision.APPROVED, ReviewDecision.REJECTED):
        service.decide(
            user_id=owner, statement_id=statement,
            decision=value, expected_revision="version-one-verified",
        )
        db_session.commit()
    events = service.history(user_id=owner, statement_id=statement)
    assert [event.sequence for event in events] == [1, 2, 3]
    assert [event.decision for event in events] == [
        ReviewDecision.REJECTED, ReviewDecision.APPROVED, ReviewDecision.REJECTED,
    ]
    assert not service.list_approved_statements(user_id=owner)
    assert len(db_session.query(StatementReviewEventRecord).all()) == 3


def test_changed_text_or_evidence_revision_revokes_eligibility(db_session: Session) -> None:
    f08, owner, statement = FakeF08(), uuid4(), uuid4()
    first = f08.set(owner, statement)
    service = StatementReviewService(db_session, f08)
    service.decide(
        user_id=owner, statement_id=statement,
        decision=ReviewDecision.APPROVED, expected_revision=first.revision,
    )
    db_session.commit()

    # F08 must rotate the revision if statement text changes or F02 evidence
    # is edited, unconfirmed, or replaced. F09 does not trust its old event.
    f08.set(
        owner, statement,
        revision="version-two-new-evidence",
        text="Changed API testing claim.",
        evidence_ids=(uuid4(),),
    )
    stale = service.get_review(user_id=owner, statement_id=statement)
    assert stale.review_status == EffectiveReviewStatus.STALE
    assert stale.reviewed_revision == first.revision
    assert not stale.finalization_eligible
    assert service.list_approved_statements(user_id=owner) == ()

    with pytest.raises(StaleVerificationError):
        service.decide(
            user_id=owner, statement_id=statement,
            decision=ReviewDecision.APPROVED,
            expected_revision=first.revision,
        )

    new_revision = service.decide(
        user_id=owner, statement_id=statement,
        decision=ReviewDecision.APPROVED,
        expected_revision="version-two-new-evidence",
    )
    db_session.commit()
    assert new_revision.finalization_eligible
    assert [event.sequence for event in service.history(
        user_id=owner, statement_id=statement
    )] == [1, 2]


@pytest.mark.parametrize(
    "status",
    [VerificationStatus.INFERRED, VerificationStatus.UNSUPPORTED],
)
def test_unverified_or_unsupported_claim_cannot_gain_approval(
    db_session: Session, status: VerificationStatus,
) -> None:
    f08, owner, statement = FakeF08(), uuid4(), uuid4()
    f08.set(owner, statement, status=status)
    service = StatementReviewService(db_session, f08)
    with pytest.raises(ReviewNotEligibleError):
        service.decide(
            user_id=owner, statement_id=statement,
            decision=ReviewDecision.APPROVED,
            expected_revision="version-one-verified",
        )
    rejected = service.decide(
        user_id=owner, statement_id=statement,
        decision=ReviewDecision.REJECTED,
        expected_revision="version-one-verified",
    )
    db_session.commit()
    assert rejected.review_status == EffectiveReviewStatus.REJECTED
    assert not rejected.finalization_eligible
    assert service.list_approved_statements(user_id=owner) == ()


def test_foreign_statement_probing_never_discloses_owner(db_session: Session) -> None:
    f08, owner, stranger, statement = FakeF08(), uuid4(), uuid4(), uuid4()
    f08.set(owner, statement)
    service = StatementReviewService(db_session, f08)
    with pytest.raises(ReviewNotFoundError):
        service.get_review(user_id=stranger, statement_id=statement)
    with pytest.raises(ReviewNotFoundError):
        service.decide(
            user_id=stranger, statement_id=statement,
            decision=ReviewDecision.REJECTED,
            expected_revision="version-one-verified",
        )
    assert service.list_approved_statements(user_id=stranger) == ()
    assert service.history(user_id=owner, statement_id=statement) == ()


def test_source_reclassified_unsupported_revokes_old_approved_status(
    db_session: Session,
) -> None:
    f08, owner, statement = FakeF08(), uuid4(), uuid4()
    prior = f08.set(owner, statement)
    service = StatementReviewService(db_session, f08)
    service.decide(
        user_id=owner, statement_id=statement,
        decision=ReviewDecision.APPROVED, expected_revision=prior.revision,
    )
    db_session.commit()

    f08.set(
        owner, statement,
        revision="version-two-invalidated",
        status=VerificationStatus.UNSUPPORTED,
    )
    assert not service.get_review(
        user_id=owner, statement_id=statement
    ).finalization_eligible
    assert service.list_approved_statements(user_id=owner) == ()
    with pytest.raises(ReviewNotEligibleError):
        service.decide(
            user_id=owner, statement_id=statement,
            decision=ReviewDecision.APPROVED, expected_revision="version-two-invalidated",
        )
