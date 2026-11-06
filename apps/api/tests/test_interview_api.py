"""Tests for the F15 preparation endpoint.

These run through the real stack: F01 for authentication and F02 for the
evidence. The statements are caller-supplied, because F09 has no store yet,
but the evidence they cite is read from F02 — so these tests check the half of
the trust boundary that is already enforced, and pin the gate that covers the
half that is not.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

ENDPOINT = "/api/interview/preparation"

WORK_EVIDENCE = {
    "evidence_type": "work_experience",
    "title": "Associate QA Engineer",
    "organization": "Model N",
    "role": "Associate QA Engineer",
    "description": "Built and maintained automated regression suites for billing paths.",
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


def _add_evidence(client: TestClient, token: str, *, approve: bool) -> str:
    created = client.post("/api/evidence/", json=WORK_EVIDENCE, headers=_auth(token))
    assert created.status_code == 201, created.text
    evidence_id = created.json()["id"]
    if approve:
        approved = client.post(
            f"/api/evidence/{evidence_id}/approve", headers=_auth(token)
        )
        assert approved.status_code == 200, approved.text
    return evidence_id


def _payload(evidence_id: str, text: str = "Reduced regression runtime by 85%") -> dict:
    return {
        "approved_statements": [
            {
                "statement_id": str(uuid4()),
                "text": text,
                "evidence_ids": [evidence_id],
                "verification_status": "VERIFIED",
            }
        ]
    }


# --- the route exists -----------------------------------------------------


def test_the_preparation_route_is_mounted(client: TestClient) -> None:
    """A router that is written but never included serves nothing.

    F04's analysis router shipped unmounted and every call returned 404 while
    its own unit tests passed, so this asserts the path is actually published.
    """
    paths = client.get("/openapi.json").json()["paths"]

    assert ENDPOINT in paths


# --- authentication and ownership -----------------------------------------


def test_preparation_requires_authentication(client: TestClient) -> None:
    response = client.post(ENDPOINT, json=_payload(str(uuid4())))

    assert response.status_code == 401


def test_evidence_owned_by_another_user_is_refused(client: TestClient) -> None:
    owner = _register(client, "owner-f15@example.edu")
    evidence_id = _add_evidence(client, owner, approve=True)
    stranger = _register(client, "stranger-f15@example.edu")

    response = client.post(ENDPOINT, json=_payload(evidence_id), headers=_auth(stranger))

    assert response.status_code == 404


def test_a_foreign_id_and_a_missing_id_are_indistinguishable(client: TestClient) -> None:
    """The response must not reveal that an evidence id exists for someone else."""
    owner = _register(client, "owner2-f15@example.edu")
    evidence_id = _add_evidence(client, owner, approve=True)
    stranger = _register(client, "stranger2-f15@example.edu")

    foreign = client.post(ENDPOINT, json=_payload(evidence_id), headers=_auth(stranger))
    missing = client.post(ENDPOINT, json=_payload(str(uuid4())), headers=_auth(stranger))

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


def test_unapproved_evidence_is_refused(client: TestClient) -> None:
    token = _register(client, "unapproved-f15@example.edu")
    evidence_id = _add_evidence(client, token, approve=False)

    response = client.post(ENDPOINT, json=_payload(evidence_id), headers=_auth(token))

    assert response.status_code == 404


# --- the advice itself ----------------------------------------------------


def test_an_unsourced_figure_is_reported_as_hard_to_defend(client: TestClient) -> None:
    token = _register(client, "figure-f15@example.edu")
    evidence_id = _add_evidence(client, token, approve=True)

    response = client.post(ENDPOINT, json=_payload(evidence_id), headers=_auth(token))

    assert response.status_code == 200, response.text
    body = response.json()
    item = body["items"][0]
    assert item["risk"] == "HARD_TO_DEFEND"
    assert any(signal["code"] == "UNSOURCED_NUMBER" for signal in item["signals"])
    assert item["questions"]


def test_the_response_carries_no_approval_or_export_state(client: TestClient) -> None:
    """F15 is advice. It must not look like an F08 or F09 outcome."""
    token = _register(client, "advisory-f15@example.edu")
    evidence_id = _add_evidence(client, token, approve=True)

    body = client.post(
        ENDPOINT, json=_payload(evidence_id), headers=_auth(token)
    ).json()

    assert body["advisory_only"] is True
    serialized = str(body)
    assert "approval_status" not in serialized
    assert "export_eligible" not in serialized


def test_duplicate_statement_ids_are_rejected(client: TestClient) -> None:
    token = _register(client, "duplicate-f15@example.edu")
    evidence_id = _add_evidence(client, token, approve=True)
    payload = _payload(evidence_id)
    payload["approved_statements"].append(dict(payload["approved_statements"][0]))

    response = client.post(ENDPOINT, json=payload, headers=_auth(token))

    assert response.status_code == 422


# --- interim measure: not served in production ----------------------------


def test_preparation_is_not_served_in_production(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """While the route trusts client-supplied statements, production must not serve it.

    The statements are the untrusted half: a caller could submit text the user
    never approved. Until F09 can resolve statement ids server-side, the route
    does not exist outside development.
    """
    token = _register(client, "prod-f15@example.edu")
    evidence_id = _add_evidence(client, token, approve=True)
    monkeypatch.setattr(settings, "app_env", "production")

    response = client.post(ENDPOINT, json=_payload(evidence_id), headers=_auth(token))

    assert response.status_code == 404
