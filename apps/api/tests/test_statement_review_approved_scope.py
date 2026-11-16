"""F09: approved-statement list is bounded and scoped to the current resume."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.modules.statement_review.contract import CurrentVerifiedStatement, VerificationStatus
from app.modules.statement_review.models import ReviewDecision
from app.modules.statement_review.service import StatementReviewService


@dataclass
class _Verifier:
    items: dict[UUID, CurrentVerifiedStatement]

    def get_current(self, *, user_id: UUID, statement_id: UUID):
        item = self.items.get(statement_id)
        return item if item and item.user_id == user_id else None

    def list_current(self, *, user_id: UUID):
        return tuple(item for item in self.items.values() if item.user_id == user_id)


def _claim(user_id: UUID, statement_id: UUID, evidence_id: UUID, n: int):
    return CurrentVerifiedStatement(
        user_id=user_id,
        statement_id=statement_id,
        text=f"Verified evidence-backed claim {n}",
        evidence_ids=(evidence_id,),
        status=VerificationStatus.VERIFIED,
        revision=f"v1-{n:032x}",
    )


def test_unfiltered_history_is_bounded_and_paginated(db_session):
    user, evidence = uuid4(), uuid4()
    ids = [uuid4() for _ in range(25)]
    verifier = _Verifier({
        sid: _claim(user, sid, evidence, n) for n, sid in enumerate(ids)
    })
    service = StatementReviewService(db_session, verifier)
    for n, sid in enumerate(ids):
        service.decide(user_id=user, statement_id=sid,
                       decision=ReviewDecision.APPROVED, expected_revision=f"v1-{n:032x}")

    first = service.list_approved_statements(user_id=user)
    second = service.list_approved_statements(user_id=user, offset=20)
    assert len(first) == 20
    assert len(second) == 5
    assert [row.statement_id for row in first] == list(reversed(ids[5:]))
    assert [row.statement_id for row in second] == list(reversed(ids[:5]))
    assert not {row.statement_id for row in first}.intersection(
        row.statement_id for row in second
    )


def test_explicit_f08_ids_return_older_approvals_without_unrelated_history(db_session):
    user, stranger, evidence = uuid4(), uuid4(), uuid4()
    ids = [uuid4() for _ in range(24)]
    foreign_id = uuid4()
    verifier = _Verifier({
        **{sid: _claim(user, sid, evidence, n) for n, sid in enumerate(ids)},
        foreign_id: _claim(stranger, foreign_id, evidence, 99),
    })
    service = StatementReviewService(db_session, verifier)
    for n, sid in enumerate(ids):
        service.decide(user_id=user, statement_id=sid,
                       decision=ReviewDecision.APPROVED, expected_revision=f"v1-{n:032x}")
    service.decide(user_id=stranger, statement_id=foreign_id,
                   decision=ReviewDecision.APPROVED, expected_revision=f"v1-{99:032x}")

    selected = service.list_approved_statements(
        user_id=user, statement_ids=(ids[0], foreign_id, ids[1], ids[0])
    )
    assert [row.statement_id for row in selected] == ids[:2]

    # A changed F08 revision immediately invalidates the prior approval.
    verifier.items[ids[0]] = _claim(user, ids[0], evidence, 70)
    current = service.list_approved_statements(user_id=user, statement_ids=(ids[0], ids[1]))
    assert [row.statement_id for row in current] == [ids[1]]


def test_invalid_service_windows_are_rejected(db_session):
    service = StatementReviewService(db_session, _Verifier({}))
    user = uuid4()
    for kwargs in ({"limit": 21}, {"limit": 0}, {"offset": -1},
                   {"offset": 10_001}, {"statement_ids": tuple(uuid4() for _ in range(21))}):
        try:
            service.list_approved_statements(user_id=user, **kwargs)
        except ValueError:
            continue
        raise AssertionError(f"Expected invalid query to fail: {kwargs.keys()}")
