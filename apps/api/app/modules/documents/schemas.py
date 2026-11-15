from __future__ import annotations

from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentFormat(StrEnum):
    PDF = "pdf"
    DOCX = "docx"


class ResumeTemplate(StrEnum):
    STANDARD = "standard"
    COMPACT = "compact"


class ResumeEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_ids: tuple[UUID, ...] = Field(min_length=1)
    statement_ids: tuple[UUID, ...] = ()
    title: str = ""
    organization: str | None = None
    role: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    statements: tuple[str, ...] = ()


class ResumeSection(BaseModel):
    model_config = ConfigDict(frozen=True)

    heading: str
    entries: tuple[ResumeEntry, ...] = Field(min_length=1)


class ResumeDocument(BaseModel):
    """Validated content supplied to the F10 document renderer."""

    model_config = ConfigDict(frozen=True)

    full_name: str = Field(min_length=1, max_length=200)
    target_role: str = Field(min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    sections: tuple[ResumeSection, ...] = Field(min_length=1)
    template: ResumeTemplate = ResumeTemplate.STANDARD

    @property
    def statements(self) -> tuple[str, ...]:
        """Flatten text for consumers that only need approved statements."""
        return tuple(text for section in self.sections for entry in section.entries
                     for text in entry.statements)
