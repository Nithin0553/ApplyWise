"""F10 resume rendering: ATS-friendly PDF and DOCX output."""

from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.shared import Inches, Pt
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from .schemas import DocumentFormat, ResumeDocument, ResumeEntry, ResumeTemplate


def _entry_label(entry: ResumeEntry) -> str:
    """The line that heads an entry, e.g. 'Associate QA Engineer, Model N'.

    Empty when the evidence carried neither an organization nor a role, which
    is normal for certifications and skills; those read as plain bullets.
    """
    parts = [part for part in (entry.role, entry.organization) if part]
    return ", ".join(parts)


def render_resume(
    resume: ResumeDocument,
    output_format: DocumentFormat,
) -> bytes:
    """Render validated resume data into PDF or DOCX bytes."""
    if output_format == DocumentFormat.PDF:
        return _render_pdf(resume)
    if output_format == DocumentFormat.DOCX:
        return _render_docx(resume)
    raise ValueError(f"Unsupported document format: {output_format}")


def _render_docx(resume: ResumeDocument) -> bytes:
    document = Document()

    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    compact = resume.template == ResumeTemplate.COMPACT
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(9 if compact else 10)

    normal.paragraph_format.space_after = Pt(3 if compact else 6)

    heading = document.add_heading(resume.full_name, level=0)
    heading.style = document.styles["Title"]

    document.add_paragraph(resume.target_role)

    if resume.company:
        document.add_paragraph(f"Target company: {resume.company}")

    if resume.sections:
        for section in resume.sections:
            document.add_heading(section.heading, level=1)
            for entry in section.entries:
                label = _entry_label(entry)
                if label:
                    paragraph = document.add_paragraph()
                    paragraph.add_run(label).bold = True
                for bullet in entry.bullets:
                    document.add_paragraph(bullet, style="List Bullet")
    else:
        # A caller that supplied only a flat list of statements.
        document.add_heading("Relevant Experience", level=1)

        for statement in resume.statements:
            document.add_paragraph(statement, style="List Bullet")

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _render_pdf(resume: ResumeDocument) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    page_width, page_height = letter
    margin = 55
    y = page_height - margin

    compact = resume.template == ResumeTemplate.COMPACT
    body_size = 9 if compact else 10
    line_height = 12 if compact else 15

    def draw_line(text: str, font: str, size: int, spacing: int) -> None:
        nonlocal y

        pdf.setFont(font, size)

        available_width = page_width - (2 * margin)
        lines = simpleSplit(text, font, size, available_width)

        for line in lines:
            if y < margin + line_height:
                pdf.showPage()
                y = page_height - margin
                pdf.setFont(font, size)

            pdf.drawString(margin, y, line)
            y -= line_height

        y -= spacing

    draw_line(resume.full_name, "Helvetica-Bold", 18, 5)
    draw_line(resume.target_role, "Helvetica", 11, 4)

    if resume.company:
        draw_line(f"Target company: {resume.company}", "Helvetica", 10, 10)

    y -= 10

    if resume.sections:
        for section in resume.sections:
            draw_line(section.heading.upper(), "Helvetica-Bold", 12, 6)
            for entry in section.entries:
                label = _entry_label(entry)
                if label:
                    draw_line(label, "Helvetica-Bold", body_size + 1, 3)
                for bullet in entry.bullets:
                    draw_line(f"- {bullet}", "Helvetica", body_size, 4)
            y -= 6
    else:
        # A caller that supplied only a flat list of statements.
        draw_line("RELEVANT EXPERIENCE", "Helvetica-Bold", 12, 8)

        for statement in resume.statements:
            draw_line(f"- {statement}", "Helvetica", body_size, 5)

    pdf.save()
    return buffer.getvalue()
