from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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

    assert scripts.get_heads() == ["20261001_0003"]
    assert scripts.get_revision("20260921_0001").down_revision == "0001"
