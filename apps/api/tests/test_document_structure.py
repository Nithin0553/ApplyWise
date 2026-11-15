"""Issue #85: evidence-backed sections and metadata freshness."""
from datetime import date
from io import BytesIO
from uuid import uuid4

import pytest
from docx import Document
from pypdf import PdfReader

from app.main import app
from app.modules.applications.schemas import (
    EvidenceSnapshotItem,
    ProvenanceSnapshotItem,
    ResumeVersionContent,
)
from app.modules.documents.adapter import build_resume_document
from app.modules.documents.renderer import render_resume
from app.modules.documents.schemas import DocumentFormat, ResumeTemplate
from app.modules.evidence.models import EvidenceRecord
from app.modules.evidence.schemas import EvidenceCreate
from app.modules.evidence.service import EvidenceService
from app.modules.statement_review.contract import UnavailableVerificationProvider
from app.modules.statement_review.dependencies import current_verification_provider
from tests.test_documents_api import prepare_trusted_resume
from tests.test_f13_trusted_finalization import (
    FakeF08,
    approve_statement,
    finalization_url,
    make_application,
    register,
)


def evidence(kind, **kwargs):
    return EvidenceSnapshotItem(
        evidence_id=uuid4(), evidence_type=kind, title=f"{kind} title",
        approved_at="2026-11-01T12:00:00Z", **kwargs,
    )


def statement(*records):
    return ProvenanceSnapshotItem(
        statement_id=uuid4(), text="An approved claim without employer or dates.",
        evidence_ids=tuple(record.evidence_id for record in records),
        verification_status="VERIFIED", approval_status="APPROVED",
        origin="F09_APPROVED", verification_revision="revision-12345678",
    )


def build(records, statements, template=ResumeTemplate.STANDARD):
    return build_resume_document(
        full_name="Test Applicant", target_role="Engineer", company=None,
        content=ResumeVersionContent(evidence=tuple(records), statements=tuple(statements)),
        template=template,
    )


def extract(data, output_format):
    if output_format == DocumentFormat.PDF:
        return "\n".join(page.extract_text() for page in PdfReader(BytesIO(data)).pages)
    return "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)


def output_text(document, output_format):
    return extract(render_resume(document, output_format), output_format)


@pytest.mark.parametrize("template", list(ResumeTemplate))
def test_all_sections_have_identical_content_in_both_formats(template):
    records = [
        evidence("work_experience", organization="Evidence Employer", role="Analyst",
                 start_date=date(2020, 1, 2), end_date=date(2024, 3, 4)),
        evidence("education", organization="Evidence University"),
        evidence("skill", skill_name="Python"),
        evidence("certification", credential="Evidence Credential"),
    ]
    document = build(records, [statement(record) for record in records], template)
    assert [s.heading for s in document.sections] == [
        "Experience", "Education", "Skills", "Certifications",
    ]
    pdf = output_text(document, DocumentFormat.PDF)
    docx = output_text(document, DocumentFormat.DOCX)
    assert pdf.replace("- An approved", "An approved").splitlines() == docx.splitlines()
    for expected in (
        "Evidence Employer", "Analyst", "2020-01-02 - 2024-03-04",
        "Evidence University", "Python", "Evidence Credential",
    ):
        assert expected in pdf
    assert "Summary" not in pdf
    assert document.sections[0].entries[0].evidence_ids == (records[0].evidence_id,)


def test_missing_sections_and_unselected_evidence_are_omitted():
    skill = evidence("skill")
    unselected = evidence("education", organization="Must not appear")
    document = build([skill, unselected], [statement(skill)])
    assert [s.heading for s in document.sections] == ["Skills"]
    for format in DocumentFormat:
        text = output_text(document, format)
        for absent in ("Summary", "Education", "Experience", "Certifications", "Must not appear"):
            assert absent not in text


def test_multiple_sources_do_not_attribute_combined_claim_to_one_employer():
    records = [evidence("work_experience", organization=name) for name in ("One", "Two")]
    claim = statement(*records)
    document = build(records, [claim])
    jobs, combined = document.sections
    assert jobs.heading == "Experience"
    assert all(not entry.statements for entry in jobs.entries)
    assert combined.heading == "Additional Qualifications"
    assert combined.entries[0].evidence_ids == claim.evidence_ids
    assert combined.entries[0].statement_ids == (claim.statement_id,)
    assert document.statements == (claim.text,)


def test_unknown_end_date_does_not_assert_present_employment():
    job = evidence("work_experience", start_date=date(2020, 1, 1))
    document = build([job], [statement(job)])
    for format in DocumentFormat:
        text = output_text(document, format)
        assert "Started 2020-01-01" in text
        assert "Present" not in text


def test_f13_carries_f02_metadata_to_preview_and_exports(client, db_session):
    owner, headers = register(client, "structured")
    application_id = make_application(db_session, owner)
    service = EvidenceService(db_session)
    f08 = FakeF08()
    statement_ids = []
    for kind in ("work_experience", "education", "skill", "certification"):
        record = service.create(user_id=owner, data=EvidenceCreate(
            evidence_type=kind, title=f"{kind} title", organization="Recorded Organization",
            role="Recorded Role", start_date=date(2020, 1, 2), end_date=date(2024, 3, 4),
            skill_name="Recorded Skill", credential="Recorded Credential",
        ))
        service.approve(user_id=owner, evidence_id=record.id)
        sid = uuid4()
        approve_statement(db_session, f08, owner, sid, record.id)
        statement_ids.append(str(sid))
    app.dependency_overrides[current_verification_provider] = lambda: f08
    finalized = client.post(finalization_url(application_id), headers=headers,
                            json={"statement_ids": statement_ids})
    assert finalized.status_code == 201, finalized.text
    snapshot = finalized.json()["snapshot"]
    assert snapshot["evidence"][0]["start_date"] == "2020-01-02"
    base = f'/api/documents/resume-versions/{finalized.json()["id"]}'
    preview = client.get(base + "/preview", headers=headers)
    assert preview.status_code == 200, preview.text
    assert [s["heading"] for s in preview.json()["sections"]] == [
        "Experience", "Education", "Skills", "Certifications",
    ]
    for format in DocumentFormat:
        response = client.get(base + "/export", params={"format": format}, headers=headers)
        assert response.status_code == 200
        text = extract(response.content, format)
        for expected in ("Recorded Organization", "2020-01-02 - 2024-03-04",
                         "Recorded Skill", "Recorded Credential"):
            assert expected in text


@pytest.mark.parametrize("field,value", [
    ("start_date", date(2021, 1, 1)), ("end_date", date(2025, 1, 1)),
    ("organization", "Changed employer"), ("role", "Changed role"),
    ("skill_name", "Changed skill"), ("credential", "Changed credential"),
])
def test_metadata_change_blocks_preview_and_both_exports(client, db_session, field, value):
    data = prepare_trusted_resume(client, db_session, f"metadata-{field}")
    # Even an out-of-band edit that leaves approval intact must fail closed.
    record = db_session.get(EvidenceRecord, data["evidence_id"])
    setattr(record, field, value)
    db_session.commit()
    base = f'/api/documents/resume-versions/{data["version_id"]}'
    for path in ("/preview", "/export?format=pdf", "/export?format=docx"):
        assert client.get(base + path, headers=data["headers"]).status_code == 409


def test_preview_rechecks_auth_owner_revocation_and_verifier(client, db_session):
    data = prepare_trusted_resume(client, db_session, "preview-security")
    url = f'/api/documents/resume-versions/{data["version_id"]}/preview'
    assert client.get(url).status_code == 401
    _, other_headers = register(client, "preview-other")
    assert client.get(url, headers=other_headers).status_code == 404
    app.dependency_overrides[current_verification_provider] = UnavailableVerificationProvider
    assert client.get(url, headers=data["headers"]).status_code == 503
    app.dependency_overrides[current_verification_provider] = lambda: data["f08"]
    EvidenceService(db_session).unconfirm(user_id=data["owner"], evidence_id=data["evidence_id"])
    db_session.commit()
    assert client.get(url, headers=data["headers"]).status_code == 409
