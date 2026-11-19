"""Render a drafted cover letter as a PDF.

This is a formatting convenience, not a trusted export. F10 renders a resume
only after F13 revalidates every approval and its evidence; nothing of the
kind happens here, because a cover-letter paragraph is a CANDIDATE that has
not been through F08 or F09 and cannot become export-eligible by being
printed. The paragraphs come from the caller, so this module asserts nothing
about them beyond laying them out, and the page says so in its footer.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

_MARGIN = 64
_BODY_SIZE = 11
_LINE_HEIGHT = 16


def render_cover_letter_pdf(
    *,
    full_name: str,
    email: str,
    company: str | None,
    paragraphs: tuple[str, ...],
    drafted_on: date | None = None,
) -> bytes:
    """Lay the drafted paragraphs out as a letter."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter
    available = page_width - (2 * _MARGIN)
    y = page_height - _MARGIN

    def draw(text: str, font: str, size: int, spacing: int) -> None:
        nonlocal y
        pdf.setFont(font, size)
        for line in simpleSplit(text, font, size, available):
            if y < _MARGIN + _LINE_HEIGHT:
                pdf.showPage()
                y = page_height - _MARGIN
                pdf.setFont(font, size)
            pdf.drawString(_MARGIN, y, line)
            y -= _LINE_HEIGHT
        y -= spacing

    draw(full_name, "Helvetica-Bold", 16, 2)
    draw(email, "Helvetica", 10, 16)

    draw((drafted_on or date.today()).strftime("%B %d, %Y"), "Helvetica", 10, 2)
    if company:
        draw(company, "Helvetica", 10, 14)

    draw("Dear Hiring Manager,", "Helvetica", _BODY_SIZE, 10)

    for paragraph in paragraphs:
        draw(paragraph, "Helvetica", _BODY_SIZE, 10)

    draw("Sincerely,", "Helvetica", _BODY_SIZE, 2)
    draw(full_name, "Helvetica", _BODY_SIZE, 0)

    # Say on the page what the page is, so a draft cannot be mistaken for the
    # resume, which is the only document this product stands behind.
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(_MARGIN, _MARGIN - 18, "Draft cover letter. Not a verified export.")

    pdf.save()
    return buffer.getvalue()
