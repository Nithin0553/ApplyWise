from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped database session.

    Shared infrastructure: any feature module may depend on this, but
    per the dependency rule in docs/ARCHITECTURE.md, modules must still
    not query another module's tables directly.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
