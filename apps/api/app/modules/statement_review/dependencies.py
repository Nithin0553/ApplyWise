"""Request-scoped F08 → F09 adapter (kept separate from the public protocol)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.evidence.service import EvidenceService

from .contract import CurrentVerificationProvider, UnavailableVerificationProvider


def _verification_service_type() -> type:
    """Import F08 only once it is installed; leave the public contract acyclic."""
    from app.modules.verification.service import VerificationService

    return VerificationService


def current_verification_provider(
    db: Session = Depends(get_db),
) -> CurrentVerificationProvider:
    """Resolve current F08 results with the same request session and F02 evidence.

    If F08 is not yet installed, dependent routes fail closed with 503.
    Do not suppress an unrelated broken import inside F08.
    """
    try:
        verifier_type = _verification_service_type()
    except ModuleNotFoundError as exc:
        if exc.name not in (
            "app.modules.verification",
            "app.modules.verification.service",
        ):
            raise
        return UnavailableVerificationProvider()
    return verifier_type(db, EvidenceService(db))
