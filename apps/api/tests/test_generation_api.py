"""Tests for the F07 preview endpoint used by the tailoring UI."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.fixtures.generation_fixtures import (
    EVIDENCE_ONE_ID,
    EVIDENCE_TWO_ID,
    USER_ID,
)

client = TestClient(app)

PAYLOAD = {
    "user_id": str(USER_ID),
    "job_context": {
        "job_title": "Software Engineer in Test",
        "company": "Example Corp",
        "description": "Own automated testing for a Python backend.",
        "requirements": ["Python", "test automation"],
    },
    "approved_evidence": [
        {
            "evidence_id": str(EVIDENCE_ONE_ID),
            "evidence_type": "WORK_EXPERIENCE",
            "title": "Associate QA Engineer",
            "organization": "Model N",
            "role": "Associate QA Engineer",
            "description": "Built automated regression suites.",
        },
        {
            "evidence_id": str(EVIDENCE_TWO_ID),
            "evidence_type": "SKILL",
            "title": "Python",
            "description": "Used for test automation.",
        },
    ],
    "max_statements": 5,
}


def test_preview_returns_candidates_with_provenance() -> None:
    response = client.post("/api/generation/preview?provider=stub", json=PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "stub"
    assert body["statements"], "expected at least one candidate statement"
    for statement in body["statements"]:
        assert statement["evidence_ids"], "every statement must carry provenance"
        assert statement["status"] == "CANDIDATE"
        assert statement["verification_status"] == "PENDING"
        assert statement["approval_status"] == "UNREVIEWED"
        assert statement["export_eligible"] is False


def test_demo_provider_rejects_ungrounded_statements() -> None:
    response = client.post("/api/generation/preview?provider=demo", json=PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    reasons = [item["reason"] for item in body["rejected"]]
    assert any("unknown evidence reference" in reason for reason in reasons)
    assert any("no evidence cited" in reason for reason in reasons)
    for statement in body["statements"]:
        assert statement["evidence_ids"]


def test_preview_rejects_a_request_with_no_evidence() -> None:
    payload = {**PAYLOAD, "approved_evidence": []}

    response = client.post("/api/generation/preview", json=payload)

    assert response.status_code == 422


def test_unknown_provider_is_a_client_error() -> None:
    response = client.post("/api/generation/preview?provider=mystery", json=PAYLOAD)

    assert response.status_code == 400


def test_providers_endpoint_lists_available_providers() -> None:
    response = client.get("/api/generation/providers")

    assert response.status_code == 200
    assert "stub" in response.json()["available"]
