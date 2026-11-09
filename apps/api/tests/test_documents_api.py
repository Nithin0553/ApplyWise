"""F10 document export API tests."""

from io import BytesIO
from unittest.mock import patch
from uuid import UUID, uuid4
from zipfile import ZipFile

import pytest
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.modules.evidence.service import EvidenceService
from app.modules.statement_review.contract import (
    UnavailableVerificationProvider,
    current_verification_provider,
)
from tests.test_f13_trusted_finalization import (
    FakeF08,
    approve_statement,
    finalization_url,
    make_application,
    make_evidence,
    register,
)


def test_export_requires_authentication():
    """Anonymous users cannot export resumes."""

    client = TestClient(app)

    response = client.get(
        f"/api/documents/resume-versions/{uuid4()}/export",
        params={"format": "pdf"},
    )

    assert response.status_code == 401


def test_export_rejects_unsupported_format():
    """Unsupported formats cannot be requested."""

    client = TestClient(app)

    response = client.get(
        f"/api/documents/resume-versions/{uuid4()}/export",
        params={"format": "txt"},
    )

    assert response.status_code in (401, 422)



def document_export_url(version_id: UUID, output_format: str) -> str:
    return (
        f"/api/documents/resume-versions/{version_id}/export"
        f"?format={output_format}"
    )


def prepare_trusted_resume(
    client: TestClient,
    db_session: Session,
    suffix: str,
):
    """Create an F13-finalized resume with current F09/F08 approval."""

    owner, headers = register(client, suffix)
    application_id = make_application(db_session, owner)
    evidence_id = make_evidence(db_session, owner)
    statement_id = uuid4()

    f08 = FakeF08()

    approve_statement(
        db_session,
        f08,
        owner,
        statement_id,
        evidence_id,
    )

    app.dependency_overrides[current_verification_provider] = lambda: f08

    response = client.post(
        finalization_url(application_id),
        headers=headers,
        json={"statement_ids": [str(statement_id)]},
    )

    assert response.status_code == 201, response.text

    return {
        "owner": owner,
        "headers": headers,
        "version_id": UUID(response.json()["id"]),
        "evidence_id": evidence_id,
        "statement_id": statement_id,
        "f08": f08,
    }


@pytest.mark.parametrize("output_format", ["pdf", "docx"])
def test_trusted_resume_download_succeeds(
    client: TestClient,
    db_session: Session,
    output_format: str,
):
    data = prepare_trusted_resume(
        client,
        db_session,
        f"download-{output_format}",
    )

    response = client.get(
        document_export_url(data["version_id"], output_format),
        headers=data["headers"],
    )

    assert response.status_code == 200, response.text
    assert "attachment" in response.headers["content-disposition"]
    assert f".{output_format}" in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"

    if output_format == "pdf":
        assert response.headers["content-type"].startswith("application/pdf")
        assert response.content.startswith(b"%PDF-")

    else:
        assert "wordprocessingml.document" in response.headers["content-type"]

        with ZipFile(BytesIO(response.content)) as archive:
            assert "word/document.xml" in archive.namelist()

        document = Document(BytesIO(response.content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)

        assert "Synthetic User" in text
        assert "Engineer" in text
        assert "Developed Python integration tests." in text


def test_changed_verification_revision_blocks_download(
    client: TestClient,
    db_session: Session,
):
    data = prepare_trusted_resume(client, db_session, "revision-block")

    data["f08"].set(
        data["owner"],
        data["statement_id"],
        data["evidence_id"],
        revision="revision-two-changed",
    )

    with patch(
        "app.modules.documents.router.render_resume"
    ) as renderer:
        response = client.get(
            document_export_url(data["version_id"], "pdf"),
            headers=data["headers"],
        )

    assert response.status_code == 409
    renderer.assert_not_called()


def test_revoked_evidence_blocks_download(
    client: TestClient,
    db_session: Session,
):
    data = prepare_trusted_resume(client, db_session, "evidence-block")

    EvidenceService(db_session).unconfirm(
        user_id=data["owner"],
        evidence_id=data["evidence_id"],
    )
    db_session.commit()

    with patch(
        "app.modules.documents.router.render_resume"
    ) as renderer:
        response = client.get(
            document_export_url(data["version_id"], "docx"),
            headers=data["headers"],
        )

    assert response.status_code == 409
    renderer.assert_not_called()


def test_unavailable_verification_blocks_download(
    client: TestClient,
    db_session: Session,
):
    data = prepare_trusted_resume(client, db_session, "f08-unavailable")

    # Simulate F08 outage explicitly; the real provider may be wired on main.
    app.dependency_overrides[current_verification_provider] = UnavailableVerificationProvider

    with patch(
        "app.modules.documents.router.render_resume"
    ) as renderer:
        response = client.get(
            document_export_url(data["version_id"], "pdf"),
            headers=data["headers"],
        )

    assert response.status_code == 503
    renderer.assert_not_called()


def test_foreign_user_cannot_download_resume(
    client: TestClient,
    db_session: Session,
):
    data = prepare_trusted_resume(client, db_session, "owner-export")

    _, foreign_headers = register(client, "foreign-export")

    with patch(
        "app.modules.documents.router.render_resume"
    ) as renderer:
        response = client.get(
            document_export_url(data["version_id"], "pdf"),
            headers=foreign_headers,
        )

    assert response.status_code == 404
    renderer.assert_not_called()
