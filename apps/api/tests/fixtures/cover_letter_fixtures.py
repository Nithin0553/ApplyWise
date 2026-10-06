"""Deterministic fixtures for F11 tests."""

from __future__ import annotations

from uuid import UUID

from app.modules.generation.cover_letter_schemas import (
    ApprovedStatement,
    CoverLetterRequest,
)
from app.modules.generation.schemas import JobContext
from app.services.ai.provider import (
    AIProviderError,
    CoverLetterResponse,
    RawParagraph,
)
from app.services.ai.provider import (
    CoverLetterRequest as ProviderCoverLetterRequest,
)

USER_ID = UUID("00000000-0000-0000-0000-0000000000aa")
EVIDENCE_ONE_ID = UUID("11111111-1111-1111-1111-111111111111")
EVIDENCE_TWO_ID = UUID("22222222-2222-2222-2222-222222222222")
STATEMENT_ONE_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
STATEMENT_TWO_ID = UUID("aaaaaaaa-0000-0000-0000-000000000002")
STATEMENT_THREE_ID = UUID("aaaaaaaa-0000-0000-0000-000000000003")

STATEMENT_ONE = ApprovedStatement(
    statement_id=STATEMENT_ONE_ID,
    text="Built and maintained automated regression suites for revenue management software",
    evidence_ids=(EVIDENCE_ONE_ID,),
    verification_status="VERIFIED",
)

STATEMENT_TWO = ApprovedStatement(
    statement_id=STATEMENT_TWO_ID,
    text="Wrote Python test automation for a backend service delivered by a six-person team",
    evidence_ids=(EVIDENCE_ONE_ID, EVIDENCE_TWO_ID),
    verification_status="VERIFIED",
)

STATEMENT_THREE = ApprovedStatement(
    statement_id=STATEMENT_THREE_ID,
    text="Owned release-candidate test cycles with engineers and product owners",
    evidence_ids=(EVIDENCE_TWO_ID,),
    verification_status="INFERRED",
)

JOB_CONTEXT = JobContext(
    job_title="Software Engineer in Test",
    company="Example Corp",
    description="Own automated testing for a Python backend.",
    requirements=("Python", "test automation"),
)


def build_request(max_paragraphs: int = 3, tone: str = "professional") -> CoverLetterRequest:
    return CoverLetterRequest(
        job_context=JOB_CONTEXT,
        approved_statements=(STATEMENT_ONE, STATEMENT_TWO, STATEMENT_THREE),
        tone=tone,  # type: ignore[arg-type]
        max_paragraphs=max_paragraphs,
    )


class FakeCoverLetterProvider:
    """Returns whatever the test says, and records what it was given."""

    name = "fake"

    def __init__(self, response: object) -> None:
        self._response = response
        self.last_request: ProviderCoverLetterRequest | None = None

    def generate_grounded(self, request: object) -> object:  # pragma: no cover - unused
        raise NotImplementedError

    def generate_cover_letter(self, request: ProviderCoverLetterRequest) -> object:
        self.last_request = request
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def paragraphs(*items: RawParagraph) -> CoverLetterResponse:
    return CoverLetterResponse(paragraphs=items)


def unavailable_provider() -> FakeCoverLetterProvider:
    return FakeCoverLetterProvider(AIProviderError("provider down"))
