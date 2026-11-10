"""F03: turn an uploaded PDF or Word resume into proposed, unconfirmed evidence.

The importer is deliberately conservative and rule-based. It only copies text that is in
the uploaded file into evidence records; it never writes new claims. Every record it
creates starts as ``UNCONFIRMED`` (F02 rule), so nothing from an import can reach
generation until the owner reviews, corrects, and approves it.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date
from xml.etree import ElementTree

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from .models import EvidenceType
from .schemas import EvidenceCreate

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_UNCOMPRESSED_DOCX_BYTES = 20 * 1024 * 1024
# A Word resume has a few dozen archive members, or a few hundred with many images.
MAX_DOCX_MEMBERS = 1000
MAX_PROPOSED_RECORDS = 100
IMPORT_SOURCE = "resume_import"

UNSUPPORTED_MESSAGE = "Only PDF (.pdf) and Word (.docx) resumes can be imported."
TOO_LARGE_MESSAGE = "This file is larger than 5 MB. Upload a smaller PDF or Word resume."
UNREADABLE_MESSAGE = (
    "This file could not be processed. Check that it is a text-based PDF or Word resume "
    "that is not password protected, and try again, or add your evidence manually."
)
NO_CONTENT_MESSAGE = (
    "No career details could be found in this file. Check that it is a text-based resume, "
    "or add your evidence manually."
)


class ResumeImportError(ValueError):
    """Base class; ``message`` is safe to show to the job seeker."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UnsupportedResumeFormatError(ResumeImportError):
    pass


class ResumeTooLargeError(ResumeImportError):
    pass


class UnreadableResumeError(ResumeImportError):
    pass


# --------------------------------------------------------------------------- extraction


def extract_text(filename: str, data: bytes) -> str:
    """Return the plain text of a PDF or .docx upload, or raise ResumeImportError."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ResumeTooLargeError(TOO_LARGE_MESSAGE)
    lowered = (filename or "").lower()
    if lowered.endswith(".pdf"):
        if data.lstrip()[:5] != b"%PDF-":
            raise UnreadableResumeError(UNREADABLE_MESSAGE)
        return _pdf_text(data)
    if lowered.endswith(".docx"):
        if data[:2] != b"PK":
            raise UnreadableResumeError(UNREADABLE_MESSAGE)
        return _docx_text(data)
    raise UnsupportedResumeFormatError(UNSUPPORTED_MESSAGE)


def _pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise UnreadableResumeError(UNREADABLE_MESSAGE)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except ResumeImportError:
        raise
    except (PyPdfError, ValueError, KeyError, OSError, RecursionError) as exc:
        raise UnreadableResumeError(UNREADABLE_MESSAGE) from exc
    if not text.strip():
        raise UnreadableResumeError(UNREADABLE_MESSAGE)
    return text


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# ZIP end-of-central-directory record: fixed 22 bytes, then a comment of up to 64 KB.
_EOCD_SIGNATURE = b"PK\x05\x06"
_EOCD_SIZE = 22
_EOCD_MAX_COMMENT = 0xFFFF


def _declared_member_count(data: bytes) -> int | None:
    """Return the member count stated in the archive's end record, or None if there is none.

    Opening a ZipFile reads an entry for every member, so an upload packed with tens of
    thousands of tiny members costs real time even though its size is within the limit.
    Reading the count first lets such a file be refused before that work starts.
    """
    start = max(0, len(data) - _EOCD_SIZE - _EOCD_MAX_COMMENT)
    position = data.rfind(_EOCD_SIGNATURE, start)
    if position < 0 or position + _EOCD_SIZE > len(data):
        return None
    # Total entries in the central directory. ZIP64 archives store 0xFFFF here, which is
    # also over the limit, so they are refused too; no Word resume needs ZIP64.
    return int.from_bytes(data[position + 10 : position + 12], "little")


def _docx_text(data: bytes) -> str:
    declared = _declared_member_count(data)
    if declared is not None and declared > MAX_DOCX_MEMBERS:
        raise UnreadableResumeError(UNREADABLE_MESSAGE)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            # The end record can understate the count, so check the parsed list as well.
            if len(archive.infolist()) > MAX_DOCX_MEMBERS:
                raise UnreadableResumeError(UNREADABLE_MESSAGE)
            # Only word/document.xml is ever decompressed, and its declared size is checked
            # before reading; zipfile stops at that declared size when it decompresses.
            info = archive.getinfo("word/document.xml")
            if info.file_size > MAX_UNCOMPRESSED_DOCX_BYTES:
                raise UnreadableResumeError(UNREADABLE_MESSAGE)
            xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml)
    except ResumeImportError:
        raise
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError, OSError) as exc:
        raise UnreadableResumeError(UNREADABLE_MESSAGE) from exc

    paragraphs: list[str] = []
    for paragraph in root.iter(f"{_W}p"):
        parts: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{_W}t" and node.text:
                parts.append(node.text)
            elif node.tag in (f"{_W}tab", f"{_W}br"):
                parts.append(" ")
        paragraphs.append("".join(parts))
    text = "\n".join(paragraphs)
    if not text.strip():
        raise UnreadableResumeError(UNREADABLE_MESSAGE)
    return text


# --------------------------------------------------------------------------- parsing

_SECTION_HEADINGS: dict[str, tuple[str, ...]] = {
    "experience": (
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "work history",
    ),
    "education": ("education", "academic background"),
    "skills": ("skills", "technical skills", "core skills", "key skills"),
    "projects": ("projects", "selected projects", "academic projects"),
    "certifications": ("certifications", "certificates", "licenses and certifications"),
}
_HEADING_LOOKUP = {name: key for key, names in _SECTION_HEADINGS.items() for name in names}
_OTHER_HEADINGS = {
    "summary",
    "professional summary",
    "objective",
    "profile",
    "awards",
    "publications",
    "references",
    "interests",
    "volunteer experience",
    "activities",
    "languages",
}

_MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ],
        start=1,
    )
    for m in names
}
_DATE = r"(?:(?:[A-Za-z]{3,9}\.?\s+)?\d{4}|\d{1,2}/\d{4})"
_RANGE = re.compile(rf"(?P<start>{_DATE})\s*(?:-|–|—|to)\s*(?P<end>{_DATE}|present|current)", re.I)
_SINGLE_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_BULLET = re.compile(r"^\s*(?:[•●▪◦*\-–·]|•)\s*")
_SEPARATORS = re.compile(r"\s+(?:—|–|\||@)\s+|\s+-\s+|\s+at\s+|,\s+", re.I)


def _norm_heading(line: str) -> str:
    return re.sub(r"[^a-z ]", "", line.lower()).strip()


def _parse_date(token: str, *, end: bool) -> date | None:
    """Parse one side of a date range.

    Returns None for "Present"/"Current" or an unrecognized month word. Raises ValueError
    when the text names a date that cannot exist, such as year 0000 or month 13.
    """
    token = token.strip().rstrip(".")
    if token.lower() in {"present", "current"}:
        return None
    if "/" in token:
        month, year = token.split("/")
        return date(int(year), int(month), 1)
    parts = token.replace(".", "").split()
    if len(parts) == 2:
        month_n = _MONTHS.get(parts[0].lower())
        if month_n:
            return date(int(parts[1]), month_n, 1)
        return None
    year_n = int(parts[0])
    # A bare year only says the year; use the year's boundary so the user can refine it.
    return date(year_n, 12, 31) if end else date(year_n, 1, 1)


def _split_dates(line: str) -> tuple[str, date | None, date | None]:
    """Split a date range off a line.

    Dates are kept only when the whole range is valid. If either side is impossible, or the
    range ends before it starts, both dates are left empty: keeping just one would invent
    meaning (an empty end date reads as "Present"). The entry is still imported, unconfirmed,
    so the owner can enter the right dates before approving it.
    """
    match = _RANGE.search(line)
    if not match:
        return line, None, None
    rest = (line[: match.start()] + " " + line[match.end() :]).strip(" |,-–—()")
    try:
        start = _parse_date(match.group("start"), end=False)
        end = _parse_date(match.group("end"), end=True)
    except ValueError:
        return rest, None, None
    if start and end and end < start:
        return rest, None, None
    return rest, start, end


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        heading = _norm_heading(line)
        if len(line) <= 40 and heading in _HEADING_LOOKUP:
            current = _HEADING_LOOKUP[heading]
            sections.setdefault(current, [])
            continue
        if len(line) <= 40 and heading in _OTHER_HEADINGS:
            current = None
            continue
        if current:
            sections[current].append(line)
    return sections


def _entries(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Group lines into (header line, bullet lines); a non-bullet line starts an entry."""
    entries: list[tuple[str, list[str]]] = []
    for line in lines:
        if _BULLET.match(line):
            bullet = _BULLET.sub("", line).strip()
            if entries and bullet:
                entries[-1][1].append(bullet)
        elif entries and not entries[-1][1] and not _has_date(line) and _has_date(entries[-1][0]):
            # A second header line (for example a location or date line) joins the header.
            entries[-1] = (f"{entries[-1][0]} | {line}", entries[-1][1])
        else:
            entries.append((line, []))
    return entries


def _has_date(line: str) -> bool:
    return bool(_RANGE.search(line))


def _clip(value: str | None, limit: int) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value[:limit] if value else None


def _parts(header: str) -> list[str]:
    return [part.strip() for part in _SEPARATORS.split(header) if part.strip()]


def _experience(lines: list[str], kind: EvidenceType) -> list[EvidenceCreate]:
    records: list[EvidenceCreate] = []
    for header, bullets in _entries(lines):
        rest, start, end = _split_dates(header)
        parts = _parts(rest)
        if not parts:
            continue
        title = parts[0]
        organization = parts[1] if len(parts) > 1 else None
        location = ", ".join(parts[2:]) if len(parts) > 2 else None
        records.append(
            EvidenceCreate(
                evidence_type=kind,
                title=title[:200],
                organization=_clip(organization, 200),
                location=_clip(location, 200),
                description=_clip("\n".join(bullets), 5000) if bullets else None,
                start_date=start,
                end_date=end,
                source=IMPORT_SOURCE,
            )
        )
    return records


def _education(lines: list[str]) -> list[EvidenceCreate]:
    records: list[EvidenceCreate] = []
    for header, bullets in _entries(lines):
        rest, start, end = _split_dates(header)
        if not (start or end):
            year = _SINGLE_YEAR.search(rest)
            if year:
                end = date(int(year.group()), 12, 31)
                rest = rest.replace(year.group(), "").strip(" |,-–—()")
        parts = _parts(rest)
        if not parts:
            continue
        records.append(
            EvidenceCreate(
                evidence_type=EvidenceType.EDUCATION,
                title=parts[0][:200],
                organization=_clip(parts[1] if len(parts) > 1 else None, 200),
                location=_clip(", ".join(parts[2:]) if len(parts) > 2 else None, 200),
                description=_clip("\n".join(bullets), 5000) if bullets else None,
                start_date=start,
                end_date=end,
                source=IMPORT_SOURCE,
            )
        )
    return records


def _skills(lines: list[str]) -> list[EvidenceCreate]:
    names: list[str] = []
    for line in lines:
        line = _BULLET.sub("", line)
        if ":" in line:
            line = line.split(":", 1)[1]
        for token in re.split(r"[,;|•·]", line):
            token = token.strip()
            if 0 < len(token) <= 100 and token.lower() not in {n.lower() for n in names}:
                names.append(token)
    return [
        EvidenceCreate(
            evidence_type=EvidenceType.SKILL,
            title=name,
            skill_name=name,
            source=IMPORT_SOURCE,
        )
        for name in names
    ]


def _certifications(lines: list[str]) -> list[EvidenceCreate]:
    records: list[EvidenceCreate] = []
    for line in lines:
        line = _BULLET.sub("", line)
        rest, start, end = _split_dates(line)
        if not (start or end):
            year = _SINGLE_YEAR.search(rest)
            if year:
                start = date(int(year.group()), 1, 1)
                rest = rest.replace(year.group(), "").strip(" |,-–—()")
        parts = _parts(rest)
        if not parts:
            continue
        records.append(
            EvidenceCreate(
                evidence_type=EvidenceType.CERTIFICATION,
                title=parts[0][:200],
                credential=_clip(parts[0], 200),
                organization=_clip(parts[1] if len(parts) > 1 else None, 200),
                start_date=start,
                source=IMPORT_SOURCE,
            )
        )
    return records


def propose_evidence(text: str) -> list[EvidenceCreate]:
    """Return proposed evidence parsed from resume text (not yet saved)."""
    sections = _sections(text)
    proposed: list[EvidenceCreate] = []
    proposed += _experience(sections.get("experience", []), EvidenceType.WORK_EXPERIENCE)
    proposed += _education(sections.get("education", []))
    proposed += _experience(sections.get("projects", []), EvidenceType.PROJECT)
    proposed += _certifications(sections.get("certifications", []))
    proposed += _skills(sections.get("skills", []))
    if not proposed:
        raise UnreadableResumeError(NO_CONTENT_MESSAGE)
    return proposed[:MAX_PROPOSED_RECORDS]


@dataclass(frozen=True)
class ImportOutcome:
    filename: str
    proposed: list[EvidenceCreate]


def read_resume(filename: str, data: bytes) -> ImportOutcome:
    """Extract and parse an upload; raises ResumeImportError when it cannot be processed."""
    return ImportOutcome(filename=filename, proposed=propose_evidence(extract_text(filename, data)))
