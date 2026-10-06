"""F07 trust boundary: evidence the user does not own never reaches a provider.

``resolve_approved_evidence`` is the rule the preview route applies before any
generation happens. It is tested here against a fake store rather than a
database, so the rule itself is pinned down independently of F02's storage:
the fake returns what F02 promises to return, and nothing else.

The end-to-end counterpart, which drives real F02 records through the HTTP
route, is in test_generation_api.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

import pytest

from app.modules.generation.resolution import (
    EvidenceNotApprovedError,
    resolve_approved_evidence,
)

OWNER_ID = UUID("00000000-0000-0000-0000-0000000000aa")
OTHER_USER_ID = UUID("00000000-0000-0000-0000-0000000000bb")

WORK_ID = UUID("11111111-1111-1111-1111-111111111111")
SKILL_ID = UUID("22222222-2222-2222-2222-222222222222")


@dataclass
class FakeContext:
    """Mirrors F02's EvidenceGroundingContext, structurally."""

    evidence_id: UUID
    evidence_type: str
    title: str
    organization: str | None = None
    role: str | None = None
    location: str | None = None
    description: str | None = None
    skill_name: str | None = None
    proficiency: str | None = None
    credential: str | None = None
    start_date: date | None = None
    end_date: date | None = None


WORK = FakeContext(
    evidence_id=WORK_ID,
    evidence_type="work_experience",
    title="Associate QA Engineer",
    organization="Model N",
    role="Associate QA Engineer",
    description="Built automated regression suites.",
)
SKILL = FakeContext(
    evidence_id=SKILL_ID,
    evidence_type="skill",
    title="Python",
    skill_name="Python",
    proficiency="Advanced",
)


class FakeEvidenceStore:
    """Stands in for F02: returns only approved evidence the user owns."""

    def __init__(self, by_user: dict[UUID, tuple[FakeContext, ...]]) -> None:
        self._by_user = by_user
        self.asked_for: list[UUID] = []

    def list_grounding_contexts(self, *, user_id: UUID) -> Sequence[FakeContext]:
        self.asked_for.append(user_id)
        return self._by_user.get(user_id, ())


def store() -> FakeEvidenceStore:
    return FakeEvidenceStore({OWNER_ID: (WORK, SKILL), OTHER_USER_ID: ()})


# --- resolution ------------------------------------------------------------


def test_owned_ids_resolve_in_the_callers_order() -> None:
    resolved = resolve_approved_evidence(
        store(), user_id=OWNER_ID, evidence_ids=[SKILL_ID, WORK_ID]
    )

    assert [item.evidence_id for item in resolved] == [SKILL_ID, WORK_ID]


def test_content_comes_from_the_store_not_the_caller() -> None:
    """The caller sends ids. Text and structured fields come from F02.

    This is the point of the boundary: there is no field a caller could use to
    alter what a statement will be grounded in.
    """
    resolved = resolve_approved_evidence(store(), user_id=OWNER_ID, evidence_ids=[SKILL_ID])

    assert resolved[0].title == "Python"
    assert resolved[0].skill_name == "Python"
    assert resolved[0].proficiency == "Advanced"
    assert resolved[0].evidence_type == "skill"


def test_a_fabricated_evidence_id_is_refused() -> None:
    with pytest.raises(EvidenceNotApprovedError):
        resolve_approved_evidence(store(), user_id=OWNER_ID, evidence_ids=[uuid4()])


def test_another_users_evidence_is_refused() -> None:
    """Asking as OTHER_USER_ID for evidence owned by OWNER_ID fails.

    It fails with the same error as a fabricated id, so the response cannot be
    used to discover that someone else's evidence exists.
    """
    with pytest.raises(EvidenceNotApprovedError):
        resolve_approved_evidence(store(), user_id=OTHER_USER_ID, evidence_ids=[WORK_ID])


def test_the_store_is_queried_for_the_authenticated_user_only() -> None:
    fake = store()

    resolve_approved_evidence(fake, user_id=OWNER_ID, evidence_ids=[WORK_ID])

    assert fake.asked_for == [OWNER_ID]


def test_one_bad_id_refuses_the_whole_selection() -> None:
    """A partly valid selection fails rather than being silently trimmed.

    Generating from fewer items than the user chose would change what the
    statements rest on without anyone noticing.
    """
    with pytest.raises(EvidenceNotApprovedError):
        resolve_approved_evidence(
            store(), user_id=OWNER_ID, evidence_ids=[WORK_ID, uuid4()]
        )


def test_an_empty_selection_is_refused() -> None:
    with pytest.raises(EvidenceNotApprovedError):
        resolve_approved_evidence(store(), user_id=OWNER_ID, evidence_ids=[])


def test_a_duplicated_selection_is_refused() -> None:
    with pytest.raises(EvidenceNotApprovedError):
        resolve_approved_evidence(
            store(), user_id=OWNER_ID, evidence_ids=[WORK_ID, WORK_ID]
        )


def test_unapproved_evidence_is_invisible_to_f07() -> None:
    """F07 relies on F02 returning approved records only.

    An unconfirmed record is simply absent from list_grounding_contexts, so it
    cannot be selected. This test pins that assumption down: if F02 ever began
    returning unapproved records, resolution would start succeeding here and
    this test would fail.
    """
    empty = FakeEvidenceStore({OWNER_ID: ()})

    with pytest.raises(EvidenceNotApprovedError):
        resolve_approved_evidence(empty, user_id=OWNER_ID, evidence_ids=[WORK_ID])
