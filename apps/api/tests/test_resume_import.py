"""F03 resume import and F02 evidence delete (Req-Func-Sw-9, Req-Func-Sw-13 to 17)."""

import io
import zipfile
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.auth.models import User, UserRole
from app.modules.auth.security import hash_password
from app.modules.evidence.resume_import import (
    MAX_DOCX_MEMBERS,
    MAX_UNCOMPRESSED_DOCX_BYTES,
    MAX_UPLOAD_BYTES,
    UnreadableResumeError,
    UnsupportedResumeFormatError,
    extract_text,
    propose_evidence,
    read_resume,
)
from tests.resume_files import SAMPLE_LINES, build_docx, build_pdf, set_declared_member_count

# build_docx always writes [Content_Types].xml and word/document.xml.
BASE_DOCX_MEMBERS = 2

PASSWORD = "correct-horse-1"


def _register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Synthetic User"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _upload(client: TestClient, headers: dict[str, str], name: str, data: bytes):
    return client.post("/api/evidence/import", headers=headers, files={"file": (name, data)})


# ------------------------------------------------------------------ parsing


def test_docx_text_round_trip_keeps_resume_lines() -> None:
    text = extract_text("resume.docx", build_docx(SAMPLE_LINES))
    assert "Coastal Analytics" in text
    assert "Python, SQL, TypeScript" in text


def test_pdf_text_round_trip_keeps_resume_lines() -> None:
    text = extract_text("resume.pdf", build_pdf(SAMPLE_LINES))
    assert "Coastal Analytics" in text
    assert "AWS Cloud Practitioner" in text


@pytest.mark.parametrize("builder,name", [(build_docx, "r.docx"), (build_pdf, "r.pdf")])
def test_proposed_records_cover_each_resume_section(builder, name) -> None:
    proposed = read_resume(name, builder(SAMPLE_LINES)).proposed
    by_type = {}
    for item in proposed:
        by_type.setdefault(item.evidence_type.value, []).append(item)

    job = by_type["work_experience"][0]
    assert job.title == "Software Engineer Intern"
    assert job.organization == "Coastal Analytics"
    assert job.location == "Corpus Christi, TX"
    assert job.start_date == date(2025, 6, 1)
    assert job.end_date == date(2025, 8, 1)
    assert job.description == (
        "Built a Python dashboard that reports weekly sales data.\n"
        "Wrote unit tests for the reporting API."
    )

    degree = by_type["education"][0]
    assert degree.title == "B.S. Computer Science"
    assert degree.organization == "Texas A&M University-Corpus Christi"

    assert {i.skill_name for i in by_type["skill"]} == {"Python", "SQL", "TypeScript"}
    assert by_type["project"][0].title == "Campus Events App"
    assert by_type["certification"][0].title == "AWS Cloud Practitioner"
    assert all(item.source == "resume_import" for item in proposed)


def test_import_only_copies_text_from_the_file() -> None:
    proposed = propose_evidence("Experience\nBarista - Cafe Uno | 2020 - Present\n- Made coffee.")
    assert len(proposed) == 1
    job = proposed[0]
    assert job.end_date is None  # "Present" is not turned into a made-up date
    assert job.description == "Made coffee."


# Lines whose dates cannot be valid. The entry is still imported, with no dates, so the
# owner can correct it before approval (Req-Func-Sw-16).
IMPOSSIBLE_DATE_LINES = [
    "Barista - Cafe Uno | 0000 - 2020",
    "Barista - Cafe Uno | 2020 - 0000",
    "Barista - Cafe Uno | Jan 0000 - Feb 2020",
    "Barista - Cafe Uno | 01/0000 - 02/2020",
    "Barista - Cafe Uno | 13/2020 - 2021",
    "Barista - Cafe Uno | 2022 - 2020",
]


@pytest.mark.parametrize("line", IMPOSSIBLE_DATE_LINES)
def test_impossible_dates_are_left_empty_and_the_entry_is_kept(line: str) -> None:
    proposed = propose_evidence(f"Experience\n{line}\n- Made coffee.")

    assert len(proposed) == 1
    job = proposed[0]
    assert (job.title, job.organization) == ("Barista", "Cafe Uno")
    assert job.description == "Made coffee."
    # Both dates are dropped: keeping only one would make "2020 - 0000" look like a current job.
    assert job.start_date is None
    assert job.end_date is None


def test_day_numbers_never_produce_an_impossible_date() -> None:
    proposed = propose_evidence("Experience\nBarista - Cafe Uno | February 31 2020 - 2021")

    assert len(proposed) == 1
    assert proposed[0].title == "Barista"


def _lines_with_impossible_years() -> list[str]:
    return [
        "Experience",
        "Barista - Cafe Uno | 0000 - 2020",
        "- Made coffee.",
        "Cashier - Corner Shop | 2020 - 0000",
        "- Ran the till.",
        "Software Engineer Intern - Coastal Analytics | Jun 2025 - Aug 2025",
        "Education",
        "B.S. Computer Science, Texas A&M University-Corpus Christi, 0000 - 2020",
    ]


@pytest.mark.parametrize("builder,name", [(build_docx, "r.docx"), (build_pdf, "r.pdf")])
def test_resume_with_impossible_years_imports_without_error(builder, name) -> None:
    proposed = read_resume(name, builder(_lines_with_impossible_years())).proposed
    by_title = {item.title: item for item in proposed}

    for title in ("Barista", "Cashier", "B.S. Computer Science"):
        assert by_title[title].start_date is None
        assert by_title[title].end_date is None
    # Valid dates elsewhere in the same resume are kept.
    assert by_title["Software Engineer Intern"].start_date == date(2025, 6, 1)
    assert by_title["Software Engineer Intern"].end_date == date(2025, 8, 1)


def test_text_without_resume_sections_is_rejected() -> None:
    with pytest.raises(UnreadableResumeError):
        propose_evidence("Dear hiring manager, this is just a letter with no sections.")


def test_unsupported_extension_is_rejected() -> None:
    with pytest.raises(UnsupportedResumeFormatError):
        extract_text("photo.png", b"\x89PNG\r\n")
    with pytest.raises(UnsupportedResumeFormatError):
        extract_text("old.doc", b"\xd0\xcf\x11\xe0")


@pytest.mark.parametrize(
    "name,data",
    [
        ("broken.pdf", b"this is plain text, not a pdf"),
        ("truncated.pdf", b"%PDF-1.4\n1 0 obj\n<<"),
        ("broken.docx", b"not a zip file"),
        ("empty.docx", build_docx([])),
        ("blank.pdf", build_pdf([])),
    ],
)
def test_corrupted_or_empty_files_are_unreadable(name: str, data: bytes) -> None:
    with pytest.raises(UnreadableResumeError):
        extract_text(name, data)


def test_docx_without_document_xml_is_unreadable() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("other.txt", "hello")
    with pytest.raises(UnreadableResumeError):
        extract_text("resume.docx", buffer.getvalue())


def test_docx_at_the_member_limit_is_read() -> None:
    data = build_docx(SAMPLE_LINES, extra_members=MAX_DOCX_MEMBERS - BASE_DOCX_MEMBERS)
    assert "Software Engineer Intern" in extract_text("resume.docx", data)


def test_docx_with_too_many_members_is_unreadable() -> None:
    data = build_docx(SAMPLE_LINES, extra_members=MAX_DOCX_MEMBERS - BASE_DOCX_MEMBERS + 1)
    with pytest.raises(UnreadableResumeError):
        extract_text("resume.docx", data)


def test_docx_that_understates_its_member_count_is_still_refused() -> None:
    data = build_docx(SAMPLE_LINES, extra_members=MAX_DOCX_MEMBERS)
    with pytest.raises(UnreadableResumeError):
        extract_text("resume.docx", set_declared_member_count(data, BASE_DOCX_MEMBERS))


def test_docx_with_oversized_document_xml_is_unreadable() -> None:
    # Highly repetitive text: small once compressed, over the limit once decompressed.
    filler = "Python " * (MAX_UNCOMPRESSED_DOCX_BYTES // 7 + 1)
    data = build_docx([*SAMPLE_LINES, filler])
    assert len(data) <= MAX_UPLOAD_BYTES
    with pytest.raises(UnreadableResumeError):
        extract_text("resume.docx", data)


# ------------------------------------------------------------------ API


def test_import_creates_unconfirmed_records_owned_by_the_user(client: TestClient) -> None:
    headers = _register(client, "alex@example.com")

    response = _upload(client, headers, "resume.docx", build_docx(SAMPLE_LINES))

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "resume.docx"
    assert len(body["records"]) >= 6
    assert {r["status"] for r in body["records"]} == {"unconfirmed"}
    assert all(r["approved_at"] is None for r in body["records"])

    listed = client.get("/api/evidence/", headers=headers).json()
    assert len(listed) == len(body["records"])
    # Imported evidence cannot be used for generation until the user approves it.
    assert client.get("/api/evidence/approved", headers=headers).json() == []


def test_import_route_accepts_a_resume_with_impossible_years(client: TestClient) -> None:
    headers = _register(client, "alex@example.com")

    response = _upload(client, headers, "resume.docx", build_docx(_lines_with_impossible_years()))

    assert response.status_code == 201
    records = {r["title"]: r for r in response.json()["records"]}
    for title in ("Barista", "Cashier", "B.S. Computer Science"):
        assert records[title]["status"] == "unconfirmed"
        assert records[title]["start_date"] is None
        assert records[title]["end_date"] is None


def test_imported_record_can_be_corrected_then_approved(client: TestClient) -> None:
    headers = _register(client, "alex@example.com")
    records = _upload(client, headers, "resume.pdf", build_pdf(SAMPLE_LINES)).json()["records"]
    job = next(r for r in records if r["evidence_type"] == "work_experience")

    fixed = client.patch(
        f"/api/evidence/{job['id']}", headers=headers, json={"title": "Software Engineering Intern"}
    )
    assert fixed.status_code == 200
    assert fixed.json()["status"] == "unconfirmed"

    approved = client.post(f"/api/evidence/{job['id']}/approve", headers=headers)
    assert approved.status_code == 200
    only_approved = client.get("/api/evidence/approved", headers=headers).json()
    assert [r["id"] for r in only_approved] == [job["id"]]


def test_imported_records_are_private_to_the_uploader(client: TestClient) -> None:
    alex = _register(client, "alex@example.com")
    sam = _register(client, "sam@example.com")
    _upload(client, alex, "resume.docx", build_docx(SAMPLE_LINES))

    assert client.get("/api/evidence/", headers=sam).json() == []


def test_unsupported_file_is_rejected_with_clear_message(client: TestClient) -> None:
    headers = _register(client, "alex@example.com")

    response = _upload(client, headers, "photo.png", b"\x89PNG\r\n\x1a\n")

    assert response.status_code == 415
    assert response.json()["detail"] == "Only PDF (.pdf) and Word (.docx) resumes can be imported."
    assert client.get("/api/evidence/", headers=headers).json() == []


def test_corrupted_file_is_rejected_and_nothing_is_saved(client: TestClient) -> None:
    headers = _register(client, "alex@example.com")

    response = _upload(client, headers, "broken.pdf", b"plain text renamed to pdf")

    assert response.status_code == 422
    assert "could not be processed" in response.json()["detail"]
    assert client.get("/api/evidence/", headers=headers).json() == []


def test_docx_with_too_many_members_is_rejected_and_nothing_is_saved(client: TestClient) -> None:
    headers = _register(client, "alex@example.com")
    data = build_docx(SAMPLE_LINES, extra_members=MAX_DOCX_MEMBERS)

    response = _upload(client, headers, "resume.docx", data)

    assert response.status_code == 422
    assert response.json()["detail"].startswith("This file could not be processed.")
    assert client.get("/api/evidence/", headers=headers).json() == []


@pytest.mark.parametrize("builder,name", [(build_docx, "resume.docx"), (build_pdf, "resume.pdf")])
def test_normal_resumes_still_import_after_the_archive_limits(
    client: TestClient, builder, name: str
) -> None:
    headers = _register(client, "alex@example.com")

    response = _upload(client, headers, name, builder(SAMPLE_LINES))

    assert response.status_code == 201
    assert len(response.json()["records"]) >= 6
    assert {r["status"] for r in response.json()["records"]} == {"unconfirmed"}


def test_file_without_resume_content_is_rejected(client: TestClient) -> None:
    headers = _register(client, "alex@example.com")

    response = _upload(client, headers, "letter.docx", build_docx(["Dear hiring manager,"]))

    assert response.status_code == 422
    assert "No career details" in response.json()["detail"]
    assert client.get("/api/evidence/", headers=headers).json() == []


def test_oversized_file_is_rejected(client: TestClient) -> None:
    headers = _register(client, "alex@example.com")

    response = _upload(client, headers, "big.pdf", b"%PDF-" + b"0" * MAX_UPLOAD_BYTES)

    assert response.status_code == 413
    assert "5 MB" in response.json()["detail"]


def test_import_requires_sign_in_and_job_seeker_role(
    client: TestClient, db_session: Session
) -> None:
    data = build_docx(SAMPLE_LINES)
    assert client.post("/api/evidence/import", files={"file": ("r.docx", data)}).status_code == 401

    reviewer = User(
        email="reviewer@example.com",
        hashed_password=hash_password(PASSWORD),
        full_name="Synthetic Reviewer",
        role=UserRole.REVIEWER,
        is_active=True,
    )
    db_session.add(reviewer)
    db_session.commit()
    token = client.post(
        "/auth/login", json={"email": reviewer.email, "password": PASSWORD}
    ).json()["access_token"]
    response = _upload(client, {"Authorization": f"Bearer {token}"}, "r.docx", data)
    assert response.status_code == 403


# ------------------------------------------------------------------ delete (Req-Func-Sw-9)


def _create(client: TestClient, headers: dict[str, str], title: str) -> dict:
    response = client.post(
        "/api/evidence/",
        headers=headers,
        json={"evidence_type": "skill", "title": title, "skill_name": title},
    )
    assert response.status_code == 201
    return response.json()


def test_owner_can_delete_evidence(client: TestClient) -> None:
    headers = _register(client, "alex@example.com")
    record = _create(client, headers, "Python")

    assert client.delete(f"/api/evidence/{record['id']}", headers=headers).status_code == 204

    assert client.get(f"/api/evidence/{record['id']}", headers=headers).status_code == 404
    assert client.get("/api/evidence/", headers=headers).json() == []


def test_deleted_approved_evidence_leaves_the_approved_list(client: TestClient) -> None:
    headers = _register(client, "alex@example.com")
    record = _create(client, headers, "Python")
    client.post(f"/api/evidence/{record['id']}/approve", headers=headers)

    client.delete(f"/api/evidence/{record['id']}", headers=headers)

    assert client.get("/api/evidence/approved", headers=headers).json() == []


def test_cannot_delete_another_users_evidence(client: TestClient) -> None:
    alex = _register(client, "alex@example.com")
    sam = _register(client, "sam@example.com")
    record = _create(client, alex, "Python")

    response = client.delete(f"/api/evidence/{record['id']}", headers=sam)

    assert response.status_code == 404
    assert response.json()["detail"] == "Evidence not found"
    assert client.get(f"/api/evidence/{record['id']}", headers=alex).status_code == 200


def test_delete_requires_authentication(client: TestClient) -> None:
    headers = _register(client, "alex@example.com")
    record = _create(client, headers, "Python")

    assert client.delete(f"/api/evidence/{record['id']}").status_code == 401
