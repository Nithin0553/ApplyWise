import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.modules.job_analysis.contracts import AnalysisRequest, AnalysisResult, Category, Importance
from app.modules.job_analysis.demo import create_demo_app
from app.modules.job_analysis.parser import UnparseableDescription
from app.modules.job_analysis.service import analyze_job_description

FIXTURES = Path(__file__).parent / "fixtures" / "job_analysis"


def parse(text):
    return analyze_job_description(AnalysisRequest(job_description=text))


@pytest.mark.parametrize("name", ["software_engineer", "data_analyst"])
def test_representative_postings_and_exact_source_context(name):
    text = (FIXTURES / f"{name}.txt").read_text()
    result = parse(text)
    assert {c for r in result.requirements for c in r.categories} == set(Category)
    assert all(text[r.source.start : r.source.end] == r.source.text for r in result.requirements)
    assert all(r.source.line == text[: r.source.start].count("\n") + 1 for r in result.requirements)
    assert not any(
        "salary" in r.text.lower() or "annual leave" in r.text for r in result.requirements
    )
    assert AnalysisResult.model_validate_json(result.model_dump_json()) == result


def test_required_preferred_optional_and_explicit_override():
    result = parse("Required skills:\nPython\nSQL preferred\nDocker optional\nJava not required")
    assert [r.importance for r in result.requirements] == [
        Importance.CRITICAL,
        Importance.PREFERRED,
        Importance.OPTIONAL,
        Importance.OPTIONAL,
    ]
    assert result.requirements[0].importance_basis == "section"
    assert result.requirements[1].importance_basis == "explicit"


def test_ambiguous_priorities_and_alternatives_are_not_invented():
    result = parse(
        "Qualifications:\nPython or Java\nSQL required but preferred\n"
        "Degree or equivalent experience"
    )
    assert all(r.needs_review for r in result.requirements)
    assert result.requirements[0].importance is None
    assert result.requirements[1].importance_basis == "conflicting"
    assert len(result.requirements) == 3
    assert "or" in result.requirements[0].text


@pytest.mark.parametrize(
    "expression,minimum,maximum,exact",
    [
        ("at least 3 years", 3, None, None),
        ("2–4 years", 2, 4, None),
        ("5+ years", 5, None, None),
        ("up to 2 years", None, 2, None),
        ("18 months", None, None, 1.5),
        ("1.5 years", None, None, 1.5),
    ],
)
def test_experience_amounts(expression, minimum, maximum, exact):
    experience = parse(f"Experience: {expression} of Python experience").requirements[0].experience
    assert experience.minimum_years == minimum
    assert experience.maximum_years == maximum
    assert experience.stated_years == exact


def test_multiple_experience_alternatives_are_flagged():
    req = parse("2 years with a degree or 5 years without a degree").requirements[0]
    assert req.experience is None
    assert req.needs_review
    assert any("experience amounts" in reason for reason in req.review_reasons)


@pytest.mark.parametrize(
    "bad", ["", " \n\t", "1234!!!", "bad\x00text", "<p>Python</p>", '{"job":"Python"}']
)
def test_malformed_text_has_clear_validation_errors(bad):
    with pytest.raises(ValidationError):
        AnalysisRequest(job_description=bad)


@pytest.mark.parametrize("bad", [None, 123, ["Python"], {"text": "Python"}])
def test_non_string_input_is_rejected(bad):
    with pytest.raises(ValidationError):
        AnalysisRequest(job_description=bad)


def test_oversized_text_is_rejected():
    with pytest.raises(ValidationError):
        AnalysisRequest(job_description="Python" * 9000)


def test_non_requirement_prose_fails_clearly():
    with pytest.raises(UnparseableDescription, match="No identifiable job requirements"):
        parse("Welcome to our wonderful company.")


def test_offsets_survive_crlf_unicode_bullets_and_inline_sections():
    text = "Required skills:\r\n  • Python; SQL\r\nPreferred skills: Node.js\r\n"
    result = parse(text)
    assert len(result.requirements) == 3
    for r in result.requirements:
        assert text[r.source.start : r.source.end] == r.source.text
    assert result.requirements[2].text == "Node.js"
    assert result.requirements[2].importance == Importance.PREFERRED


def test_unknown_heading_does_not_inherit_critical_priority():
    result = parse("Required skills:\nPython\nAdditional background:\nSQL experience")
    assert result.requirements[1].importance is None


def test_output_is_deterministic_and_ids_are_unique():
    text = "Required skills:\nPython\nPython\nSQL"
    a, b = parse(text), parse(text)
    assert a == b
    assert len({r.id for r in a.requirements}) == 3


def test_downstream_contract_import_does_not_load_parser():
    code = (
        "import sys; from app.modules.job_analysis.contracts import AnalysisResult; "
        "assert 'app.modules.job_analysis.parser' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_api_contract_and_validation():
    with TestClient(create_demo_app()) as client:
        response = client.post(
            "/api/f04/analyze", json={"job_description": "Required skills: Python"}
        )
        assert response.status_code == 200
        assert (
            AnalysisResult.model_validate(response.json()).requirements[0].importance == "Critical"
        )
        for data in (
            {},
            {"job_description": " "},
            {"job_description": 5},
            {"job_description": "Welcome to our company"},
        ):
            response = client.post("/api/f04/analyze", json=data)
            assert response.status_code == 422
            assert response.json()["detail"]
        response = client.post(
            "/api/f04/analyze", content="not JSON", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


def test_production_cannot_start_demo(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="development"):
        create_demo_app()


def test_schema_is_serializable_for_non_python_consumers():
    schema = AnalysisResult.model_json_schema()
    assert json.loads(json.dumps(schema))["properties"]["schema_version"]["const"] == "1.0"
