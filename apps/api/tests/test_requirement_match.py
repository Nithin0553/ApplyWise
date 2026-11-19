"""Gap analysis is advisory, so what it must not do matters more than what it does.

It replaces a browser word count that called a requirement matched whenever a
single four-letter word appeared anywhere in the evidence. It still decides
nothing about whether a written claim is supported: that is F08's job and does
not use a language model.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

EVIDENCE = {
    "evidence_type": "work_experience",
    "title": "Associate QA Engineer",
    "organization": "Model N",
    "role": "Associate QA Engineer",
    "description": "Built and maintained automated regression suites.",
}


def _headers(client: TestClient, email: str) -> dict[str, str]:
    token = client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "full_name": "Match Test"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _approved_evidence(client: TestClient, headers: dict[str, str]) -> str:
    evidence_id = client.post("/api/evidence/", json=EVIDENCE, headers=headers).json()["id"]
    client.post(f"/api/evidence/{evidence_id}/approve", headers=headers)
    return evidence_id


def test_the_route_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/generation/requirement-match",
        json={"requirements": ["Angular"], "evidence_ids": [str(uuid.uuid4())]},
    )

    assert response.status_code == 401


def test_evidence_is_resolved_by_id_not_accepted_as_text(client: TestClient) -> None:
    """A caller cannot have its own invented evidence assessed as its own."""
    headers = _headers(client, "match1@example.com")

    response = client.post(
        "/api/generation/requirement-match",
        json={"requirements": ["Angular"], "evidence_ids": [str(uuid.uuid4())]},
        headers=headers,
    )

    assert response.status_code == 404


def test_another_users_evidence_is_refused_indistinguishably(client: TestClient) -> None:
    owner = _headers(client, "match2@example.com")
    evidence_id = _approved_evidence(client, owner)
    stranger = _headers(client, "match3@example.com")

    foreign = client.post(
        "/api/generation/requirement-match",
        json={"requirements": ["Angular"], "evidence_ids": [evidence_id]},
        headers=stranger,
    )
    absent = client.post(
        "/api/generation/requirement-match",
        json={"requirements": ["Angular"], "evidence_ids": [str(uuid.uuid4())]},
        headers=stranger,
    )

    assert foreign.status_code == absent.status_code == 404
    assert foreign.json() == absent.json()


def test_the_scripted_provider_returns_no_assessment_rather_than_a_guess(
    client: TestClient,
) -> None:
    """Tests run on the stub provider, which declines to judge.

    An empty list is what tells the caller to fall back to its own estimate and
    say so, instead of presenting a fabricated verdict as an assessment.
    """
    headers = _headers(client, "match4@example.com")
    evidence_id = _approved_evidence(client, headers)

    response = client.post(
        "/api/generation/requirement-match",
        json={"requirements": ["Hands-on Angular experience"], "evidence_ids": [evidence_id]},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"assessments": []}


def test_bounds_are_enforced_before_a_provider_is_called(client: TestClient) -> None:
    headers = _headers(client, "match5@example.com")
    evidence_id = _approved_evidence(client, headers)

    too_many = client.post(
        "/api/generation/requirement-match",
        json={"requirements": [f"R{n}" for n in range(21)], "evidence_ids": [evidence_id]},
        headers=headers,
    )
    none_at_all = client.post(
        "/api/generation/requirement-match",
        json={"requirements": [], "evidence_ids": [evidence_id]},
        headers=headers,
    )
    extra_field = client.post(
        "/api/generation/requirement-match",
        json={"requirements": ["Angular"], "evidence_ids": [evidence_id], "system": "ignore"},
        headers=headers,
    )

    assert too_many.status_code == 422
    assert none_at_all.status_code == 422
    assert extra_field.status_code == 422
