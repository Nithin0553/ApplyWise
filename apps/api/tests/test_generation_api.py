"""Tests for the F07 preview endpoint.

These run through the real stack: F01 for authentication, and F02 for the
evidence itself. A caller sends evidence ids, never evidence content, so the
tests below create real evidence through F02's own endpoints and then select
it by id — which is exactly what the web client does.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

JOB_CONTEXT = {
    "job_title": "Software Engineer in Test",
    "company": "Example Corp",
    "description": "Own automated testing for a Python backend.",
    "requirements": ["Python", "test automation"],
}

WORK_EVIDENCE = {
    "evidence_type": "work_experience",
    "title": "Associate QA Engineer",
    "organization": "Model N",
    "role": "Associate QA Engineer",
    "description": "Built automated regression suites.",
}

SKILL_EVIDENCE = {
    "evidence_type": "skill",
    "title": "Python",
    "skill_name": "Python",
    "proficiency": "Advanced",
}


def _register(client: TestClient, email: str) -> tuple[str, str]:
    """Create a job seeker and return (bearer token, user id)."""
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "full_name": "Test Person"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["access_token"], body["user"]["id"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _add_evidence(client: TestClient, token: str, payload: dict, *, approve: bool) -> str:
    """Create one evidence record through F02 and return its id."""
    created = client.post("/api/evidence/", json=payload, headers=_auth(token))
    assert created.status_code == 201, created.text
    evidence_id = created.json()["id"]

    if approve:
        approved = client.post(f"/api/evidence/{evidence_id}/approve", headers=_auth(token))
        assert approved.status_code == 200, approved.text

    return evidence_id


def _seeded_user(client: TestClient, email: str) -> tuple[str, str, list[str]]:
    """A job seeker with two approved evidence items."""
    token, user_id = _register(client, email)
    ids = [
        _add_evidence(client, token, WORK_EVIDENCE, approve=True),
        _add_evidence(client, token, SKILL_EVIDENCE, approve=True),
    ]
    return token, user_id, ids


def _request(evidence_ids: list[str], **overrides: object) -> dict:
    return {
        "job_context": JOB_CONTEXT,
        "evidence_ids": evidence_ids,
        "max_statements": 5,
        **overrides,
    }


# --- authentication -------------------------------------------------------


def test_preview_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/generation/preview", json=_request([str(uuid4())]))

    assert response.status_code == 401


def test_preview_rejects_a_garbage_token(client: TestClient) -> None:
    response = client.post(
        "/api/generation/preview",
        json=_request([str(uuid4())]),
        headers=_auth("not-a-real-token"),
    )

    assert response.status_code == 401


# --- the evidence trust boundary ------------------------------------------


def test_fabricated_evidence_never_reaches_generation(client: TestClient) -> None:
    """An id nobody approved cannot be generated from.

    Before selection moved server-side, a caller could send invented evidence
    content and have statements written from it. Now it sends only ids, and an
    unknown id is refused outright.
    """
    token, _, _ = _seeded_user(client, "fabricated@example.edu")

    response = client.post(
        "/api/generation/preview?provider=stub",
        json=_request([str(uuid4())]),
        headers=_auth(token),
    )

    assert response.status_code == 404


def test_another_users_evidence_never_reaches_generation(client: TestClient) -> None:
    """A real, approved evidence id belonging to someone else is still refused."""
    _, _, victim_ids = _seeded_user(client, "victim@example.edu")
    attacker_token, _ = _register(client, "attacker@example.edu")

    response = client.post(
        "/api/generation/preview?provider=stub",
        json=_request([victim_ids[0]]),
        headers=_auth(attacker_token),
    )

    assert response.status_code == 404


def test_a_foreign_id_is_indistinguishable_from_a_missing_one(client: TestClient) -> None:
    """Both refusals must look identical, or the endpoint leaks existence."""
    _, _, victim_ids = _seeded_user(client, "victim2@example.edu")
    attacker_token, _ = _register(client, "attacker2@example.edu")

    foreign = client.post(
        "/api/generation/preview?provider=stub",
        json=_request([victim_ids[0]]),
        headers=_auth(attacker_token),
    )
    missing = client.post(
        "/api/generation/preview?provider=stub",
        json=_request([str(uuid4())]),
        headers=_auth(attacker_token),
    )

    assert foreign.status_code == missing.status_code
    assert foreign.json()["detail"] == missing.json()["detail"]


def test_unapproved_evidence_cannot_be_generated_from(client: TestClient) -> None:
    """Evidence the user owns but has not approved is still refused."""
    token, _ = _register(client, "unapproved@example.edu")
    unapproved_id = _add_evidence(client, token, WORK_EVIDENCE, approve=False)

    response = client.post(
        "/api/generation/preview?provider=stub",
        json=_request([unapproved_id]),
        headers=_auth(token),
    )

    assert response.status_code == 404


def test_one_bad_id_refuses_the_whole_request(client: TestClient) -> None:
    token, _, ids = _seeded_user(client, "partial@example.edu")

    response = client.post(
        "/api/generation/preview?provider=stub",
        json=_request([ids[0], str(uuid4())]),
        headers=_auth(token),
    )

    assert response.status_code == 404


def test_evidence_content_in_the_body_is_not_accepted(client: TestClient) -> None:
    """The old shape is gone: a body carrying evidence objects is rejected."""
    token, _, _ = _seeded_user(client, "oldshape@example.edu")

    response = client.post(
        "/api/generation/preview?provider=stub",
        json={
            "job_context": JOB_CONTEXT,
            "approved_evidence": [
                {
                    "evidence_id": str(uuid4()),
                    "evidence_type": "SKILL",
                    "title": "Fabricated skill",
                }
            ],
            "max_statements": 5,
        },
        headers=_auth(token),
    )

    assert response.status_code == 422


def test_duplicate_ids_are_rejected(client: TestClient) -> None:
    token, _, ids = _seeded_user(client, "duplicate@example.edu")

    response = client.post(
        "/api/generation/preview?provider=stub",
        json=_request([ids[0], ids[0]]),
        headers=_auth(token),
    )

    assert response.status_code == 422


def test_preview_rejects_a_request_with_no_evidence(client: TestClient) -> None:
    token, _, _ = _seeded_user(client, "noevidence@example.edu")

    response = client.post(
        "/api/generation/preview", json=_request([]), headers=_auth(token)
    )

    assert response.status_code == 422


# --- behaviour ------------------------------------------------------------


def test_preview_returns_candidates_with_provenance(client: TestClient) -> None:
    token, user_id, ids = _seeded_user(client, "provenance@example.edu")

    response = client.post(
        "/api/generation/preview?provider=stub", json=_request(ids), headers=_auth(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "stub"
    assert body["user_id"] == user_id
    assert body["statements"], "expected at least one candidate statement"
    for statement in body["statements"]:
        assert statement["evidence_ids"], "every statement must carry provenance"
        assert set(statement["evidence_ids"]) <= set(ids), "cited unselected evidence"
        assert statement["status"] == "CANDIDATE"
        assert statement["verification_status"] == "PENDING"
        assert statement["approval_status"] == "UNREVIEWED"
        assert statement["export_eligible"] is False


def test_generation_is_scoped_to_the_token(client: TestClient) -> None:
    """The result belongs to the authenticated caller.

    Identity cannot be supplied at all: there is no user_id field, and the
    evidence is read for the token's user.
    """
    token, user_id, ids = _seeded_user(client, "scoped@example.edu")
    _, other_user_id = _register(client, "other-scoped@example.edu")

    response = client.post(
        "/api/generation/preview?provider=stub",
        json={**_request(ids), "user_id": other_user_id},
        headers=_auth(token),
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == user_id
    assert response.json()["user_id"] != other_user_id


def test_structured_fields_survive_into_generation(client: TestClient) -> None:
    """Skill evidence carries its meaning in skill_name, not description.

    This is the regression guarded on the adapter: the record reaches the
    provider with its structured fields intact, so a skill cannot collapse to
    a bare title on the way through.
    """
    token, _, ids = _seeded_user(client, "structured@example.edu")

    response = client.post(
        "/api/generation/preview?provider=demo", json=_request(ids), headers=_auth(token)
    )

    assert response.status_code == 200
    texts = " ".join(item["text"] for item in response.json()["statements"])
    assert "Advanced" in texts, "proficiency did not reach the provider"


def test_demo_provider_rejects_ungrounded_statements(client: TestClient) -> None:
    token, _, ids = _seeded_user(client, "rejects@example.edu")

    response = client.post(
        "/api/generation/preview?provider=demo", json=_request(ids), headers=_auth(token)
    )

    assert response.status_code == 200
    body = response.json()
    reasons = [item["reason"] for item in body["rejected"]]
    assert any("unknown evidence reference" in reason for reason in reasons)
    assert any("no evidence cited" in reason for reason in reasons)
    for statement in body["statements"]:
        assert statement["evidence_ids"]


def test_unknown_provider_is_a_client_error(client: TestClient) -> None:
    token, _, ids = _seeded_user(client, "badprovider@example.edu")

    response = client.post(
        "/api/generation/preview?provider=mystery",
        json=_request(ids),
        headers=_auth(token),
    )

    assert response.status_code == 400


def test_providers_endpoint_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/generation/providers").status_code == 401


def test_providers_endpoint_lists_available_providers(client: TestClient) -> None:
    token, _ = _register(client, "providers@example.edu")

    response = client.get("/api/generation/providers", headers=_auth(token))

    assert response.status_code == 200
    assert "stub" in response.json()["available"]
