"""F10 resume rendering: ATS-friendly PDF and DOCX output."""

from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.shared import Inches, Pt
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from .schemas import DocumentFormat, ResumeDocument, ResumeTemplate


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

    for kind, text in _content_lines(resume):
        if kind == "section":
            document.add_heading(text, level=1)
        elif kind == "entry":
            document.add_paragraph().add_run(text).bold = True
        elif kind == "bullet":
            document.add_paragraph(text, style="List Bullet")
        else:
            document.add_paragraph(text)

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

    for kind, text in _content_lines(resume):
        if kind == "section":
            y -= 8
            draw_line(text, "Helvetica-Bold", 12, 8)
        elif kind == "entry":
            draw_line(text, "Helvetica-Bold", body_size, 3)
        else:
            prefix = "- " if kind == "bullet" else ""
            draw_line(prefix + text, "Helvetica", body_size, 5)

    pdf.save()
    return buffer.getvalue()


def _content_lines(resume: ResumeDocument) -> list[tuple[str, str]]:
    """Both formats consume the same ordered section content."""
    lines: list[tuple[str, str]] = []
    for section in resume.sections:
        lines.append(("section", section.heading))
        for entry in section.entries:
            # Keep title and role when distinct (e.g. degree versus assistantship).
            heading = " | ".join(dict.fromkeys(
                value for value in (entry.title, entry.role, entry.organization) if value
            ))
            if heading:
                lines.append(("entry", heading))
            if entry.start_date or entry.end_date:
                # A missing end date is unknown, not proof of current employment.
                dates = " - ".join(
                    value.isoformat() for value in (entry.start_date, entry.end_date) if value
                )
                if not entry.start_date:
                    dates = "Ended " + dates
                elif not entry.end_date:
                    dates = "Started " + dates
                lines.append(("dates", dates))
            lines.extend(("bullet", text) for text in entry.statements)
    return lines
