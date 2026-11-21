"""F15 API uses F08/F09 server-owned approvals, not caller-supplied claims."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from tests.test_f08_f09_integration import COVERED_CLAIM, _auth, _seed, _verify

ENDPOINT = "/api/interview/preparation"


def _approved(client: TestClient, email: str, *, inferred: bool = False):
    token, evidence_id = _seed(client, email)
    text = (
        "Improved release confidence for the billing organisation"
        if inferred else COVERED_CLAIM
    )
    claim = _verify(client, token, text, evidence_id)
    assert claim["status"] == ("INFERRED" if inferred else "VERIFIED")
    decision = client.post(
        f"/api/statement-review/{claim['statement_id']}/decision",
        json={"decision": "APPROVED", "expected_revision": claim["revision"]},
        headers=_auth(token),
    )
    assert decision.status_code == 200, decision.text
    return token, evidence_id, claim["statement_id"]


def _payload(statement_id: str):
    return {"statement_ids": [statement_id]}


def test_the_preparation_route_is_mounted(client: TestClient) -> None:
    assert ENDPOINT in client.get("/openapi.json").json()["paths"]


def test_preparation_requires_authentication(client: TestClient) -> None:
    assert client.post(ENDPOINT, json=_payload(str(uuid4()))).status_code == 401


def test_a_foreign_id_and_missing_id_are_indistinguishable(client: TestClient) -> None:
    _, _, owner_id = _approved(client, "f15-owner@example.edu")
    stranger, _ = _seed(client, "f15-stranger@example.edu")
    foreign = client.post(ENDPOINT, json=_payload(owner_id), headers=_auth(stranger))
    missing = client.post(
        ENDPOINT, json=_payload(str(uuid4())), headers=_auth(stranger)
    )
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


def test_unapproved_statement_is_refused(client: TestClient) -> None:
    token, evidence_id = _seed(client, "f15-unapproved@example.edu")
    claim = _verify(client, token, COVERED_CLAIM, evidence_id)
    result = client.post(
        ENDPOINT, json=_payload(claim["statement_id"]), headers=_auth(token)
    )
    assert result.status_code == 404


def test_current_approved_inferred_statement_gets_advice_not_export_authority(
    client: TestClient,
) -> None:
    token, evidence_id, statement_id = _approved(
        client, "f15-inferred@example.edu", inferred=True
    )
    result = client.post(
        ENDPOINT, json=_payload(statement_id), headers=_auth(token)
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["advisory_only"] is True
    assert body["items"][0]["statement_id"] == statement_id
    assert evidence_id in body["items"][0]["evidence_ids"]
    assert body["items"][0]["questions"]
    assert body["items"][0]["risk"] in ("NEEDS_DETAIL", "HARD_TO_DEFEND")
    assert "approval_status" not in str(body)
    assert "export_eligible" not in str(body)


def test_stale_evidence_blocks_interview_preparation(client: TestClient) -> None:
    token, evidence_id, statement_id = _approved(client, "f15-stale@example.edu")
    edited = client.patch(
        f"/api/evidence/{evidence_id}",
        json={"description": "Different experience recorded after review."},
        headers=_auth(token),
    )
    assert edited.status_code == 200, edited.text
    result = client.post(
        ENDPOINT, json=_payload(statement_id), headers=_auth(token)
    )
    assert result.status_code == 404


def test_forged_verification_and_approval_labels_fail_validation(
    client: TestClient,
) -> None:
    token, _, statement_id = _approved(client, "f15-forged@example.edu")
    payload = {
        "statement_ids": [statement_id],
        "approved_statements": [{
            "statement_id": statement_id,
            "verification_status": "VERIFIED",
            "approval_status": "APPROVED",
            "text": "Invented an accomplishment.",
            "evidence_ids": [str(uuid4())],
        }],
    }
    assert client.post(ENDPOINT, json=payload, headers=_auth(token)).status_code == 422


def test_duplicate_and_oversized_statement_ids_fail_validation(
    client: TestClient,
) -> None:
    token, _, statement_id = _approved(client, "f15-duplicate@example.edu")
    assert client.post(
        ENDPOINT, json={"statement_ids": [statement_id, statement_id]},
        headers=_auth(token),
    ).status_code == 422
    assert client.post(
        ENDPOINT, json={"statement_ids": [str(uuid4()) for _ in range(21)]},
        headers=_auth(token),
    ).status_code == 422


def test_unsupported_claim_never_reaches_advice(client: TestClient) -> None:
    token, evidence_id = _seed(client, "f15-unsupported@example.edu")
    claim = _verify(client, token, "Reduced regression runtime by 85%", evidence_id)
    assert claim["status"] == "UNSUPPORTED"
    response = client.post(
        f"/api/statement-review/{claim['statement_id']}/decision",
        json={"decision": "APPROVED", "expected_revision": claim["revision"]},
        headers=_auth(token),
    )
    assert response.status_code == 409
    assert client.post(
        ENDPOINT, json=_payload(claim["statement_id"]), headers=_auth(token)
    ).status_code == 404


def test_preparation_is_authorized_in_production(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    token, _, statement_id = _approved(client, "f15-prod@example.edu")
    monkeypatch.setattr(settings, "app_env", "production")
    result = client.post(
        ENDPOINT, json=_payload(statement_id), headers=_auth(token)
    )
    assert result.status_code == 200, result.text
    assert result.json()["advisory_only"] is True
