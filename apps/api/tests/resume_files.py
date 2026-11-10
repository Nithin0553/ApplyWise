"""Builders for small synthetic PDF and Word resumes used by the F03 import tests."""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

SAMPLE_LINES = [
    "Alex Morgan",
    "alex.morgan@example.com",
    "Experience",
    "Software Engineer Intern - Coastal Analytics, Corpus Christi, TX | Jun 2025 - Aug 2025",
    "- Built a Python dashboard that reports weekly sales data.",
    "- Wrote unit tests for the reporting API.",
    "Education",
    "B.S. Computer Science, Texas A&M University-Corpus Christi, 2021 - 2025",
    "Skills",
    "Languages: Python, SQL, TypeScript",
    "Projects",
    "Campus Events App | Jan 2024 - May 2024",
    "- Built a React app for student event sign-ups.",
    "Certifications",
    "AWS Cloud Practitioner, Amazon Web Services, 2024",
]


def build_pdf(lines: list[str]) -> bytes:
    def esc(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    shown = "\n".join(f"({esc(line)}) Tj T*" for line in lines)
    stream = f"BT /F1 11 Tf 50 760 Td 14 TL\n{shown}\nET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return bytes(out)


def build_docx(lines: list[str], *, extra_members: int = 0) -> bytes:
    """Return a minimal .docx; ``extra_members`` adds that many empty archive members."""
    paragraphs = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{escape(line)}</w:t></w:r></w:p>' for line in lines
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{paragraphs}</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document)
        for index in range(extra_members):
            archive.writestr(f"word/media/extra{index}.bin", b"")
    return buffer.getvalue()


def set_declared_member_count(data: bytes, count: int) -> bytes:
    """Overwrite the member counts in a zip's end record, leaving the members unchanged."""
    position = data.rfind(b"PK\x05\x06")
    field = count.to_bytes(2, "little")
    return data[: position + 8] + field + field + data[position + 12 :]
