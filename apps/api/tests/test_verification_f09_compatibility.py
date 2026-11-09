"""F08 must drop into F09's provider slot without either module importing the other.

F09 declares ``CurrentVerificationProvider`` and ``CurrentVerifiedStatement`` in
``app/modules/statement_review/contract.py``. That module is not on ``main``
yet (it arrives with the F09 PR), so this file restates the shape F09 requires
and checks F08 against it. When F09 merges, the restatement here can be
replaced by an import and these assertions keep their meaning.

The point is not that the classes are the same object. It is that F09 reads
only attributes and compares only StrEnum values, so a structurally identical
F08 satisfies it — the same technique F07's ``resolution`` uses to consume F02
without depending on it.
"""

from __future__ import annotations

import inspect
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from app.modules.verification.analysis import classify, derive_revision
from app.modules.verification.contracts import (
    VerificationProvider,
    VerificationStatus,
    VerifiedStatement,
)
from tests.fixtures.verification_fixtures import APPROVED, USER_ID, WORK_ID


class F09VerificationStatus(StrEnum):
    """Restated from statement_review/contract.py."""

    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNSUPPORTED = "UNSUPPORTED"


class F09CurrentVerificationProvider(Protocol):
    """Restated from statement_review/contract.py."""

    def get_current(self, *, user_id: UUID, statement_id: UUID): ...  # noqa: ANN201

    def list_current(self, *, user_id: UUID): ...  # noqa: ANN201


REQUIRED_FIELDS = {
    "statement_id",
    "user_id",
    "text",
    "evidence_ids",
    "status",
    "revision",
}


def _statement() -> VerifiedStatement:
    text = "Built and maintained automated regression suites for revenue management software"
    ids = (WORK_ID,)
    status, findings = classify(text=text, evidence_ids=ids, approved=APPROVED)
    return VerifiedStatement(
        statement_id=uuid4(),
        user_id=USER_ID,
        text=text,
        evidence_ids=ids,
        status=status,
        revision=derive_revision(
            text=text, evidence_ids=ids, approved=APPROVED, status=status
        ),
        findings=findings,
    )


def test_f08_carries_every_field_f09_reads() -> None:
    assert REQUIRED_FIELDS <= set(VerifiedStatement.model_fields)


def test_the_provider_methods_match_f09s_signatures() -> None:
    for name in ("get_current", "list_current"):
        ours = inspect.signature(getattr(VerificationProvider, name))
        theirs = inspect.signature(getattr(F09CurrentVerificationProvider, name))
        assert list(ours.parameters) == list(theirs.parameters), name
        for parameter in list(ours.parameters.values())[1:]:
            assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, name


def test_status_values_compare_equal_across_the_two_modules() -> None:
    """StrEnum is what lets F09 compare our status without importing ours."""
    for ours, theirs in zip(VerificationStatus, F09VerificationStatus, strict=True):
        assert ours.value == theirs.value
        assert ours == theirs.value


def test_f09s_export_gate_reads_our_status_correctly() -> None:
    """F09 gates on ``!= UNSUPPORTED``; check that against a real verdict."""
    statement = _statement()

    assert statement.status != F09VerificationStatus.UNSUPPORTED
    assert statement.status.value in {"VERIFIED", "INFERRED"}


def test_the_revision_satisfies_f09s_field_constraints() -> None:
    """F09 validates revision as 8-128 chars matching ^[a-zA-Z0-9._:-]+$."""
    import re

    revision = _statement().revision

    assert 8 <= len(revision) <= 128
    assert re.fullmatch(r"^[a-zA-Z0-9._:-]+$", revision)


def test_findings_are_additive_and_do_not_break_f09() -> None:
    """F09 ignores ``findings``; it must not be required to know about it."""
    statement = _statement()
    f09_view = {name: getattr(statement, name) for name in REQUIRED_FIELDS}

    assert set(f09_view) == REQUIRED_FIELDS
    assert statement.findings  # present for the verification UI, unused by F09
