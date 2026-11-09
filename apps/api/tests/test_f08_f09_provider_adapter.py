"""F08/F09 dependency adapter: fail closed until F08 is installed and healthy."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.modules.evidence.service import EvidenceService
from app.modules.statement_review import dependencies
from app.modules.statement_review.contract import (
    UnavailableVerificationProvider,
    VerificationUnavailableError,
)


def test_adapter_uses_real_service_with_same_session(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Service:
        def __init__(self, session: Session, evidence: EvidenceService):
            self.session = session
            self.evidence = evidence

    monkeypatch.setattr(contract, "_verification_service_type", lambda: Service)
    provider = dependencies.current_verification_provider(db_session)
    assert isinstance(provider, Service)
    assert provider.session is db_session
    assert isinstance(provider.evidence, EvidenceService)
    assert provider.evidence.session is db_session


def test_missing_f08_module_fails_closed(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def absent() -> type:
        raise ModuleNotFoundError(
            "F08 is not yet available.", name="app.modules.verification.service"
        )

    monkeypatch.setattr(contract, "_verification_service_type", absent)
    provider = dependencies.current_verification_provider(db_session)
    assert isinstance(provider, UnavailableVerificationProvider)
    with pytest.raises(VerificationUnavailableError):
        provider.list_current(user_id=uuid4())


def test_broken_transitive_import_is_not_silently_hidden(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> type:
        raise ModuleNotFoundError(
            "Internal dependency broken", name="unrelated_runtime_package"
        )

    monkeypatch.setattr(contract, "_verification_service_type", broken)
    with pytest.raises(ModuleNotFoundError, match="Internal dependency broken"):
        dependencies.current_verification_provider(db_session)
