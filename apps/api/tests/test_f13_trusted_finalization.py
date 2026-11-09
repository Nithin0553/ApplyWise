"""F13 trusted finalization: only current F02 + F08/F09 state can authorize export."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.modules.applications.schemas import ApplicationCreate, ResumeVersionContent
from app.modules.applications.service import ApplicationService
from app.modules.evidence.models import EvidenceType
from app.modules.evidence.schemas import EvidenceCreate
from app.modules.evidence.service import EvidenceService
from app.modules.statement_review.contract import (
    CurrentVerifiedStatement,
    UnavailableVerificationProvider,
    VerificationStatus,
    current_verification_provider,
)
from app.modules.statement_review.models import ReviewDecision
from app.modules.statement_review.service import StatementReviewService


class FakeF08:
    def __init__(self) -> None:
        self.items: dict[tuple[UUID, UUID], CurrentVerifiedStatement] = {}

    def set(
        self,
        user_id: UUID,
        statement_id: UUID,
        evidence_id: UUID,
        *,
        status: VerificationStatus = VerificationStatus.VERIFIED,
        revision: str = "revision-one-current",
        text: str = "Developed Python integration tests.",
    ) -> None:
        self.items[(user_id, statement_id)] = CurrentVerifiedStatement(
            user_id=user_id,
            statement_id=statement_id,
            evidence_ids=(evidence_id,),
            status=status,
            revision=revision,
            text=text,
        )

    def get_current(
        self, *, user_id: UUID, statement_id: UUID
    ) -> CurrentVerifiedStatement | None:
        return self.items.get((user_id, statement_id))

    def list_current(self, *, user_id: UUID) -> tuple[CurrentVerifiedStatement, ...]:
        return tuple(
            item for (owner, _), item in self.items.items() if owner == user_id
        )


def register(client: TestClient, suffix: str) -> tuple[UUID, dict[str, str]]:
    response = client.post(
        "/auth/register",
        json={
            "email": f"trusted-finalization-{suffix}@example.org",
            "full_name": "Synthetic User",
            "password": "synthetic-pass-123",
        },
    )
    assert response.status_code == 201
    body = response.json()
    return UUID(body["user"]["id"]), {"Authorization": f"Bearer {body['access_token']}"}


def make_application(db: Session, owner: UUID) -> UUID:
    result = ApplicationService(db).create_application(
        user_id=owner,
        data=ApplicationCreate(company_name="Example Company", role_title="Engineer"),
    )
    db.commit()
    return result.id


def make_evidence(db: Session, owner: UUID) -> UUID:
    evidence = EvidenceService(db)
    record = evidence.create(
        user_id=owner,
        data=EvidenceCreate(
            evidence_type=EvidenceType.SKILL,
            title="Python",
            skill_name="Python",
        ),
    )
    evidence.approve(user_id=owner, evidence_id=record.id)
    db.commit()
    return record.id


def approve_statement(
    db: Session, provider: FakeF08, owner: UUID,
    statement: UUID, evidence_id: UUID,
    *, status: VerificationStatus = VerificationStatus.VERIFIED,
) -> None:
    provider.set(owner, statement, evidence_id, status=status)
    StatementReviewService(db, provider).decide(
        user_id=owner, statement_id=statement,
        decision=ReviewDecision.APPROVED,
        expected_revision="revision-one-current",
    )
    db.commit()


def finalization_url(application_id: UUID) -> str:
    return f"/api/applications/{application_id}/trusted-finalize"


def trusted_export_url(version_id: UUID) -> str:
    return f"/api/applications/resume-versions/{version_id}/trusted-export-content"


def test_unavailable_f08_fails_closed_without_saving_version(
    client: TestClient, db_session: Session,
) -> None:
    app.dependency_overrides[current_verification_provider] = UnavailableVerificationProvider
    owner, headers = register(client, "unavailable")
    application_id = make_application(db_session, owner)
    response = client.post(
        finalization_url(application_id), headers=headers,
        json={"statement_ids": [str(uuid4())]},
    )
    assert response.status_code == 503
    versions = client.get(
        f"/api/applications/{application_id}/resume-versions", headers=headers
    )
    assert versions.status_code == 200
    assert versions.json() == []


def test_trusted_f13_creates_snapshot_and_rechecks_f02_before_export(
    client: TestClient, db_session: Session,
) -> None:
    owner, headers = register(client, "current")
    application_id = make_application(db_session, owner)
    evidence_id = make_evidence(db_session, owner)
    statement = uuid4()
    f08 = FakeF08()
    approve_statement(db_session, f08, owner, statement, evidence_id)
    app.dependency_overrides[current_verification_provider] = lambda: f08

    response = client.post(
        finalization_url(application_id),
        headers=headers,
        json={"statement_ids": [str(statement)]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["version_number"] == 1
    snapshot = body["snapshot"]
    assert snapshot["user_id"] == str(owner)
    assert snapshot["statements"][0]["text"] == "Developed Python integration tests."
    assert snapshot["statements"][0]["origin"] == "F09_APPROVED"
    assert snapshot["statements"][0]["verification_status"] == "VERIFIED"
    assert snapshot["statements"][0]["approval_status"] == "APPROVED"
    assert snapshot["statements"][0]["verification_revision"] == "revision-one-current"
    assert snapshot["evidence"][0]["evidence_id"] == str(evidence_id)
    assert snapshot["evidence"][0]["title"] == "Python"

    export_url = trusted_export_url(UUID(body["id"]))
    current = client.get(export_url, headers=headers)
    assert current.status_code == 200
    assert current.json()["statements"] == snapshot["statements"]
    assert current.json()["evidence"] == snapshot["evidence"]

    # Revocation does not erase history, but prevents F10 from using it.
    EvidenceService(db_session).unconfirm(user_id=owner, evidence_id=evidence_id)
    db_session.commit()
    assert client.get(export_url, headers=headers).status_code == 409
    still_saved = client.get(
        f"/api/applications/resume-versions/{body['id']}", headers=headers
    )
    assert still_saved.status_code == 200
    assert still_saved.json()["snapshot"] == snapshot


def test_inferred_remains_labeled_inferred_and_revision_change_revokes_export(
    client: TestClient, db_session: Session,
) -> None:
    owner, headers = register(client, "inferred")
    app_id = make_application(db_session, owner)
    evidence_id = make_evidence(db_session, owner)
    statement_id = uuid4()
    f08 = FakeF08()
    approve_statement(
        db_session, f08, owner, statement_id, evidence_id,
        status=VerificationStatus.INFERRED,
    )
    app.dependency_overrides[current_verification_provider] = lambda: f08
    result = client.post(
        finalization_url(app_id), headers=headers,
        json={"statement_ids": [str(statement_id)]},
    )
    assert result.status_code == 201
    snapshot = result.json()["snapshot"]
    assert snapshot["statements"][0]["verification_status"] == "INFERRED"
    assert snapshot["statements"][0]["origin"] == "F09_APPROVED"
    version_id = UUID(result.json()["id"])

    f08.set(
        owner, statement_id, evidence_id,
        status=VerificationStatus.VERIFIED, revision="revision-two-changed",
    )
    assert client.get(trusted_export_url(version_id), headers=headers).status_code == 409
    attempt = client.post(
        finalization_url(app_id), headers=headers,
        json={"statement_ids": [str(statement_id)]},
    )
    assert attempt.status_code == 409


def test_unsupported_and_unapproved_statements_never_finalize(
    client: TestClient, db_session: Session,
) -> None:
    owner, headers = register(client, "unsupported")
    app_id = make_application(db_session, owner)
    evidence_id = make_evidence(db_session, owner)
    statement_id = uuid4()
    f08 = FakeF08()
    f08.set(owner, statement_id, evidence_id, status=VerificationStatus.UNSUPPORTED)
    app.dependency_overrides[current_verification_provider] = lambda: f08

    blocked = client.post(
        finalization_url(app_id), headers=headers,
        json={"statement_ids": [str(statement_id)]},
    )
    assert blocked.status_code == 409
    assert client.get(
        f"/api/applications/{app_id}/resume-versions", headers=headers
    ).json() == []


def test_foreign_application_and_client_forged_flags_are_rejected(
    client: TestClient, db_session: Session,
) -> None:
    alice, a_headers = register(client, "alice")
    _, b_headers = register(client, "bob")
    app_id = make_application(db_session, alice)
    f08 = FakeF08()
    app.dependency_overrides[current_verification_provider] = lambda: f08

    assert client.post(
        finalization_url(app_id), headers=b_headers,
        json={"statement_ids": [str(uuid4())]},
    ).status_code == 404

    assert client.post(
        finalization_url(app_id), headers=a_headers,
        json={
            "statement_ids": [str(uuid4())],
            "verification_status": "VERIFIED",
            "approval_status": "APPROVED",
            "text": "Forged",
        },
    ).status_code == 422

    chosen = str(uuid4())
    assert client.post(
        finalization_url(app_id), headers=a_headers,
        json={"statement_ids": [chosen, chosen]},
    ).status_code == 422


def test_historical_drafts_and_foreign_versions_are_never_trusted_export(
    client: TestClient, db_session: Session,
) -> None:
    alice, a_headers = register(client, "draft-owner")
    _, b_headers = register(client, "draft-stranger")
    app_id = make_application(db_session, alice)
    draft = ApplicationService(db_session).save_resume_version(
        user_id=alice, application_id=app_id,
        content=ResumeVersionContent(),
    )
    db_session.commit()
    assert client.get(
        trusted_export_url(draft.id), headers=a_headers
    ).status_code == 409
    assert client.get(
        trusted_export_url(draft.id), headers=b_headers
    ).status_code == 404

    # The generic historical-save endpoint cannot mint F09_APPROVED origin.
    response = client.post(
        f"/api/applications/{app_id}/resume-versions",
        headers=a_headers,
        json={
            "statements": [{
                "statement_id": str(uuid4()),
                "text": "Forged trusted approval",
                "evidence_ids": [],
                "verification_status": "VERIFIED",
                "approval_status": "APPROVED",
                "origin": "F09_APPROVED",
            }],
        },
    )
    assert response.status_code == 422


def test_reapproval_of_identical_text_on_new_revision_does_not_reauthorize_old_version(
    client: TestClient, db_session: Session,
) -> None:
    """An updated F08 revision is material even when the visible text is equal."""
    owner, headers = register(client, "same-text-revision")
    application_id = make_application(db_session, owner)
    evidence_id = make_evidence(db_session, owner)
    statement_id = uuid4()
    f08 = FakeF08()
    approve_statement(db_session, f08, owner, statement_id, evidence_id)
    app.dependency_overrides[current_verification_provider] = lambda: f08

    first = client.post(
        finalization_url(application_id), headers=headers,
        json={"statement_ids": [str(statement_id)]},
    )
    assert first.status_code == 201
    previous_id = UUID(first.json()["id"])
    assert first.json()["snapshot"]["statements"][0]["verification_revision"] == (
        "revision-one-current"
    )
    assert client.get(trusted_export_url(previous_id), headers=headers).status_code == 200

    # F08 may rotate a revision for relevant evidence fields not shown in the
    # F13 snapshot, or another re-verification of exactly the same claim.
    f08.set(
        owner, statement_id, evidence_id,
        revision="revision-two-updated",
        text="Developed Python integration tests.",
    )
    assert client.get(trusted_export_url(previous_id), headers=headers).status_code == 409

    StatementReviewService(db_session, f08).decide(
        user_id=owner, statement_id=statement_id,
        decision=ReviewDecision.APPROVED,
        expected_revision="revision-two-updated",
    )
    db_session.commit()

    # A new user approval on the new revision cannot retroactively authorize
    # the already-saved snapshot, even though its visible content matches.
    assert client.get(trusted_export_url(previous_id), headers=headers).status_code == 409
    second = client.post(
        finalization_url(application_id), headers=headers,
        json={"statement_ids": [str(statement_id)]},
    )
    assert second.status_code == 201
    assert second.json()["version_number"] == 2
    assert second.json()["snapshot"]["statements"][0]["verification_revision"] == (
        "revision-two-updated"
    )
    assert client.get(
        trusted_export_url(UUID(second.json()["id"])), headers=headers
    ).status_code == 200


def test_trusted_origin_without_revision_is_invalid() -> None:
    from pydantic import ValidationError

    from app.modules.applications.schemas import ProvenanceSnapshotItem

    with pytest.raises(ValidationError):
        ProvenanceSnapshotItem(
            statement_id=uuid4(),
            text="Untrusted server-origin assertion.",
            evidence_ids=(),
            verification_status="VERIFIED",
            approval_status="APPROVED",
            origin="F09_APPROVED",
        )
