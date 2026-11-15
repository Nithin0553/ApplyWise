from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DocumentFormat(StrEnum):
    PDF = "pdf"
    DOCX = "docx"


class ResumeTemplate(StrEnum):
    STANDARD = "standard"
    COMPACT = "compact"


class ResumeEntry(BaseModel):
    """One place of work, study, project or credential on the resume."""

    model_config = ConfigDict(frozen=True)

    organization: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    bullets: tuple[str, ...] = Field(min_length=1)


class ResumeSection(BaseModel):
    """A headed block of the resume, e.g. Professional Experience."""

    model_config = ConfigDict(frozen=True)

    heading: str = Field(min_length=1, max_length=120)
    entries: tuple[ResumeEntry, ...] = Field(min_length=1)


class ResumeDocument(BaseModel):
    """Validated content supplied to the F10 document renderer."""

    model_config = ConfigDict(frozen=True)

    full_name: str = Field(min_length=1, max_length=200)
    target_role: str = Field(min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    statements: tuple[str, ...] = Field(min_length=1)
    # Grouped form of the same statements, derived from the type of evidence
    # each one cites. Empty for callers that supply only a flat list, which
    # the renderer still handles.
    sections: tuple[ResumeSection, ...] = ()
    template: ResumeTemplate = ResumeTemplate.STANDARD
