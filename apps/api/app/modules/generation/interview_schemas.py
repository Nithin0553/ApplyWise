"""F15 public contract: interview defensibility preparation.

See docs/contracts/F15_INTERVIEW_DEFENSIBILITY_CONTRACT.md for the full
description.

The central distinction in this module is between *defensibility* and
*verification*. F08 decides whether a claim is VERIFIED, INFERRED or
UNSUPPORTED against the user's evidence, and that decision gates export.
F15 decides something narrower and softer: how hard a claim would be to
explain out loud in an interview, given the evidence behind it. A
HARD_TO_DEFEND result is advice to the user, never a verification outcome,
and nothing here is allowed to look like one — which is why every result
carries ``advisory_only: Literal[True]`` and no approval or export field
exists on these models at all.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .cover_letter_schemas import ApprovedStatement

MAX_QUESTION_LENGTH = 300
MAX_SUPPORTING_POINT_LENGTH = 300
MAX_SIGNAL_DETAIL_LENGTH = 120
MAX_QUESTIONS_PER_STATEMENT = 6
MAX_STATEMENTS_PER_REQUEST = 20
MAX_CITED_EVIDENCE_PER_REQUEST = 50


class DefensibilityRisk(StrEnum):
    """How hard a statement would be to justify if an interviewer probed it.

    This is an ordered scale, worst last, so a caller can sort by it.
    """

    SUPPORTED = "SUPPORTED"
    NEEDS_DETAIL = "NEEDS_DETAIL"
    HARD_TO_DEFEND = "HARD_TO_DEFEND"


class SignalCode(StrEnum):
    """Why a statement was flagged. One code per detectable pattern."""

    UNSOURCED_NUMBER = "UNSOURCED_NUMBER"
    UNSOURCED_SUPERLATIVE = "UNSOURCED_SUPERLATIVE"
    UNSOURCED_LEADERSHIP = "UNSOURCED_LEADERSHIP"
    THIN_EVIDENCE = "THIN_EVIDENCE"
    INFERRED_STATEMENT = "INFERRED_STATEMENT"
    SINGLE_SOURCE = "SINGLE_SOURCE"


class QuestionKind(StrEnum):
    """What an interview question is trying to get at."""

    EVIDENCE_PROBE = "EVIDENCE_PROBE"
    SPECIFICS = "SPECIFICS"
    OWNERSHIP = "OWNERSHIP"
    METRIC_SOURCE = "METRIC_SOURCE"


class RiskSignal(BaseModel):
    """One concrete reason a statement may be hard to defend.

    ``detail`` quotes the part of the statement that triggered the signal, so
    the user can see exactly what an interviewer would seize on. It is bounded
    because it is derived from statement text.
    """

    model_config = ConfigDict(frozen=True)

    code: SignalCode
    detail: str = Field(min_length=1, max_length=MAX_SIGNAL_DETAIL_LENGTH)


class InterviewQuestion(BaseModel):
    """A question the user should be ready to answer about one statement."""

    model_config = ConfigDict(frozen=True)

    question_id: UUID
    statement_id: UUID
    kind: QuestionKind
    text: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)


class StatementPreparation(BaseModel):
    """Everything F15 has to say about one approved statement.

    ``supporting_points`` are drawn from the user's own cited evidence and are
    never new prose: they restate facts the evidence already contains, so that
    rehearsing an answer cannot drift into inventing one.
    """

    model_config = ConfigDict(frozen=True)

    statement_id: UUID
    statement_text: str = Field(min_length=1)
    evidence_ids: tuple[UUID, ...] = Field(min_length=1)
    risk: DefensibilityRisk
    signals: tuple[RiskSignal, ...] = ()
    questions: tuple[InterviewQuestion, ...] = Field(min_length=1)
    supporting_points: tuple[str, ...] = ()

    @model_validator(mode="after")
    def questions_belong_to_this_statement(self) -> Self:
        if any(item.statement_id != self.statement_id for item in self.questions):
            raise ValueError("questions must reference their own statement_id")
        if len(self.questions) > MAX_QUESTIONS_PER_STATEMENT:
            raise ValueError("too many questions for one statement")
        return self


class InterviewPrepRequest(BaseModel):
    """What a caller may ask for.

    The user's identity is absent, exactly as in ``GenerationPreviewRequest``
    and ``CoverLetterRequest``: it comes from the authenticated session and is
    passed to the service by the route.

    ``approved_statements`` is supplied by the caller only because F09 has no
    store to resolve ids against yet. The *evidence* each statement cites is
    not caller-supplied: the route reads those records from F02 for the
    authenticated user, so the material a claim is checked against is
    authoritative even while the statements are not. When F09 lands, this
    field becomes ``statement_ids`` resolved through
    ``cover_letter_contracts.select_approved_statements`` and the gate on the
    route comes off. Until then the route is not served in production.
    """

    model_config = ConfigDict(frozen=True)

    approved_statements: tuple[ApprovedStatement, ...] = Field(
        min_length=1, max_length=MAX_STATEMENTS_PER_REQUEST
    )

    @model_validator(mode="after")
    def statement_ids_are_unique(self) -> Self:
        ids = [item.statement_id for item in self.approved_statements]
        if len(ids) != len(set(ids)):
            raise ValueError("approved_statements contains duplicate statement_id values")
        return self

    @model_validator(mode="after")
    def cited_evidence_is_bounded(self) -> Self:
        """Bound the evidence read, not just the statement count.

        Each statement may cite many evidence items, so a request well inside
        the statement limit could still ask the route to resolve an unbounded
        number of records from F02.
        """
        distinct = {
            evidence_id
            for statement in self.approved_statements
            for evidence_id in statement.evidence_ids
        }
        if len(distinct) > MAX_CITED_EVIDENCE_PER_REQUEST:
            raise ValueError(
                "approved_statements cite more than "
                f"{MAX_CITED_EVIDENCE_PER_REQUEST} distinct evidence items"
            )
        return self


class InterviewPrep(BaseModel):
    """F15's output: preparation advice, and nothing with authority.

    ``advisory_only`` is a ``Literal[True]`` so that a response carrying a
    defensibility result can never be mistaken for, or coerced into, an F08
    verification or an F09 approval. There is deliberately no approval,
    verification or export field on this model.
    """

    model_config = ConfigDict(frozen=True)

    prep_id: UUID
    user_id: UUID
    generated_at: datetime
    items: tuple[StatementPreparation, ...] = Field(min_length=1)
    advisory_only: Literal[True] = True

    @property
    def hard_to_defend_count(self) -> int:
        return sum(
            1 for item in self.items if item.risk is DefensibilityRisk.HARD_TO_DEFEND
        )
