"""F08 is the dependency F09 fails closed without. This proves it closes.

`statement_review.contract.current_verification_provider` resolves F08 lazily
and falls back to `UnavailableVerificationProvider` when the module is absent,
so before F08 exists every review route answers 503. Installing F08 is what
makes F09 real — and nothing in either module's own tests can show that,
because each is tested against a fake.

These tests use the real wiring: no fakes, no dependency overrides beyond the
database. They are the evidence that the chain F11, F15 and F13 all sit on top
of actually closes.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

WORK_EVIDENCE = {
    "evidence_type": "work_experience",
    "title": "Associate QA Engineer",
    "organization": "Model N",
    "role": "Associate QA Engineer",
    "description": (
        "Built and maintained automated regression suites for revenue management "
        "software across two release trains."
    ),
}

COVERED_CLAIM = (
    "Built and maintained automated regression suites for revenue management software"
)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed(client: TestClient, email: str) -> tuple[str, str]:
    """A signed-in job seeker with one approved evidence record."""
    token = client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "full_name": "Chain Test"},
    ).json()["access_token"]
    evidence_id = client.post(
        "/api/evidence/", json=WORK_EVIDENCE, headers=_auth(token)
    ).json()["id"]
    approved = client.post(
        f"/api/evidence/{evidence_id}/approve", headers=_auth(token)
    )
    assert approved.status_code == 200, approved.text
    return token, evidence_id


def _verify(client: TestClient, token: str, text: str, evidence_id: str) -> dict:
    created = client.post(
        "/api/verification/statements",
        json={"text": text, "evidence_ids": [evidence_id]},
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text
    return created.json()


def test_f09_reads_a_real_f08_verdict_through_the_adapter(client: TestClient) -> None:
    """Without F08 installed this route answers 503. With it, a real verdict."""
    token, evidence_id = _seed(client, "chain1@example.edu")
    statement = _verify(client, token, COVERED_CLAIM, evidence_id)
    assert statement["status"] == "VERIFIED"

    review = client.get(
        f"/api/statement-review/{statement['statement_id']}", headers=_auth(token)
    )

    assert review.status_code == 200, review.text
    body = review.json()
    assert body["verification_status"] == "VERIFIED"
    assert body["verification_revision"] == statement["revision"]
    assert body["review_status"] == "UNREVIEWED"
    assert body["finalization_eligible"] is False


def test_approval_at_the_current_revision_makes_a_statement_available(
    client: TestClient,
) -> None:
    """The /approved list is what F11, F15 and F13 finalization consume."""
    token, evidence_id = _seed(client, "chain2@example.edu")
    statement = _verify(client, token, COVERED_CLAIM, evidence_id)
    review = client.get(
        f"/api/statement-review/{statement['statement_id']}", headers=_auth(token)
    ).json()

    decided = client.post(
        f"/api/statement-review/{statement['statement_id']}/decision",
        json={"decision": "APPROVED", "expected_revision": review["verification_revision"]},
        headers=_auth(token),
    )

    assert decided.status_code == 200, decided.text
    assert decided.json()["finalization_eligible"] is True

    approved = client.get("/api/statement-review/approved", headers=_auth(token))
    assert approved.status_code == 200
    assert [item["statement_id"] for item in approved.json()] == [
        statement["statement_id"]
    ]
    assert approved.json()[0]["verification_status"] == "VERIFIED"


def test_editing_the_evidence_revokes_an_existing_approval(client: TestClient) -> None:
    """The guarantee the whole trust chain rests on, exercised end to end.

    F08 derives the revision from the cited evidence, so editing that evidence
    moves it. F09 sees the stored approval no longer matches and reports STALE,
    and the statement leaves the approved list without anyone revoking it by
    hand.
    """
    token, evidence_id = _seed(client, "chain3@example.edu")
    statement = _verify(client, token, COVERED_CLAIM, evidence_id)
    review = client.get(
        f"/api/statement-review/{statement['statement_id']}", headers=_auth(token)
    ).json()
    client.post(
        f"/api/statement-review/{statement['statement_id']}/decision",
        json={"decision": "APPROVED", "expected_revision": review["verification_revision"]},
        headers=_auth(token),
    )
    assert len(client.get("/api/statement-review/approved", headers=_auth(token)).json()) == 1

    edited = client.patch(
        f"/api/evidence/{evidence_id}",
        json={"description": "Shadowed the regression suite owner."},
        headers=_auth(token),
    )
    assert edited.status_code == 200, edited.text

    after = client.get(
        f"/api/statement-review/{statement['statement_id']}", headers=_auth(token)
    ).json()

    assert after["verification_revision"] != review["verification_revision"]
    assert after["review_status"] == "STALE"
    assert after["finalization_eligible"] is False
    assert client.get("/api/statement-review/approved", headers=_auth(token)).json() == []


def test_an_unsupported_claim_cannot_be_approved_through_f09(
    client: TestClient,
) -> None:
    """F08 blocks fabrication at the gate F09 enforces (Req-Qual-Trace-2)."""
    token, evidence_id = _seed(client, "chain4@example.edu")
    statement = _verify(
        client, token, "Reduced regression runtime by 85%", evidence_id
    )
    assert statement["status"] == "UNSUPPORTED"

    review = client.get(
        f"/api/statement-review/{statement['statement_id']}", headers=_auth(token)
    ).json()
    decided = client.post(
        f"/api/statement-review/{statement['statement_id']}/decision",
        json={"decision": "APPROVED", "expected_revision": review["verification_revision"]},
        headers=_auth(token),
    )

    assert decided.status_code == 409
    assert client.get("/api/statement-review/approved", headers=_auth(token)).json() == []


def test_an_inferred_claim_can_be_approved_and_keeps_its_status(
    client: TestClient,
) -> None:
    """Only UNSUPPORTED is barred. INFERRED is the user's call, not blocked."""
    token, evidence_id = _seed(client, "chain5@example.edu")
    statement = _verify(
        client, token, "Improved release confidence for the billing organisation", evidence_id
    )
    assert statement["status"] == "INFERRED"

    review = client.get(
        f"/api/statement-review/{statement['statement_id']}", headers=_auth(token)
    ).json()
    decided = client.post(
        f"/api/statement-review/{statement['statement_id']}/decision",
        json={"decision": "APPROVED", "expected_revision": review["verification_revision"]},
        headers=_auth(token),
    )

    assert decided.status_code == 200, decided.text
    approved = client.get("/api/statement-review/approved", headers=_auth(token)).json()
    assert [item["verification_status"] for item in approved] == ["INFERRED"]
