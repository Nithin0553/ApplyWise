"""The F07 trust boundary: where approved evidence comes from.

A caller chooses *which* of its own approved evidence to draw on, by id. It
never supplies the evidence itself. The records are read from F02 for the
authenticated user, so content and approval state cannot be fabricated or
altered in transit, and the "only approved evidence" guarantee is enforced
rather than merely contractual.

``ApprovedEvidenceProvider`` mirrors the Protocol F02 publishes in
``app.modules.evidence.contracts``. It is restated here, structurally, so this
module and its tests carry no dependency on the evidence package or on a
database: the resolution rule can be tested with a fake store in microseconds,
and the route supplies the real ``EvidenceService``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from .adapters import GroundingContext, from_grounding_contexts
from .errors import GenerationError
from .schemas import GenerationEvidence


class EvidenceNotApprovedError(GenerationError):
    """A requested id is not approved evidence owned by this user.

    Deliberately one error for every reason — the record does not exist, it
    belongs to someone else, it was never approved — so a caller cannot use
    the response to learn which. F02's own evidence service refuses missing
    and foreign-owned records identically, for the same reason.
    """


class ApprovedEvidenceProvider(Protocol):
    """F02's integration seam, as F07 consumes it.

    The implementation is expected to return only evidence that is persisted,
    owned by ``user_id``, and APPROVED. F07 does not query the evidence tables
    and cannot itself confirm approval state.
    """

    def list_grounding_contexts(self, *, user_id: UUID) -> Sequence[GroundingContext]:
        """Return approved structured evidence owned by the requested user."""
        ...


def resolve_approved_evidence(
    provider: ApprovedEvidenceProvider,
    *,
    user_id: UUID,
    evidence_ids: Sequence[UUID],
) -> tuple[GenerationEvidence, ...]:
    """Turn caller-supplied ids into evidence the user actually owns.

    Any id that does not resolve to one of this user's approved records raises,
    rather than being quietly dropped. Generating from fewer items than the
    user selected would silently change what the statements rest on, which is
    precisely the kind of unnoticed substitution F07 exists to prevent.

    Returns the records in the order the caller listed them, so the E1/E2
    references in a result follow the user's own ordering.
    """
    if not evidence_ids:
        raise EvidenceNotApprovedError("No evidence was selected.")

    owned = {
        context.evidence_id: context
        for context in provider.list_grounding_contexts(user_id=user_id)
    }

    selected: list[GroundingContext] = []
    seen: set[UUID] = set()
    for evidence_id in evidence_ids:
        if evidence_id in seen:
            raise EvidenceNotApprovedError("Duplicate evidence selected.")
        seen.add(evidence_id)

        context = owned.get(evidence_id)
        if context is None:
            raise EvidenceNotApprovedError(
                "One or more selected items are not approved evidence you own."
            )
        selected.append(context)

    return tuple(from_grounding_contexts(selected))
