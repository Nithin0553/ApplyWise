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


class AIProviderError(Exception):
    """Raised by a provider when it is unavailable or cannot answer."""


class AIProvider(Protocol):
    """Interface every AI provider implementation must satisfy."""

    name: str

    def generate_grounded(
        self, request: GroundedGenerationRequest
    ) -> GroundedGenerationResponse:
        ...
