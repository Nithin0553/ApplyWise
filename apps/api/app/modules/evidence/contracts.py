from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from .schemas import ApprovedEvidence, EvidenceGroundingContext


class ApprovedEvidenceProvider(Protocol):
    """Stable F02 integration seam for matching, generation, and verification."""

    def list_approved(self, *, user_id: UUID) -> Sequence[ApprovedEvidence]:
        """Return only approved evidence owned by the requested user."""
        ...

    def list_grounding_contexts(
        self, *, user_id: UUID
    ) -> Sequence[EvidenceGroundingContext]:
        """Return approved structured evidence ready for F05/F07/F08 adapters."""
        ...
