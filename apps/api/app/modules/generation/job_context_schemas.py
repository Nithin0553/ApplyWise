"""Request and response for reading a role title and employer from a posting.

Unlike F07's statements this output is not evidence-grounded and is not
verified: it pre-fills two fields the user can edit. It is kept in its own
module to make that difference obvious rather than letting it sit beside the
grounded-generation contracts.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# The paste box in the UI stops at 6000 characters; the same bound here keeps
# an arbitrarily long body from being forwarded to a paid provider.
MAX_DESCRIPTION_CHARS = 6000


class JobContextSuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=MAX_DESCRIPTION_CHARS)


class JobContextSuggestionView(BaseModel):
    """Any field may be empty: the posting may not state it, or the provider
    may not have managed to read it. The caller falls back rather than
    treating an empty answer as "this posting asks for nothing"."""

    role_title: str = ""
    company_name: str = ""
    requirements: list[str] = Field(default_factory=list, max_length=20)


Requirement = Annotated[str, StringConstraints(min_length=1, max_length=300, strip_whitespace=True)]


class RequirementMatchBody(BaseModel):
    """Requirements to assess, and the evidence ids to assess them against.

    Evidence arrives as ids, never as text: the records are read from F02 for
    the authenticated user, so a caller cannot have its own invented evidence
    assessed as though the user owned it.
    """

    model_config = ConfigDict(extra="forbid")

    requirements: list[Requirement] = Field(min_length=1, max_length=20)
    evidence_ids: list[UUID] = Field(min_length=1, max_length=20)


class RequirementAssessmentView(BaseModel):
    """Advisory gap analysis. Decides nothing about whether a claim is supported."""

    requirement: str
    coverage: Literal["COVERED", "PARTIAL", "MISSING"]
    evidence_ids: list[UUID] = Field(default_factory=list)
    note: str = ""


class RequirementMatchView(BaseModel):
    assessments: list[RequirementAssessmentView] = Field(default_factory=list)
