"""Provider-neutral AI interface for grounded generation (F07).

Everything provider-specific (OpenAI, Anthropic, a local model, ...) must live
behind the ``AIProvider`` protocol in this package. Feature modules such as
``app.modules.generation`` only ever talk to this interface.

Design note: the provider never sees database UUIDs. The generation service
gives each evidence item a short reference such as ``"E1"`` and maps the
provider's citations back to real evidence IDs afterwards. Short references
are easier for language models to repeat correctly, and any reference the
provider invents can be detected and rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PromptEvidence:
    """One approved evidence item, as shown to the provider."""

    ref: str  # short reference, e.g. "E1"
    text: str  # human-readable evidence content


@dataclass(frozen=True)
class GroundedGenerationRequest:
    """Everything a provider is allowed to use. Nothing else."""

    job_context: str
    evidence: tuple[PromptEvidence, ...]
    instructions: str
    max_statements: int


@dataclass(frozen=True)
class RawStatement:
    """One statement exactly as the provider returned it (untrusted)."""

    text: str
    cited_refs: tuple[str, ...]


@dataclass(frozen=True)
class GroundedGenerationResponse:
    """Untrusted provider output. The generation service validates it."""

    statements: tuple[RawStatement, ...]


@dataclass(frozen=True)
class PromptStatement:
    """One approved statement, as shown to the provider (F11)."""

    ref: str  # short reference, e.g. "S1"
    text: str


@dataclass(frozen=True)
class CoverLetterRequest:
    """Everything a provider may use when drafting a cover letter."""

    job_context: str
    statements: tuple[PromptStatement, ...]
    instructions: str
    tone: str
    max_paragraphs: int


@dataclass(frozen=True)
class RawParagraph:
    """One paragraph exactly as the provider returned it (untrusted)."""

    text: str
    cited_refs: tuple[str, ...]


@dataclass(frozen=True)
class CoverLetterResponse:
    """Untrusted provider output. The cover letter service validates it."""

    paragraphs: tuple[RawParagraph, ...]


@dataclass(frozen=True)
class JobContextRequest:
    """A pasted job description, as the user supplied it."""

    description: str


@dataclass(frozen=True)
class JobContextSuggestion:
    """Role title and employer read out of a description. Both may be empty.

    A suggestion only pre-fills two editable fields. It never reaches evidence,
    verification or approval, so a wrong answer costs the user a correction and
    nothing more -- which is why an empty string is an acceptable answer and a
    guess is not required.
    """

    role_title: str
    company_name: str
    # What the posting actually asks for. Empty when the provider could not
    # read them, which the caller treats as "use the old heuristic".
    requirements: tuple[str, ...] = ()


@dataclass(frozen=True)
class RequirementMatchRequest:
    """Requirements to assess, against the evidence the user has approved."""

    requirements: tuple[str, ...]
    evidence: tuple[PromptEvidence, ...]


@dataclass(frozen=True)
class RequirementAssessment:
    """How well one requirement is answered by the cited evidence.

    Advisory only. This says what the user can currently speak to and where
    the gaps are; it decides nothing about whether a written claim is
    supported, which remains F08's job and stays deterministic.
    """

    requirement: str
    coverage: str  # COVERED | PARTIAL | MISSING
    cited_refs: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class RequirementMatchResponse:
    assessments: tuple[RequirementAssessment, ...]


class AIProviderError(Exception):
    """Raised by a provider when it is unavailable or cannot answer."""


class AIProvider(Protocol):
    """Interface every AI provider implementation must satisfy."""

    name: str

    def generate_grounded(
        self, request: GroundedGenerationRequest
    ) -> GroundedGenerationResponse:
        ...

    def generate_cover_letter(self, request: CoverLetterRequest) -> CoverLetterResponse:
        ...

    def suggest_job_context(self, request: JobContextRequest) -> JobContextSuggestion:
        ...

    def assess_requirements(
        self, request: RequirementMatchRequest
    ) -> RequirementMatchResponse:
        ...
