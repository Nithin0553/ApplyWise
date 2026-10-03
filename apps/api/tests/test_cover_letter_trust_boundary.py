"""F11 trust boundary: a statement the user does not own never reaches a provider.

These tests cover the rule Nithin asked for on PR #16 — a forged, unowned or
unapproved statement must not reach the provider — at the level where the rule
lives, so it is enforced and covered before F09's persistence exists rather
than after. ``select_approved_statements`` is what the route will call once
there is a store; ``FakeStatementStore`` stands in for that store here.

The last test covers the interim measure: while the route still accepts
statements from the client, it must not be served in production at all.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.modules.generation.cover_letter_contracts import (
    StatementNotApprovedError,
    select_approved_statements,
)
from app.modules.generation.cover_letter_schemas import ApprovedStatement
from tests.fixtures.cover_letter_fixtures import (
    STATEMENT_ONE,
    STATEMENT_THREE,
    STATEMENT_TWO,
    USER_ID,
)
from tests.test_generation_api import COVER_LETTER_PAYLOAD, _auth, _register

OTHER_USER_ID = UUID("00000000-0000-0000-0000-0000000000bb")


class FakeStatementStore:
    """Stands in for F09: returns only the statements a user actually owns."""

    def __init__(self, by_user: dict[UUID, tuple[ApprovedStatement, ...]]) -> None:
        self._by_user = by_user
        self.asked_for: list[UUID] = []

    def list_approved_statements(self, *, user_id: UUID) -> Sequence[ApprovedStatement]:
        self.asked_for.append(user_id)
        return self._by_user.get(user_id, ())


def store() -> FakeStatementStore:
    return FakeStatementStore(
        {
            USER_ID: (STATEMENT_ONE, STATEMENT_TWO, STATEMENT_THREE),
            OTHER_USER_ID: (),
        }
    )


# --- selection -------------------------------------------------------------


def test_selecting_owned_statements_returns_them_in_the_callers_order() -> None:
    resolved = select_approved_statements(
        store(),
        user_id=USER_ID,
        statement_ids=[STATEMENT_TWO.statement_id, STATEMENT_ONE.statement_id],
    )

    assert [item.statement_id for item in resolved] == [
        STATEMENT_TWO.statement_id,
        STATEMENT_ONE.statement_id,
    ]


def test_the_statements_come_from_the_store_not_the_caller() -> None:
    """The caller supplies ids. The text and approval state come from the store.

    This is the whole point of the seam: a caller cannot smuggle in different
    wording, or a different verification status, by sending a fuller object.
    """
    resolved = select_approved_statements(
        store(), user_id=USER_ID, statement_ids=[STATEMENT_ONE.statement_id]
    )

    assert resolved[0] is STATEMENT_ONE


def test_a_forged_statement_id_is_refused() -> None:
    """An id nobody ever approved resolves to nothing, so the call fails."""
    with pytest.raises(StatementNotApprovedError):
        select_approved_statements(store(), user_id=USER_ID, statement_ids=[uuid4()])


def test_another_users_statement_is_refused() -> None:
    """Asking as OTHER_USER_ID for a statement owned by USER_ID fails.

    Crucially it fails with the same error as a missing id, so a caller cannot
    use the response to discover that someone else's statement exists.
    """
    with pytest.raises(StatementNotApprovedError):
        select_approved_statements(
            store(), user_id=OTHER_USER_ID, statement_ids=[STATEMENT_ONE.statement_id]
        )


def test_the_store_is_queried_for_the_authenticated_user_only() -> None:
    fake = store()

    select_approved_statements(
        fake, user_id=USER_ID, statement_ids=[STATEMENT_ONE.statement_id]
    )

    assert fake.asked_for == [USER_ID]


def test_one_bad_id_refuses_the_whole_selection() -> None:
    """A partially valid selection is refused in full, never silently trimmed.

    Drafting from fewer statements than the user chose would misrepresent what
    they asked for, so this fails rather than quietly dropping the bad id.
    """
    with pytest.raises(StatementNotApprovedError):
        select_approved_statements(
            store(),
            user_id=USER_ID,
            statement_ids=[STATEMENT_ONE.statement_id, uuid4()],
        )


def test_an_empty_selection_is_refused() -> None:
    with pytest.raises(StatementNotApprovedError):
        select_approved_statements(store(), user_id=USER_ID, statement_ids=[])


def test_a_duplicated_selection_is_refused() -> None:
    with pytest.raises(StatementNotApprovedError):
        select_approved_statements(
            store(),
            user_id=USER_ID,
            statement_ids=[STATEMENT_ONE.statement_id, STATEMENT_ONE.statement_id],
        )


# --- interim measure: not served in production -----------------------------


def test_cover_letter_route_is_not_served_in_production(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """While the route trusts client-supplied statements, production must not serve it."""
    token, _ = _register(client, "prod-gate@example.edu")
    monkeypatch.setattr(settings, "app_env", "production")

    response = client.post(
        "/api/generation/cover-letter/preview",
        json=COVER_LETTER_PAYLOAD,
        headers=_auth(token),
    )

    assert response.status_code == 404


def test_statement_generation_is_still_served_in_production(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gate is specific to F11: F07's own route resolves nothing client-side."""
    token, _ = _register(client, "prod-f07@example.edu")
    monkeypatch.setattr(settings, "app_env", "production")

    response = client.post(
        "/api/generation/preview?provider=stub",
        json={
            "job_context": COVER_LETTER_PAYLOAD["job_context"],
            "approved_evidence": [
                {
                    "evidence_id": "11111111-1111-1111-1111-111111111111",
                    "evidence_type": "SKILL",
                    "title": "Python",
                    "skill_name": "Python",
                    "proficiency": "Advanced",
                }
            ],
            "max_statements": 3,
        },
        headers=_auth(token),
    )

    assert response.status_code == 200
