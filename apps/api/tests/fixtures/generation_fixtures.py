"""Deterministic fixtures for F07 tests.

Fixed UUIDs keep every test run identical, which is what "deterministic"
means in the F07 acceptance criteria.
"""

from __future__ import annotations

from uuid import UUID

from app.modules.generation.schemas import GenerationEvidence, GenerationRequest, JobContext
from app.services.ai.provider import (
    AIProviderError,
    GroundedGenerationRequest,
    GroundedGenerationResponse,
    RawStatement,
)

USER_ID = UUID("00000000-0000-0000-0000-0000000000aa")
EVIDENCE_ONE_ID = UUID("11111111-1111-1111-1111-111111111111")
EVIDENCE_TWO_ID = UUID("22222222-2222-2222-2222-222222222222")

EVIDENCE_ONE = GenerationEvidence(
    evidence_id=EVIDENCE_ONE_ID,
    evidence_type="WORK_EXPERIENCE",
    title="Associate QA Engineer",
    organization="Model N",
    role="Associate QA Engineer",
    description="Built automated regression suites for revenue management software.",
)

EVIDENCE_TWO = GenerationEvidence(
    evidence_id=EVIDENCE_TWO_ID,
    evidence_type="SKILL",
    title="Python",
    description="Used for test automation and backend services.",
)

JOB_CONTEXT = JobContext(
    job_title="Software Engineer in Test",
    company="Example Corp",
    description="Own automated testing for a Python backend.",
    requirements=("Python", "test automation"),
)


def build_request(max_statements: int = 5) -> GenerationRequest:
    return GenerationRequest(
        job_context=JOB_CONTEXT,
        approved_evidence=(EVIDENCE_ONE, EVIDENCE_TWO),
        max_statements=max_statements,
    )


class FakeAIProvider:
    """Returns whatever the test tells it to, and records what it received."""

    name = "fake"

    def __init__(self, response: object) -> None:
        self._response = response
        self.last_request: GroundedGenerationRequest | None = None

    def generate_grounded(self, request: GroundedGenerationRequest) -> object:
        self.last_request = request
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def response_with(*statements: RawStatement) -> GroundedGenerationResponse:
    return GroundedGenerationResponse(statements=statements)


def unavailable_provider() -> FakeAIProvider:
    return FakeAIProvider(AIProviderError("provider down"))
