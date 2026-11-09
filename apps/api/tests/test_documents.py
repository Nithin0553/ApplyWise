"""Tests for F10 document rendering and export eligibility."""

from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from docx import Document

from app.modules.documents.renderer import render_resume
from app.modules.documents.schemas import (
    DocumentFormat,
    ResumeDocument,
    ResumeTemplate,
)
from app.modules.documents.service import (
    DocumentNotFinalizedError,
    validate_export_eligibility,
)


@pytest.fixture
def sample_resume():
    return ResumeDocument(
        full_name="Alex Morgan",
        target_role="IT Support Specialist",
        company="Example Company",
        statements=(
            "Troubleshoot hardware and software issues.",
            "Prepare computers for new employees.",
            "Document technical procedures.",
        ),
    )


@pytest.mark.parametrize(
    "template",
    [ResumeTemplate.STANDARD, ResumeTemplate.COMPACT],
)
def test_pdf_generation(sample_resume, template):
    resume = sample_resume.model_copy(update={"template": template})

    result = render_resume(resume, DocumentFormat.PDF)

    assert result.startswith(b"%PDF")
    assert len(result) > 100


@pytest.mark.parametrize(
    "template",
    [ResumeTemplate.STANDARD, ResumeTemplate.COMPACT],
)
def test_docx_generation(sample_resume, template):
    resume = sample_resume.model_copy(update={"template": template})

    result = render_resume(resume, DocumentFormat.DOCX)

    assert result.startswith(b"PK")

    with ZipFile(BytesIO(result)) as archive:
        assert "word/document.xml" in archive.namelist()

    document = Document(BytesIO(result))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    assert "Alex Morgan" in text
    assert "IT Support Specialist" in text
    assert "Troubleshoot hardware and software issues." in text


def test_empty_resume_statements_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ResumeDocument(
            full_name="Alex Morgan",
            target_role="IT Support Specialist",
            statements=(),
        )


def test_unsupported_format_rejected(sample_resume):
    with pytest.raises(ValueError):
        render_resume(sample_resume, "txt")

@pytest.fixture
def approved_snapshot():
    statement = SimpleNamespace(
        text="Developed and maintained technical documentation.",
        verification_status="VERIFIED",
        approval_status="APPROVED",
        origin="F09_APPROVED",
        evidence_ids=("evidence-001",),
    )

    return SimpleNamespace(statements=(statement,))


def test_verified_approved_resume_is_eligible(approved_snapshot):
    validate_export_eligibility(approved_snapshot)


def test_explicitly_approved_inferred_resume_is_not_statically_blocked(approved_snapshot):
    """Current F09 approval is still checked in F13 at export time."""
    statement = approved_snapshot.statements[0]
    inferred = SimpleNamespace(**{**vars(statement), "verification_status": "INFERRED"})
    validate_export_eligibility(SimpleNamespace(statements=(inferred,)))


@pytest.mark.parametrize(
    "field,value",
    [
        ("verification_status", "UNSUPPORTED"),
        ("approval_status", "UNREVIEWED"),
        ("origin", "DRAFT_USER_REVIEWED"),
        ("evidence_ids", ()),
        ("text", "   "),
    ],
)
def test_unfinalized_resume_rejected(approved_snapshot, field, value):
    statement = approved_snapshot.statements[0]

    modified_statement = SimpleNamespace(
        **{
            **vars(statement),
            field: value,
        }
    )

    modified_snapshot = SimpleNamespace(
        statements=(modified_statement,)
    )

    with pytest.raises(DocumentNotFinalizedError):
        validate_export_eligibility(modified_snapshot)


def test_resume_without_statements_rejected():
    snapshot = SimpleNamespace(statements=())

    with pytest.raises(DocumentNotFinalizedError):
        validate_export_eligibility(snapshot)
def test_adapter_preserves_trusted_statement_text_and_template():
    from uuid import uuid4

    from app.modules.applications.schemas import (
        ApprovalSnapshotStatus,
        EvidenceSnapshotItem,
        ProvenanceOrigin,
        ProvenanceSnapshotItem,
        ResumeVersionContent,
        VerificationSnapshotStatus,
    )
    from app.modules.documents.adapter import build_resume_document
    from app.modules.documents.schemas import ResumeTemplate

    evidence_id = uuid4()

    evidence = EvidenceSnapshotItem(
        evidence_id=evidence_id,
        evidence_type="experience",
        title="Software Developer",
        organization="Example Company",
        role="Developer",
        description="Developed backend services",
        approved_at="2026-11-01T12:00:00Z",
    )

    statement = ProvenanceSnapshotItem(
        statement_id=uuid4(),
        text="Developed Python APIs for internal applications.",
        evidence_ids=(evidence_id,),
        verification_status=VerificationSnapshotStatus.VERIFIED,
        approval_status=ApprovalSnapshotStatus.APPROVED,
        origin=ProvenanceOrigin.F09_APPROVED,
        verification_revision="revision-12345678",
    )

    content = ResumeVersionContent(
        evidence=(evidence,),
        statements=(statement,),
    )

    document = build_resume_document(
        full_name="Test Applicant",
        target_role="Backend Developer",
        company="Example Company",
        content=content,
        template=ResumeTemplate.COMPACT,
    )

    assert document.full_name == "Test Applicant"
    assert document.target_role == "Backend Developer"
    assert document.company == "Example Company"
    assert document.statements == (
        "Developed Python APIs for internal applications.",
    )
    assert document.template == ResumeTemplate.COMPACT
