from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.applications.service import ApplicationService
from app.modules.auth.models import User, UserRole
from app.modules.auth.security import hash_password

PASSWORD = "correct-horse-1"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, email: str) -> dict[str, object]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Synthetic User"},
    )
    assert response.status_code == 201
    return response.json()


def _reviewer_token(client: TestClient, db_session: Session) -> str:
    reviewer = User(
        email="reviewer@example.com",
        hashed_password=hash_password(PASSWORD),
        full_name="Synthetic Reviewer",
        role=UserRole.REVIEWER,
        is_active=True,
    )
    db_session.add(reviewer)
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={"email": reviewer.email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _application_and_version(client: TestClient, token: str) -> tuple[str, str]:
    application = client.post(
        "/api/applications/",
        headers=_headers(token),
        json={"company_name": "Example Co", "role_title": "Software Engineer"},
    )
    assert application.status_code == 201
    application_id = application.json()["id"]

    version = client.post(
        f"/api/applications/{application_id}/resume-versions",
        headers=_headers(token),
        json={"evidence": [], "statements": []},
    )
    assert version.status_code == 201
    return application_id, version.json()["id"]


def test_feature_routes_require_authentication(client: TestClient) -> None:
    assert client.get("/api/evidence/").status_code == 401
    assert client.get("/api/applications/").status_code == 401
    assert client.get("/api/shares/").status_code == 401
    assert client.get("/api/shares/resolve/aaaaaaaaaaaaaaaaaaaa").status_code == 401


def test_evidence_api_uses_authenticated_owner_boundary(client: TestClient) -> None:
    owner = _register(client, "evidence.owner@example.com")
    other = _register(client, "evidence.other@example.com")
    owner_token = owner["access_token"]
    other_token = other["access_token"]

    created = client.post(
        "/api/evidence/",
        headers=_headers(owner_token),
        json={
            "evidence_type": "skill",
            "title": "Python",
            "skill_name": "Python",
            "proficiency": "advanced",
        },
    )
    assert created.status_code == 201
    evidence_id = created.json()["id"]
    assert created.json()["user_id"] == owner["user"]["id"]

    assert (
        client.get(f"/api/evidence/{evidence_id}", headers=_headers(other_token)).status_code
        == 404
    )

    approved = client.post(
        f"/api/evidence/{evidence_id}/approve",
        headers=_headers(owner_token),
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    approved_list = client.get("/api/evidence/approved", headers=_headers(owner_token))
    assert approved_list.status_code == 200
    assert [item["id"] for item in approved_list.json()] == [evidence_id]


def test_application_api_scopes_versions_to_authenticated_owner(client: TestClient) -> None:
    owner = _register(client, "application.owner@example.com")
    other = _register(client, "application.other@example.com")
    owner_token = owner["access_token"]
    other_token = other["access_token"]

    application_id, version_id = _application_and_version(client, owner_token)

    assert (
        client.get(
            f"/api/applications/{application_id}", headers=_headers(other_token)
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/applications/resume-versions/{version_id}",
            headers=_headers(other_token),
        ).status_code
        == 404
    )

    versions = client.get(
        f"/api/applications/{application_id}/resume-versions",
        headers=_headers(owner_token),
    )
    assert versions.status_code == 200
    assert versions.json()[0]["version_number"] == 1
    assert versions.json()[0]["id"] == version_id


def test_resume_version_count_endpoint_is_owner_scoped(
    client: TestClient,
    db_session: Session,
) -> None:
    owner = _register(client, "count.owner@example.com")
    other = _register(client, "count.other@example.com")
    owner_token = owner["access_token"]
    other_token = other["access_token"]

    first_id, _ = _application_and_version(client, owner_token)
    second_id, _ = _application_and_version(client, owner_token)
    other_id, _ = _application_and_version(client, other_token)

    response = client.post(
        f"/api/applications/{first_id}/resume-versions",
        headers=_headers(owner_token),
        json={"evidence": [], "statements": []},
    )
    assert response.status_code == 201

    counts = client.get(
        "/api/applications/resume-version-counts",
        headers=_headers(owner_token),
    )
    assert counts.status_code == 200
    assert counts.json() == {first_id: 2, second_id: 1}
    assert other_id not in counts.json()

    other_counts = client.get(
        "/api/applications/resume-version-counts",
        headers=_headers(other_token),
    )
    assert other_counts.status_code == 200
    assert other_counts.json() == {other_id: 1}

    assert client.get("/api/applications/resume-version-counts").status_code == 401
    reviewer = _reviewer_token(client, db_session)
    assert client.get(
        "/api/applications/resume-version-counts",
        headers=_headers(reviewer),
    ).status_code == 403


def test_reviewed_draft_atomic_save_uses_authoritative_approved_evidence(
    client: TestClient,
) -> None:
    owner = _register(client, "draft.owner@example.com")
    other = _register(client, "draft.other@example.com")
    owner_token, other_token = owner["access_token"], other["access_token"]

    created_evidence = client.post(
        "/api/evidence/",
        headers=_headers(owner_token),
        json={"evidence_type": "project", "title": "Real API testing",
              "description": "Built REST API tests in Python."},
    )
    assert created_evidence.status_code == 201
    evidence_id = created_evidence.json()["id"]

    payload = {
        "application": {"company_name": "Example", "role_title": "QA Engineer"},
        "statements": [{
            "statement_id": str(uuid4()),
            "text": "Built REST API tests in Python.",
            "evidence_ids": [evidence_id],
        }],
    }

    # Cannot create a draft using evidence that was never approved.
    unconfirmed = client.post(
        "/api/applications/reviewed-drafts",
        headers=_headers(owner_token),
        json=payload,
    )
    assert unconfirmed.status_code == 404
    assert client.get("/api/applications/", headers=_headers(owner_token)).json() == []

    approve = client.post(
        f"/api/evidence/{evidence_id}/approve",
        headers=_headers(owner_token),
    )
    assert approve.status_code == 200

    saved = client.post(
        "/api/applications/reviewed-drafts",
        headers=_headers(owner_token),
        json=payload,
    )
    assert saved.status_code == 201
    result = saved.json()
    application = result["application"]
    snapshot = result["resume_version"]["snapshot"]
    assert application["status"] == "draft"
    assert snapshot["statements"][0]["verification_status"] == "INFERRED"
    assert snapshot["statements"][0]["approval_status"] == "APPROVED"
    assert snapshot["statements"][0]["origin"] == "DRAFT_USER_REVIEWED"
    assert snapshot["evidence"][0]["title"] == approve.json()["title"]
    assert snapshot["evidence"][0]["description"] == approve.json()["description"]
    # SQLite loses timezone metadata on readback; compare the timestamp values
    # without assuming whether JSON serialization includes the UTC suffix.
    snapshot_approval = datetime.fromisoformat(
        snapshot["evidence"][0]["approved_at"].replace("Z", "+00:00")
    )
    source_approval = datetime.fromisoformat(
        approve.json()["approved_at"].replace("Z", "+00:00")
    )
    assert snapshot_approval.replace(tzinfo=None) == source_approval.replace(tzinfo=None)
    assert snapshot["application_id"] == application["id"]
    # The public snapshot route cannot impersonate a future F09 approval.
    forged_snapshot = {
        "evidence": snapshot["evidence"],
        "statements": [{**snapshot["statements"][0], "origin": "F09_APPROVED"}],
    }
    forged = client.post(
        f"/api/applications/{application['id']}/resume-versions",
        headers=_headers(owner_token),
        json=forged_snapshot,
    )
    assert forged.status_code == 422
    assert client.get(
        f"/api/applications/{application['id']}/resume-versions",
        headers=_headers(owner_token),
    ).json()[0]["snapshot"]["statements"][0]["origin"] == "DRAFT_USER_REVIEWED"
    assert len(client.get("/api/applications/", headers=_headers(owner_token)).json()) == 1

    # Same IDs and content from a foreign owner must not succeed.
    foreign = client.post(
        "/api/applications/reviewed-drafts",
        headers=_headers(other_token),
        json=payload,
    )
    assert foreign.status_code == 404
    assert client.get("/api/applications/", headers=_headers(other_token)).json() == []

    duplicate = {**payload, "statements": payload["statements"] * 2}
    assert client.post(
        "/api/applications/reviewed-drafts",
        headers=_headers(owner_token),
        json=duplicate,
    ).status_code == 422
    assert len(client.get("/api/applications/", headers=_headers(owner_token)).json()) == 1
    assert client.post("/api/applications/reviewed-drafts", json=payload).status_code == 401


def test_reviewed_draft_save_rolls_back_application_on_version_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _register(client, "draft.rollback@example.com")
    token = owner["access_token"]
    evidence = client.post(
        "/api/evidence/",
        headers=_headers(token),
        json={"evidence_type": "project", "title": "Synthetic data",
              "description": "Completed testing work."},
    ).json()
    assert client.post(
        f"/api/evidence/{evidence['id']}/approve", headers=_headers(token),
    ).status_code == 200

    def fail_version(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("Simulated version persistence failure")

    monkeypatch.setattr(ApplicationService, "save_resume_version", fail_version)
    with pytest.raises(RuntimeError, match="Simulated version"):
        client.post(
            "/api/applications/reviewed-drafts",
            headers=_headers(token),
            json={"application": {"company_name": "Test", "role_title": "QA"},
                  "statements": [{
                      "statement_id": str(uuid4()), "text": "Completed testing work.",
                      "evidence_ids": [evidence["id"]],
                  }]},
        )
    assert client.get("/api/applications/", headers=_headers(token)).json() == []


def test_sharing_api_enforces_job_seeker_and_reviewer_roles(
    client: TestClient,
    db_session: Session,
) -> None:
    owner = _register(client, "share.owner@example.com")
    other = _register(client, "share.other@example.com")
    owner_token = owner["access_token"]
    other_token = other["access_token"]
    reviewer_token = _reviewer_token(client, db_session)

    _, version_id = _application_and_version(client, owner_token)
    created = client.post(
        f"/api/shares/resume-versions/{version_id}",
        headers=_headers(owner_token),
        json={},
    )
    assert created.status_code == 201
    share_id = created.json()["grant"]["id"]
    secret = created.json()["secret"]

    resolved = client.get(
        f"/api/shares/resolve/{secret}",
        headers=_headers(reviewer_token),
    )
    assert resolved.status_code == 200
    assert resolved.json()["resume_version_id"] == version_id

    assert (
        client.get(f"/api/shares/resolve/{secret}", headers=_headers(owner_token)).status_code
        == 403
    )
    assert client.get("/api/shares/", headers=_headers(reviewer_token)).status_code == 403

    feedback = client.post(
        f"/api/shares/resolve/{secret}/feedback",
        headers=_headers(reviewer_token),
        json={"comment": "The evidence-backed bullets are clear."},
    )
    assert feedback.status_code == 201

    history = client.get(
        f"/api/shares/{share_id}/feedback",
        headers=_headers(owner_token),
    )
    assert history.status_code == 200
    assert [item["comment"] for item in history.json()] == [
        "The evidence-backed bullets are clear."
    ]

    assert (
        client.post(
            f"/api/shares/{share_id}/revoke",
            headers=_headers(other_token),
        ).status_code
        == 404
    )


def test_alembic_chain_has_one_head_rooted_after_f01() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == ["20261006_0004"]
    assert scripts.get_revision("20261006_0004").down_revision == "20261001_0003"
    assert scripts.get_revision("20260921_0001").down_revision == "0001"
