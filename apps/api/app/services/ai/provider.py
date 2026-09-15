from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GroundedGenerationRequest:
    job_context: str
    approved_evidence: list[str]
    instructions: str


@dataclass(frozen=True)
class GroundedGenerationResponse:
    text: str
    cited_evidence_indexes: list[int]


class AIProvider(Protocol):
    def generate_grounded(
        self, request: GroundedGenerationRequest
    ) -> GroundedGenerationResponse:
        ...
