from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DocumentFormat(StrEnum):
    PDF = "pdf"
    DOCX = "docx"


class ResumeTemplate(StrEnum):
    STANDARD = "standard"
    COMPACT = "compact"


class ResumeDocument(BaseModel):
    """Validated content supplied to the F10 document renderer."""

    model_config = ConfigDict(frozen=True)

    full_name: str = Field(min_length=1, max_length=200)
    target_role: str = Field(min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    statements: tuple[str, ...] = Field(min_length=1)
    template: ResumeTemplate = ResumeTemplate.STANDARD
