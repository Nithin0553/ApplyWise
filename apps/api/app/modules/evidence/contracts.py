from __future__ import annotations

from typing import Protocol, Sequence
from uuid import UUID

from .schemas import ApprovedEvidence


class ApprovedEvidenceProvider(Protocol):
    """Stable F02 integration seam for matching, generation, and verification."""

    def list_approved(self, *, user_id: UUID) -> Sequence[ApprovedEvidence]:
        """Return only approved evidence owned by the requested user."""
        ...
