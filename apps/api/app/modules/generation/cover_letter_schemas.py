"""F11 public contract: cover letter generation from approved statements.

See docs/contracts/F11_COVER_LETTER_CONTRACT.md.

The grounding chain for F11 is one step further along than for F07: a cover
letter is written from statements that already passed verification (F08) and
user approval (F09), not from raw evidence. Those statements still carry their
own evidence provenance, which F11 preserves paragraph by paragraph.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schemas import JobContext

MAX_PARAGRAPH_LENGTH = 800


class ApprovedStatement(BaseModel):
    """One statement that F08 verified and the user approved in F09.

    The ``Literal`` types are the point: an UNSUPPORTED or unapproved statement
    cannot be represented by this model at all, so it cannot enter a cover
    letter even by mistake.
    """

    model_config = ConfigDict(frozen=True)

    statement_id: UUID
    text: str = Field(min_length=1, max_length=500)
    evidence_ids: tuple[UUID, ...] = Field(min_length=1)
    verification_status: Literal["VERIFIED", "INFERRED"]
    approval_status: Literal["APPROVED"] = "APPROVED"


class CoverLetterRequest(BaseModel):
    """What a caller may ask for.

    Note what is absent, exactly as in ``GenerationRequest``: the user's
    identity. It comes from the authenticated session (F01) and is passed to
    ``CoverLetterService.generate`` by the route, so a caller cannot draft
    against another user's account by editing a payload. There is no field to
    edit.
    """

    model_config = ConfigDict(frozen=True)

    job_context: JobContext
    approved_statements: tuple[ApprovedStatement, ...] = Field(min_length=1)
    tone: Literal["professional", "warm", "direct"] = "professional"
    max_paragraphs: int = Field(default=3, ge=2, le=5)

    @model_validator(mode="after")
    def statement_ids_are_unique(self) -> Self:
        ids = [item.statement_id for item in self.approved_statements]
        if len(ids) != len(set(ids)):
            raise ValueError("approved_statements contains duplicate statement_id values")
        return self


class CoverLetterParagraph(BaseModel):
    """A drafted paragraph. Like F07 output, it is a candidate and no more.

    A cover letter paragraph is new prose, so it goes back through verification
    and approval before it can be exported, exactly as ADR-003 requires.
    """

    model_config = ConfigDict(frozen=True)

    paragraph_id: UUID
    text: str = Field(min_length=1, max_length=MAX_PARAGRAPH_LENGTH)
    statement_ids: tuple[UUID, ...] = Field(min_length=1)
    evidence_ids: tuple[UUID, ...] = Field(min_length=1)
    status: Literal["CANDIDATE"] = "CANDIDATE"
    verification_status: Literal["PENDING"] = "PENDING"
    approval_status: Literal["UNREVIEWED"] = "UNREVIEWED"
    export_eligible: Literal[False] = False


class RejectedParagraph(BaseModel):
    """Provider output that failed F11's safety checks and was discarded."""

    model_config = ConfigDict(frozen=True)

    text: str
    reason: str


class CoverLetterPdfRequest(BaseModel):
    """Paragraphs to lay out as a letter.

    The author's name is NOT a field: it comes from the authenticated session,
    like every other identity in this module. The paragraphs are the caller's
    draft, and rendering them asserts nothing about them -- see
    ``cover_letter_pdf``.
    """

    model_config = ConfigDict(frozen=True)

    company: str | None = Field(default=None, max_length=200)
    paragraphs: tuple[str, ...] = Field(min_length=1, max_length=12)


class CoverLetterDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    draft_id: UUID
    user_id: UUID
    provider: str
    generated_at: datetime
    tone: str
    paragraphs: tuple[CoverLetterParagraph, ...]
    rejected: tuple[RejectedParagraph, ...] = ()



class CoverLetterSelectionRequest(BaseModel):
    """Public F11 request: the caller selects F08 IDs, never approval labels.

    The server resolves these through current F09 decisions and F02 evidence.
    The separate CoverLetterRequest carries resolved statements to the
    internal generation service only, not through the public HTTP boundary.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_context: JobContext
    statement_ids: tuple[UUID, ...] = Field(min_length=1, max_length=10)
    tone: Literal["professional", "warm", "direct"] = "professional"
    max_paragraphs: int = Field(default=3, ge=2, le=5)

    @model_validator(mode="after")
    def ids_are_unique(self) -> Self:
        if len(set(self.statement_ids)) != len(self.statement_ids):
            raise ValueError("statement_ids contains duplicate values")
        return self
