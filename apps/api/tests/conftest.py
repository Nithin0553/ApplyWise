"""Shared test fixtures.

Tests run against an in-memory SQLite database instead of the real
PostgreSQL instance, and against the scripted AI provider rather than a real
one, so `pytest` has no external dependency. SQLite is
compatible with the column types used so far (String, Boolean, DateTime);
a feature introducing a Postgres-only type should extend this fixture
rather than assume Postgres is always available in CI.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Import every module's models so Base.metadata is complete, mirroring
# migrations/env.py.
from app.modules.auth import models as auth_models  # noqa: F401


@pytest.fixture(autouse=True)
def offline_ai_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may call a real AI provider.

    Routes that do not take a provider override read ``AI_PROVIDER`` from the
    environment, so a developer who has set it to a real provider in their
    .env would otherwise have the suite make live API calls: slow,
    non-deterministic, billed, and green or red depending on whose machine it
    ran on. This pins every test to the scripted provider and removes the key,
    so leaving the machine is not possible rather than merely discouraged.

    A test that wants to exercise a real provider's parsing constructs it
    directly with a stubbed httpx transport, as test_anthropic_provider.py
    does.
    """
    monkeypatch.setattr(settings, "ai_provider", "stub")
    monkeypatch.setattr(settings, "ai_api_key", None)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
