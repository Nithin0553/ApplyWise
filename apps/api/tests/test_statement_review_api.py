"""F09 HTTP trust-boundary tests: auth, ownership, revisions and outage."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.modules.auth.models import User, UserRole
from app.modules.statement_review.contract import (
    CurrentVerifiedStatement,
    VerificationStatus,
    current_verification_provider,
)

PASSWORD = "synthetic-pass-123"


def register(client: TestClient, suffix: str) -> tuple[UUID, dict[str, str]]:
    result = client.post(
        "/auth/register",
        json={
            "email": f"review-{suffix}@example.org",
            "full_name": "Synthetic Reviewer",
            "password": PASSWORD,
        },
    )
    assert result.status_code == 201
    data = result.json()
    return UUID(data["user"]["id"]), {"Authorization": f"Bearer {data['access_token']}"}


class VerifiedFixtures:
    def __init__(self):
        self.current: dict[tuple[UUID, UUID], CurrentVerifiedStatement] = {}

    def add(
        self, user_id: UUID, statement_id: UUID,
        status: VerificationStatus = VerificationStatus.VERIFIED,
        revision: str = "verified-version-one",
    ) -> None:
        self.current[(user_id, statement_id)] = CurrentVerifiedStatement(
            user_id=user_id,
            statement_id=statement_id,
            text="Designed an API testing pipeline.",
            evidence_ids=(uuid4(),),
            status=status,
            revision=revision,
        )

    def get_current(
        self, *, user_id: UUID, statement_id: UUID
    ) -> CurrentVerifiedStatement | None:
        return self.current.get((user_id, statement_id))

    def list_current(self, *, user_id: UUID) -> tuple[CurrentVerifiedStatement, ...]:
        return tuple(item for (owner, _), item in self.current.items() if owner == user_id)


def enable_test_verifier(f08: VerifiedFixtures) -> None:
    app.dependency_overrides[current_verification_provider] = lambda: f08


def test_live_routes_fail_closed_without_real_f08(client: TestClient) -> None:
    _, headers = register(client, "offline")
    statement = str(uuid4())
    assert client.get("/api/statement-review/approved", headers=headers).status_code == 503
    assert client.get(f"/api/statement-review/{statement}", headers=headers).status_code == 503
    result = client.post(
        f"/api/statement-review/{statement}/decision",
        headers=headers,
        json={"decision": "APPROVED", "expected_revision": "verified-version-one"},
    )
    assert result.status_code == 503
    assert client.get(
        f"/api/statement-review/{statement}/history", headers=headers
    ).status_code == 503
    assert client.get("/api/statement-review/approved").status_code == 401


def test_authenticated_approved_review_persists_and_is_owner_isolated(
    client: TestClient,
) -> None:
    alice, alice_headers = register(client, "alice")
    bob, bob_headers = register(client, "bob")
    statement = uuid4()
    f08 = VerifiedFixtures()
    f08.add(alice, statement)
    enable_test_verifier(f08)

    pending = client.get(f"/api/statement-review/{statement}", headers=alice_headers)
    assert pending.status_code == 200
    assert pending.json()["review_status"] == "UNREVIEWED"
    assert not pending.json()["finalization_eligible"]

    selected = client.post(
        f"/api/statement-review/{statement}/decision",
        headers=alice_headers,
        json={"decision": "APPROVED", "expected_revision": "verified-version-one"},
    )
    assert selected.status_code == 200
    assert selected.json()["review_status"] == "APPROVED"
    assert selected.json()["finalization_eligible"]

    approved = client.get("/api/statement-review/approved", headers=alice_headers)
    assert approved.status_code == 200
    assert approved.json()[0]["statement_id"] == str(statement)
    assert approved.json()[0]["text"] == "Designed an API testing pipeline."
    assert client.get("/api/statement-review/approved", headers=bob_headers).json() == []

    # An unknown id and another user's id must look the same to Bob.
    for guess in (str(statement), str(uuid4())):
        denied = client.get(f"/api/statement-review/{guess}", headers=bob_headers)
        assert denied.status_code == 404
        denied = client.post(
            f"/api/statement-review/{guess}/decision",
            headers=bob_headers,
            json={"decision": "REJECTED", "expected_revision": "verified-version-one"},
        )
        assert denied.status_code == 404
    assert client.get(
        f"/api/statement-review/{statement}/history", headers=bob_headers
    ).status_code == 404

    history = client.get(
        f"/api/statement-review/{statement}/history", headers=alice_headers
    )
    assert history.status_code == 200
    assert [x["sequence"] for x in history.json()] == [1]


def test_replay_or_forged_flags_fail_validation_and_revision_mismatch(
    client: TestClient,
) -> None:
    user_id, headers = register(client, "forgery")
    statement = uuid4()
    f08 = VerifiedFixtures()
    f08.add(user_id, statement)
    enable_test_verifier(f08)

    bad = client.post(
        f"/api/statement-review/{statement}/decision",
        headers=headers,
        json={
            "decision": "APPROVED",
            "expected_revision": "verified-version-one",
            "verification_status": "VERIFIED",
            "approval_status": "APPROVED",
        },
    )
    assert bad.status_code == 422

    wrong = client.post(
        f"/api/statement-review/{statement}/decision",
        headers=headers,
        json={"decision": "APPROVED", "expected_revision": "old-version-token"},
    )
    assert wrong.status_code == 409
    assert client.get("/api/statement-review/approved", headers=headers).json() == []

    approved = client.post(
        f"/api/statement-review/{statement}/decision",
        headers=headers,
        json={"decision": "APPROVED", "expected_revision": "verified-version-one"},
    )
    assert approved.status_code == 200
    f08.add(user_id, statement, revision="verified-version-two")
    stale = client.get(f"/api/statement-review/{statement}", headers=headers)
    assert stale.json()["review_status"] == "STALE"
    assert stale.json()["finalization_eligible"] is False
    assert client.get("/api/statement-review/approved", headers=headers).json() == []


def test_unsupported_claim_can_be_rejected_but_never_approved(client: TestClient) -> None:
    user_id, headers = register(client, "unsupported")
    statement = uuid4()
    f08 = VerifiedFixtures()
    f08.add(user_id, statement, status=VerificationStatus.UNSUPPORTED)
    enable_test_verifier(f08)

    denied = client.post(
        f"/api/statement-review/{statement}/decision",
        headers=headers,
        json={"decision": "APPROVED", "expected_revision": "verified-version-one"},
    )
    assert denied.status_code == 409
    rejected = client.post(
        f"/api/statement-review/{statement}/decision",
        headers=headers,
        json={"decision": "REJECTED", "expected_revision": "verified-version-one"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "REJECTED"
    assert rejected.json()["finalization_eligible"] is False


def test_only_job_seekers_can_make_decisions(
    client: TestClient, db_session: Session,
) -> None:
    user_id, headers = register(client, "reviewer-role")
    record = db_session.get(User, user_id)
    assert record is not None
    record.role = UserRole.REVIEWER
    db_session.commit()
    f08 = VerifiedFixtures()
    f08.add(user_id, uuid4())
    enable_test_verifier(f08)
    response = client.get("/api/statement-review/approved", headers=headers)
    assert response.status_code == 403


def test_inferred_approval_preserves_classification_and_blocks_stale_revision(
    client: TestClient,
) -> None:
    user_id, headers = register(client, "inferred")
    statement = uuid4()
    f08 = VerifiedFixtures()
    f08.add(user_id, statement, status=VerificationStatus.INFERRED)
    enable_test_verifier(f08)
    approved = client.post(
        f"/api/statement-review/{statement}/decision",
        headers=headers,
        json={"decision": "APPROVED", "expected_revision": "verified-version-one"},
    )
    assert approved.status_code == 200
    assert approved.json()["verification_status"] == "INFERRED"
    assert approved.json()["finalization_eligible"] is True
    current = client.get("/api/statement-review/approved", headers=headers)
    assert current.status_code == 200
    assert current.json()[0]["verification_status"] == "INFERRED"

    f08.add(user_id, statement, status=VerificationStatus.UNSUPPORTED,
            revision="unsupported-updated-revision")
    assert client.get("/api/statement-review/approved", headers=headers).json() == []
    assert client.get(f"/api/statement-review/{statement}", headers=headers).json()[
        "finalization_eligible"
    ] is False
