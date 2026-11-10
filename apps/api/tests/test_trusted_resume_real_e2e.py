"""Real F02 → F08 → F09 → F13 → F10 API integration, without fake providers.

This is a synthetic, isolated SQLite test, not a production/browser STD
execution. In particular it tests the *installed* F08 provider instead of
injecting FakeF08 as the individual F09/F13/F10 unit tests do.
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfReader

from tests.test_f08_f09_integration import COVERED_CLAIM, _auth, _seed, _verify


def _application(client: TestClient, token: str) -> str:
    result = client.post(
        "/api/applications/",
        json={"company_name": "Example Company", "role_title": "QA Engineer"},
        headers=_auth(token),
    )
    assert result.status_code == 201, result.text
    return result.json()["id"]


def _approve(client: TestClient, token: str, statement_id: str, revision: str) -> dict:
    result = client.post(
        f"/api/statement-review/{statement_id}/decision",
        json={"decision": "APPROVED", "expected_revision": revision},
        headers=_auth(token),
    )
    assert result.status_code == 200, result.text
    assert result.json()["finalization_eligible"] is True
    return result.json()


def _finalize(
    client: TestClient, token: str, application_id: str, statement_id: str
) -> dict:
    result = client.post(
        f"/api/applications/{application_id}/trusted-finalize",
        json={"statement_ids": [statement_id]},
        headers=_auth(token),
    )
    assert result.status_code == 201, result.text
    return result.json()


def _export(client: TestClient, token: str, version_id: str, output: str):
    return client.get(
        f"/api/documents/resume-versions/{version_id}/export",
        params={"format": output},
        headers=_auth(token),
    )


@pytest.mark.parametrize("output", ["pdf", "docx"])
def test_real_verified_claim_finalizes_and_exports_in_both_formats(
    client: TestClient, output: str,
) -> None:
    token, evidence_id = _seed(client, "real-export-" + output + "@example.edu")
    statement = _verify(client, token, COVERED_CLAIM, evidence_id)
    assert statement["status"] == "VERIFIED"
    app_id = _application(client, token)

    _approve(client, token, statement["statement_id"], statement["revision"])
    version = _finalize(client, token, app_id, statement["statement_id"])
    saved = version["snapshot"]["statements"][0]
    assert saved["origin"] == "F09_APPROVED"
    assert saved["verification_status"] == "VERIFIED"
    assert saved["verification_revision"] == statement["revision"]
    assert saved["text"] == COVERED_CLAIM
    assert version["snapshot"]["evidence"][0]["evidence_id"] == evidence_id

    response = _export(client, token, version["id"], output)
    assert response.status_code == 200, response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    assert f".{output}" in response.headers["content-disposition"]
    if output == "pdf":
        assert response.content.startswith(b"%PDF-")
        text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
    else:
        assert response.content.startswith(b"PK")
        with ZipFile(BytesIO(response.content)) as archive:
            assert "word/document.xml" in archive.namelist()
        text = "\n".join(
            paragraph.text
            for paragraph in Document(BytesIO(response.content)).paragraphs
        )
    assert "regression suites" in text
    assert "QA Engineer" in text

    # The historical F13 snapshot persists, but is not itself export authority.
    stored = client.get(
        f"/api/applications/resume-versions/{version['id']}", headers=_auth(token)
    )
    assert stored.status_code == 200
    assert stored.json()["snapshot"]["statements"][0] == saved


def test_real_inferred_claim_requires_user_approval_and_keeps_label(
    client: TestClient,
) -> None:
    token, evidence_id = _seed(client, "real-inferred-export@example.edu")
    claim = "Improved release confidence for the billing organisation"
    statement = _verify(client, token, claim, evidence_id)
    assert statement["status"] == "INFERRED"
    app_id = _application(client, token)

    pending = client.post(
        f"/api/applications/{app_id}/trusted-finalize",
        json={"statement_ids": [statement["statement_id"]]},
        headers=_auth(token),
    )
    assert pending.status_code == 409

    _approve(client, token, statement["statement_id"], statement["revision"])
    version = _finalize(client, token, app_id, statement["statement_id"])
    item = version["snapshot"]["statements"][0]
    assert item["verification_status"] == "INFERRED"
    assert item["verification_revision"] == statement["revision"]
    assert item["approval_status"] == "APPROVED"
    assert _export(client, token, version["id"], "docx").status_code == 200


def test_real_unsupported_claim_never_reaches_finalization_or_document_render(
    client: TestClient,
) -> None:
    token, evidence_id = _seed(client, "real-unsupported-export@example.edu")
    statement = _verify(client, token, "Reduced regression runtime by 85%", evidence_id)
    assert statement["status"] == "UNSUPPORTED"
    app_id = _application(client, token)

    decision = client.post(
        f"/api/statement-review/{statement['statement_id']}/decision",
        json={"decision": "APPROVED", "expected_revision": statement["revision"]},
        headers=_auth(token),
    )
    assert decision.status_code == 409
    denied = client.post(
        f"/api/applications/{app_id}/trusted-finalize",
        json={"statement_ids": [statement["statement_id"]]},
        headers=_auth(token),
    )
    assert denied.status_code == 409
    assert client.get(
        f"/api/applications/{app_id}/resume-versions", headers=_auth(token)
    ).json() == []


def test_real_evidence_revocation_invalidates_old_export_and_blocks_renderer(
    client: TestClient,
) -> None:
    token, evidence_id = _seed(client, "real-stale-export@example.edu")
    statement = _verify(client, token, COVERED_CLAIM, evidence_id)
    app_id = _application(client, token)
    _approve(client, token, statement["statement_id"], statement["revision"])
    version = _finalize(client, token, app_id, statement["statement_id"])

    before = _export(client, token, version["id"], "pdf")
    assert before.status_code == 200

    revoked = client.post(
        f"/api/evidence/{evidence_id}/unconfirm", headers=_auth(token)
    )
    assert revoked.status_code == 200, revoked.text
    updated = client.get(
        f"/api/statement-review/{statement['statement_id']}", headers=_auth(token)
    )
    assert updated.status_code == 200
    assert updated.json()["verification_revision"] != statement["revision"]
    assert updated.json()["review_status"] == "STALE"
    assert updated.json()["finalization_eligible"] is False

    with patch("app.modules.documents.router.render_resume") as renderer:
        stale = _export(client, token, version["id"], "pdf")
    assert stale.status_code == 409
    renderer.assert_not_called()
    assert client.get(
        "/api/statement-review/approved", headers=_auth(token)
    ).json() == []
    # Immutable history still exists; it does not grant F10 export permission.
    snapshot = client.get(
        f"/api/applications/resume-versions/{version['id']}", headers=_auth(token)
    )
    assert snapshot.status_code == 200
    assert snapshot.json()["snapshot"]["statements"][0]["text"] == COVERED_CLAIM


def test_real_foreign_owner_cannot_finalize_or_export(
    client: TestClient,
) -> None:
    token, evidence_id = _seed(client, "real-owner-a@example.edu")
    statement = _verify(client, token, COVERED_CLAIM, evidence_id)
    app_id = _application(client, token)
    _approve(client, token, statement["statement_id"], statement["revision"])
    version = _finalize(client, token, app_id, statement["statement_id"])

    foreign_token, _ = _seed(client, "real-owner-b@example.edu")
    attempt = client.post(
        f"/api/applications/{app_id}/trusted-finalize",
        json={"statement_ids": [statement["statement_id"]]},
        headers=_auth(foreign_token),
    )
    assert attempt.status_code == 404
    with patch("app.modules.documents.router.render_resume") as renderer:
        foreign_export = _export(client, foreign_token, version["id"], "docx")
    assert foreign_export.status_code == 404
    renderer.assert_not_called()
