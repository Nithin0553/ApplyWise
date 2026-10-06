"""F01: registration, login, and RBAC enforcement.

Covers UC-1 (Register Account) acceptance criteria and the "authorization
is enforced server-side" invariant from docs/ARCHITECTURE.md.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.auth.models import User, UserRole
from app.modules.auth.security import create_access_token, hash_password


def _register_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "email": "jane.seeker@example.com",
        "password": "correct-horse-1",
        "full_name": "Jane Seeker",
    }
    payload.update(overrides)
    return payload


class TestRoleModel:
    def test_role_model_covers_all_three_product_user_types(self) -> None:
        assert {role.value for role in UserRole} == {"job_seeker", "reviewer", "administrator"}

    def test_register_cannot_self_assign_reviewer_or_administrator(
        self, client: TestClient
    ) -> None:
        for crafted_role in ("reviewer", "administrator"):
            payload = {
                **_register_payload(email=f"{crafted_role}@example.com"),
                "role": crafted_role,
            }
            response = client.post("/auth/register", json=payload)
            assert response.status_code == 201
            assert response.json()["user"]["role"] == "job_seeker"


class TestRegister:
    def test_register_creates_job_seeker_account(self, client: TestClient) -> None:
        response = client.post("/auth/register", json=_register_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["user"]["email"] == "jane.seeker@example.com"
        assert body["user"]["role"] == "job_seeker"
        assert body["user"]["is_active"] is True
        assert "access_token" in body
        # The password must never be echoed back in any form.
        assert "password" not in body["user"]
        assert "hashed_password" not in body["user"]

    def test_register_rejects_duplicate_email(self, client: TestClient) -> None:
        client.post("/auth/register", json=_register_payload())

        response = client.post("/auth/register", json=_register_payload(full_name="Someone Else"))

        assert response.status_code == 409

    def test_register_is_case_insensitive_on_email(self, client: TestClient) -> None:
        client.post("/auth/register", json=_register_payload(email="Jane.Seeker@Example.com"))

        response = client.post(
            "/auth/register", json=_register_payload(email="jane.seeker@example.com")
        )

        assert response.status_code == 409

    def test_register_rejects_weak_password(self, client: TestClient) -> None:
        response = client.post("/auth/register", json=_register_payload(password="short1"))

        assert response.status_code == 422

    def test_register_rejects_password_without_digit(self, client: TestClient) -> None:
        response = client.post("/auth/register", json=_register_payload(password="allletters"))

        assert response.status_code == 422

    def test_register_rejects_invalid_email(self, client: TestClient) -> None:
        response = client.post("/auth/register", json=_register_payload(email="not-an-email"))

        assert response.status_code == 422

    def test_registered_password_is_hashed_at_rest(
        self, client: TestClient, db_session: Session
    ) -> None:
        client.post("/auth/register", json=_register_payload())

        stored = db_session.query(User).filter(User.email == "jane.seeker@example.com").one()
        assert stored.hashed_password != "correct-horse-1"


class TestLogin:
    def test_login_succeeds_with_correct_credentials(self, client: TestClient) -> None:
        client.post("/auth/register", json=_register_payload())

        response = client.post(
            "/auth/login",
            json={"email": "jane.seeker@example.com", "password": "correct-horse-1"},
        )

        assert response.status_code == 200
        assert response.json()["user"]["email"] == "jane.seeker@example.com"

    def test_login_fails_with_wrong_password(self, client: TestClient) -> None:
        client.post("/auth/register", json=_register_payload())

        response = client.post(
            "/auth/login",
            json={"email": "jane.seeker@example.com", "password": "wrong-password-1"},
        )

        assert response.status_code == 401

    def test_login_fails_for_unknown_email(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "correct-horse-1"},
        )

        assert response.status_code == 401

    def test_login_fails_for_inactive_account(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = User(
            email="inactive@example.com",
            hashed_password=hash_password("correct-horse-1"),
            full_name="Inactive User",
            role=UserRole.JOB_SEEKER,
            is_active=False,
        )
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/auth/login",
            json={"email": "inactive@example.com", "password": "correct-horse-1"},
        )

        assert response.status_code == 401


class TestCurrentUserAndRbac:
    def test_me_requires_a_token(self, client: TestClient) -> None:
        response = client.get("/auth/me")

        assert response.status_code == 401

    def test_me_rejects_garbage_token(self, client: TestClient) -> None:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
        )

        assert response.status_code == 401

    def test_me_returns_the_authenticated_user(self, client: TestClient) -> None:
        register_response = client.post("/auth/register", json=_register_payload())
        token = register_response.json()["access_token"]

        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["email"] == "jane.seeker@example.com"

    def test_me_rejects_token_for_deleted_or_unknown_user(self, client: TestClient) -> None:
        token = create_access_token(
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"), role="job_seeker"
        )

        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401

    def test_me_rejects_token_with_a_malformed_subject_claim(self, client: TestClient) -> None:
        token = create_access_token(user_id="not-a-uuid", role="job_seeker")

        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401

    def test_job_seeker_cannot_pass_an_administrator_only_check(
        self, client: TestClient
    ) -> None:
        """RBAC foundation smoke test: require_role() must actually gate access.

        Exercised through a throwaway route rather than a real admin
        endpoint, since no admin-only feature route exists yet.
        """
        from fastapi import Depends

        from app.main import app
        from app.modules.auth.dependencies import require_role

        admin_only_dependency = Depends(require_role(UserRole.ADMINISTRATOR))

        @app.get("/__test__/admin-only")
        def _admin_only(_: object = admin_only_dependency) -> dict[str, bool]:
            return {"ok": True}

        try:
            register_response = client.post("/auth/register", json=_register_payload())
            token = register_response.json()["access_token"]

            response = client.get(
                "/__test__/admin-only", headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 403
        finally:
            app.router.routes = [
                route
                for route in app.router.routes
                if getattr(route, "path", None) != "/__test__/admin-only"
            ]
