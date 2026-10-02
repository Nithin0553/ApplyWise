"""Stable F04 DTOs for F05/F06. This module does not import the parser."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(StrEnum):
    SKILL = "skill"
    EDUCATION = "education"
    EXPERIENCE = "experience"
    RESPONSIBILITY = "responsibility"
    QUALIFICATION = "qualification"


class Importance(StrEnum):
    CRITICAL = "Critical"
    PREFERRED = "Preferred"
    OPTIONAL = "Optional"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AnalysisRequest(Contract):
    job_description: str = Field(strict=True, min_length=1, max_length=50000)

    @field_validator("job_description")
    @classmethod
    def validate_plain_text(cls, value: str) -> str:
        # Do not strip or normalize: offsets refer to the original submitted string.
        if not value.strip():
            raise ValueError("Job description must contain non-whitespace text")
        if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
            raise ValueError("Job description contains unsupported control characters")
        if "<" in value and ">" in value:
            raise ValueError("Submit plain text, not HTML or markup")
        if value.lstrip().startswith(("{", "[")):
            raise ValueError("Submit job-description text, not a JSON document")
        if len([c for c in value if c.isalpha()]) < 5:
            raise ValueError("Job description must contain meaningful text")
        return value


class SourceContext(Contract):
    text: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    line: int = Field(ge=1)
    section: str | None = None


class ExperienceExpectation(Contract):
    minimum_years: float | None = None
    maximum_years: float | None = None
    stated_years: float | None = None
    expression: str


class Requirement(Contract):
    id: str
    text: str
    categories: list[Category] = Field(min_length=1)
    importance: Importance | None
    importance_basis: Literal["explicit", "section", "unspecified", "conflicting"]
    source: SourceContext
    experience: ExperienceExpectation | None = None
    needs_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)


class AnalysisResult(Contract):
    schema_version: Literal["1.0"] = "1.0"
    document_id: str
    requirements: list[Requirement] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
