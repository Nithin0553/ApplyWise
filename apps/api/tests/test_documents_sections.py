"""F10 resume structure: sections derived from the evidence each claim cites.

The export used to be a flat bullet list under one "Relevant Experience"
heading, because the adapter kept only each statement's text and dropped the
link to the evidence behind it. The typed evidence was in the snapshot the
whole time. These tests pin the grouping to provenance: the section a claim
lands in is decided by the kind of evidence it cites, never by reading its
wording, so the same approved content always produces the same document.
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

from docx import Document

from app.modules.applications.schemas import (
    ApprovalSnapshotStatus,
    EvidenceSnapshotItem,
    ProvenanceOrigin,
    ProvenanceSnapshotItem,
    ResumeVersionContent,
    VerificationSnapshotStatus,
)
from app.modules.documents.adapter import build_resume_document
from app.modules.documents.renderer import render_resume
from app.modules.documents.schemas import (
    DocumentFormat,
    ResumeDocument,
    ResumeTemplate,
)

NOW = datetime.now(UTC)


def evidence(evidence_type, title, organization=None, role=None):
    return EvidenceSnapshotItem(
        evidence_id=uuid4(),
        evidence_type=evidence_type,
        title=title,
        organization=organization,
        role=role,
        approved_at=NOW,
    )


def statement(text, *records):
    return ProvenanceSnapshotItem(
        statement_id=uuid4(),
        text=text,
        evidence_ids=tuple(record.evidence_id for record in records),
        verification_status=VerificationSnapshotStatus.VERIFIED,
        approval_status=ApprovalSnapshotStatus.APPROVED,
        origin=ProvenanceOrigin.F09_APPROVED,
        verification_revision="v1-" + ("0" * 32),
    )


def build(*pairs, template=ResumeTemplate.STANDARD):
    records, statements = [], []
    for record, text in pairs:
        if record not in records:
            records.append(record)
        statements.append(statement(text, record))
    content = ResumeVersionContent(
        evidence=tuple(records), statements=tuple(statements)
    )
    return build_resume_document(
        full_name="Synthetic Applicant",
        target_role="Quality Assurance Engineer",
        company="Example Company",
        content=content,
        template=template,
    )


def test_statements_are_grouped_by_the_evidence_they_cite():
    job = evidence("work_experience", "QA Engineer", "Example Company", "QA Engineer")
    cert = evidence("certification", "ISTQB Foundation Level")
    skill = evidence("skill", "Python")

    document = build(
        (job, "Built automated regression suites."),
        (cert, "Hold the ISTQB Foundation Level certification."),
        (skill, "Advanced Python, alongside Java and SQL."),
    )

    headings = [section.heading for section in document.sections]
    assert headings == ["Professional Experience", "Certifications", "Technical Skills"]


def test_sections_follow_a_fixed_order_regardless_of_approval_order():
    skill = evidence("skill", "Python")
    job = evidence("work_experience", "QA Engineer", "Example Company", "QA Engineer")
    education = evidence("education", "M.S. Computer Science", "Example University")

    # Approved skill-first; experience must still lead the document.
    document = build(
        (skill, "Advanced Python."),
        (job, "Built automated regression suites."),
        (education, "Completed an M.S. in Computer Science."),
    )

    assert [section.heading for section in document.sections] == [
        "Professional Experience",
        "Education",
        "Technical Skills",
    ]


def test_one_employer_collects_its_statements_under_a_single_entry():
    job = evidence("work_experience", "QA Engineer", "Example Company", "QA Engineer")

    document = build(
        (job, "Built automated regression suites."),
        (job, "Owned release-candidate test cycles."),
    )

    experience = document.sections[0]
    assert len(experience.entries) == 1
    entry = experience.entries[0]
    assert entry.organization == "Example Company"
    assert entry.role == "QA Engineer"
    assert len(entry.bullets) == 2


def test_a_responsibility_is_filed_under_the_job_it_cites():
    # A statement citing both the job and a responsibility record belongs on
    # the job, not in a section of its own.
    job = evidence("work_experience", "QA Engineer", "Example Company", "QA Engineer")
    duty = evidence("responsibility", "Release sign-off")

    content = ResumeVersionContent(
        evidence=(duty, job),  # responsibility cited first on purpose
        statements=(statement("Signed off release candidates.", duty, job),),
    )
    document = build_resume_document(
        full_name="Synthetic Applicant",
        target_role="Quality Assurance Engineer",
        company="Example Company",
        content=content,
        template=ResumeTemplate.STANDARD,
    )

    assert [section.heading for section in document.sections] == [
        "Professional Experience"
    ]
    assert document.sections[0].entries[0].organization == "Example Company"


def test_evidence_without_an_organization_renders_as_plain_bullets():
    cert = evidence("certification", "ISTQB Foundation Level")

    document = build((cert, "Hold the ISTQB Foundation Level certification."))

    entry = document.sections[0].entries[0]
    assert entry.organization is None
    assert entry.role is None


def test_flat_statements_are_preserved_alongside_the_sections():
    job = evidence("work_experience", "QA Engineer", "Example Company", "QA Engineer")

    document = build((job, "Built automated regression suites."))

    # The flat list stays, so nothing that reads `statements` breaks.
    assert document.statements == ("Built automated regression suites.",)


def test_docx_renders_the_section_headings():
    job = evidence("work_experience", "QA Engineer", "Example Company", "QA Engineer")
    cert = evidence("certification", "ISTQB Foundation Level")

    document = build(
        (job, "Built automated regression suites."),
        (cert, "Hold the ISTQB Foundation Level certification."),
    )
    rendered = Document(BytesIO(render_resume(document, DocumentFormat.DOCX)))

    headings = [
        paragraph.text
        for paragraph in rendered.paragraphs
        if paragraph.style.name == "Heading 1"
    ]
    assert headings == ["Professional Experience", "Certifications"]

    text = "\n".join(paragraph.text for paragraph in rendered.paragraphs)
    assert "QA Engineer, Example Company" in text
    # The old single heading is gone.
    assert "Relevant Experience" not in text


def test_a_document_without_sections_still_renders():
    # A caller that supplies only a flat list keeps the previous output.
    document = ResumeDocument(
        full_name="Synthetic Applicant",
        target_role="Quality Assurance Engineer",
        statements=("Built automated regression suites.",),
    )

    rendered = Document(BytesIO(render_resume(document, DocumentFormat.DOCX)))
    text = "\n".join(paragraph.text for paragraph in rendered.paragraphs)

    assert "Relevant Experience" in text
    assert "Built automated regression suites." in text
    assert render_resume(document, DocumentFormat.PDF).startswith(b"%PDF")
