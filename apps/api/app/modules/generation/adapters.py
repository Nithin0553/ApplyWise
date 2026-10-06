"""Adapter from F02's grounding seam to F07's input type.

F02 exposes ``ApprovedEvidenceProvider.list_grounding_contexts(user_id=...)``,
returning ``EvidenceGroundingContext`` objects. F07 converts those into
``GenerationEvidence`` here, in one place, so the structured approved fields
survive into the prompt instead of collapsing to title and description.

The adapter reads the context **structurally** (a Protocol) rather than
importing the evidence module, which keeps the F07 module free of a build-time
dependency on F02 and matches the team rule that modules integrate through
documented contracts. Any object carrying these attributes is accepted, which
is also what makes the adapter testable without a database.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from .schemas import GenerationEvidence


class GroundingContext(Protocol):
    """The shape F07 reads from F02's ``EvidenceGroundingContext``."""

    evidence_id: UUID
    evidence_type: object  # str or StrEnum on the F02 side
    title: str
    organization: str | None
    role: str | None
    location: str | None
    description: str | None
    skill_name: str | None
    proficiency: str | None
    credential: str | None
    start_date: date | None
    end_date: date | None


def from_grounding_context(context: GroundingContext) -> GenerationEvidence:
    """Convert one approved F02 grounding context into F07 input."""
    evidence_type = getattr(context.evidence_type, "value", context.evidence_type)
    return GenerationEvidence(
        evidence_id=context.evidence_id,
        evidence_type=str(evidence_type),
        title=context.title,
        organization=context.organization,
        role=context.role,
        location=context.location,
        description=context.description,
        skill_name=context.skill_name,
        proficiency=context.proficiency,
        credential=context.credential,
        start_date=context.start_date,
        end_date=context.end_date,
    )


def from_grounding_contexts(
    contexts: Iterable[GroundingContext],
) -> Sequence[GenerationEvidence]:
    """Convert a whole ``list_grounding_contexts(...)`` result."""
    return tuple(from_grounding_context(context) for context in contexts)
