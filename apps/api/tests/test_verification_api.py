"""Tests for the F08 endpoints, through the real stack.

F01 supplies identity, F02 supplies the evidence. A caller sends a claim and
evidence ids; it can never send a verdict.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

ENDPOINT = "/api/verification/statements"

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


def _register(client: TestClient, email: str) -> str:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "full_name": "Test Person"},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _evidence(client: TestClient, token: str, *, approve: bool = True) -> str:
    created = client.post("/api/evidence/", json=WORK_EVIDENCE, headers=_auth(token))
    assert created.status_code == 201, created.text
    evidence_id = created.json()["id"]
    if approve:
        approved = client.post(
            f"/api/evidence/{evidence_id}/approve", headers=_auth(token)
        )
        assert approved.status_code == 200, approved.text
    return evidence_id


def _submit(client: TestClient, token: str, text: str, evidence_id: str):  # noqa: ANN202
    return client.post(
        ENDPOINT, json={"text": text, "evidence_ids": [evidence_id]}, headers=_auth(token)
    )


# --- the route exists ------------------------------------------------------


def test_the_verification_routes_are_mounted(client: TestClient) -> None:
    """A router written but never included serves nothing; F04 shipped that way."""
    paths = client.get("/openapi.json").json()["paths"]

    assert ENDPOINT in paths


# --- authentication and ownership -----------------------------------------


def test_submission_requires_authentication(client: TestClient) -> None:
    response = client.post(
        ENDPOINT, json={"text": "A claim", "evidence_ids": [str(uuid4())]}
    )

    assert response.status_code == 401


def test_a_foreign_statement_is_not_readable(client: TestClient) -> None:
    owner = _register(client, "owner-f08@example.edu")
    evidence_id = _evidence(client, owner)
    statement_id = _submit(client, owner, "Built regression suites", evidence_id).json()[
        "statement_id"
    ]
    stranger = _register(client, "stranger-f08@example.edu")

    response = client.get(f"{ENDPOINT}/{statement_id}", headers=_auth(stranger))

    assert response.status_code == 404


def test_a_foreign_statement_and_a_missing_one_are_indistinguishable(
    client: TestClient,
) -> None:
    owner = _register(client, "owner2-f08@example.edu")
    evidence_id = _evidence(client, owner)
    statement_id = _submit(client, owner, "Built regression suites", evidence_id).json()[
        "statement_id"
    ]
    stranger = _register(client, "stranger2-f08@example.edu")

    foreign = client.get(f"{ENDPOINT}/{statement_id}", headers=_auth(stranger))
    missing = client.get(f"{ENDPOINT}/{uuid4()}", headers=_auth(stranger))

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


def test_a_statement_is_absent_from_another_users_list(client: TestClient) -> None:
    owner = _register(client, "owner3-f08@example.edu")
    evidence_id = _evidence(client, owner)
    _submit(client, owner, "Built regression suites", evidence_id)
    stranger = _register(client, "stranger3-f08@example.edu")

    listed = client.get(ENDPOINT, headers=_auth(stranger))

    assert listed.status_code == 200
    assert listed.json() == []


# --- what a caller cannot assert ------------------------------------------


def test_a_client_cannot_submit_its_own_verdict(client: TestClient) -> None:
    """``extra="forbid"`` means a forged status or revision is a 422, not silence."""
    token = _register(client, "forge-f08@example.edu")
    evidence_id = _evidence(client, token)

    response = client.post(
        ENDPOINT,
        json={
            "text": "Reduced runtime by 85%",
            "evidence_ids": [evidence_id],
            "status": "VERIFIED",
            "revision": "forged-revision",
        },
        headers=_auth(token),
    )

    assert response.status_code == 422


def test_an_unsourced_figure_is_classified_unsupported(client: TestClient) -> None:
    token = _register(client, "figure-f08@example.edu")
    evidence_id = _evidence(client, token)

    body = _submit(client, token, "Reduced regression runtime by 85%", evidence_id).json()

    assert body["status"] == "UNSUPPORTED"
    assert body["export_eligible"] is False
    assert any(f["reason"] == "FIGURE_NOT_IN_EVIDENCE" for f in body["findings"])


def test_a_covered_claim_is_verified_and_exportable(client: TestClient) -> None:
    token = _register(client, "covered-f08@example.edu")
    evidence_id = _evidence(client, token)

    body = _submit(
        client,
        token,
        "Built and maintained automated regression suites for revenue management software",
        evidence_id,
    ).json()

    assert body["status"] == "VERIFIED"
    assert body["export_eligible"] is True


def test_unapproved_evidence_cannot_support_a_claim(client: TestClient) -> None:
    token = _register(client, "unapproved-f08@example.edu")
    evidence_id = _evidence(client, token, approve=False)

    body = _submit(client, token, "Built regression suites", evidence_id).json()

    assert body["status"] == "UNSUPPORTED"
    assert any(f["reason"] == "EVIDENCE_NOT_AVAILABLE" for f in body["findings"])


def test_foreign_evidence_cannot_support_a_claim(client: TestClient) -> None:
    """A claim citing someone else's evidence is judged against nothing."""
    owner = _register(client, "evowner-f08@example.edu")
    evidence_id = _evidence(client, owner)
    stranger = _register(client, "evstranger-f08@example.edu")

    body = _submit(client, stranger, "Built regression suites", evidence_id).json()

    assert body["status"] == "UNSUPPORTED"
    assert any(f["reason"] == "EVIDENCE_NOT_AVAILABLE" for f in body["findings"])


# --- the invalidation guarantee, end to end -------------------------------


def test_unapproving_the_evidence_changes_the_verdict_and_the_revision(
    client: TestClient,
) -> None:
    """The statement is untouched. F09's whole invalidation model rests on this."""
    token = _register(client, "invalidate-f08@example.edu")
    evidence_id = _evidence(client, token)
    first = _submit(
        client,
        token,
        "Built and maintained automated regression suites for revenue management software",
        evidence_id,
    ).json()
    assert first["status"] == "VERIFIED"

    unconfirmed = client.post(
        f"/api/evidence/{evidence_id}/unconfirm", headers=_auth(token)
    )
    assert unconfirmed.status_code == 200, unconfirmed.text

    after = client.get(
        f"{ENDPOINT}/{first['statement_id']}", headers=_auth(token)
    ).json()

    assert after["status"] == "UNSUPPORTED"
    assert after["revision"] != first["revision"]
    assert after["export_eligible"] is False


def test_editing_the_evidence_rotates_the_revision(client: TestClient) -> None:
    token = _register(client, "editev-f08@example.edu")
    evidence_id = _evidence(client, token)
    first = _submit(client, token, "Built regression suites", evidence_id).json()

    edited = client.patch(
        f"/api/evidence/{evidence_id}",
        json={"description": "Shadowed the regression suite owner."},
        headers=_auth(token),
    )
    assert edited.status_code == 200, edited.text

    after = client.get(
        f"{ENDPOINT}/{first['statement_id']}", headers=_auth(token)
    ).json()

    assert after["revision"] != first["revision"]


# --- withdrawal ------------------------------------------------------------


def test_owner_can_withdraw_a_statement(client: TestClient) -> None:
    token = _register(client, "withdraw-f08@example.edu")
    evidence_id = _evidence(client, token)
    statement_id = _submit(client, token, "Built regression suites", evidence_id).json()[
        "statement_id"
    ]

    removed = client.delete(f"{ENDPOINT}/{statement_id}", headers=_auth(token))

    assert removed.status_code == 204
    assert client.get(f"{ENDPOINT}/{statement_id}", headers=_auth(token)).status_code == 404


def test_cannot_withdraw_another_users_statement(client: TestClient) -> None:
    owner = _register(client, "wowner-f08@example.edu")
    evidence_id = _evidence(client, owner)
    statement_id = _submit(client, owner, "Built regression suites", evidence_id).json()[
        "statement_id"
    ]
    stranger = _register(client, "wstranger-f08@example.edu")

    response = client.delete(f"{ENDPOINT}/{statement_id}", headers=_auth(stranger))

    assert response.status_code == 404
    assert client.get(f"{ENDPOINT}/{statement_id}", headers=_auth(owner)).status_code == 200
