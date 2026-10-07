"""Set up a local ApplyWise database without Docker, and optionally seed it.

Why this exists
---------------
The normal local setup runs PostgreSQL in Docker and applies Alembic
migrations. That is the right thing for development and for CI. But Docker is
not always available — a locked-down machine, a laptop that will not start the
engine, a demo five minutes before it is due — and the application itself does
not need PostgreSQL to run locally.

This script creates the schema directly from the SQLAlchemy models, which is
the same thing the test suite does, so it works on SQLite. Alembic cannot
migrate SQLite (F02's evidence migration alters a constraint, which SQLite does
not support), so migrations are deliberately bypassed here rather than fought.

This is a convenience for local runs and demos. It is **not** a substitute for
migrations: anything deployed, and CI, must still go through Alembic, because
only migrations record how an existing database moves from one version to the
next.

The script refuses to run against anything but SQLite. ``--seed`` writes a
well-known account with a published password, so pointing this at a shared
PostgreSQL database -- by having ``DATABASE_URL`` already exported in the shell,
for instance -- would plant credentials anyone who has read this file knows. The
check is in ``create_schema`` and ``seed`` themselves rather than only in
``main``, so importing the module cannot route around it.

Usage
-----
From apps/api, with the virtual environment active::

    set DATABASE_URL=sqlite:///C:/Users/<you>/Projects/ApplyWise/local.db
    python local_setup.py              # create the schema
    python local_setup.py --seed       # create it and add demo evidence

Then start the API as usual::

    python -m uvicorn app.main:app --reload

The seeded account is demo@example.edu / demopass123, with four approved
evidence items, so the Tailor screen has something to work with immediately.
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import sessionmaker

# Importing every module's models makes Base.metadata complete. This mirrors
# migrations/env.py and tests/conftest.py; a new module with tables must be
# added here too, or its tables will silently not be created.
from app.db.base import Base
from app.modules.applications import models as _applications  # noqa: F401
from app.modules.auth import models as _auth  # noqa: F401
from app.modules.evidence import models as _evidence  # noqa: F401
from app.modules.sharing import models as _sharing  # noqa: F401

DEMO_EMAIL = "demo@example.edu"
DEMO_PASSWORD = "demopass123"

DEMO_EVIDENCE = [
    {
        "evidence_type": "work_experience",
        "title": "Associate QA Engineer",
        "organization": "Model N",
        "role": "Associate QA Engineer",
        "location": "Hyderabad, India",
        "description": (
            "Built automated regression suites for revenue management software "
            "and owned release-candidate test cycles"
        ),
    },
    {
        "evidence_type": "skill",
        "title": "Python",
        "skill_name": "Python",
        "proficiency": "Advanced",
    },
    {
        "evidence_type": "certification",
        "title": "ISTQB Foundation Level",
        "organization": "ISTQB",
        "credential": "CTFL-2023-44810",
    },
    {
        "evidence_type": "project",
        "title": "ApplyWise capstone backend",
        "organization": "Texas A&M University-Corpus Christi",
        "description": (
            "Designed a grounded generation module with provenance validation "
            "and a full regression suite"
        ),
    },
]


class UnsupportedDatabaseError(RuntimeError):
    """Raised when DATABASE_URL points at anything but SQLite."""


def require_sqlite(url: str) -> str:
    """Return ``url`` if it is a SQLite URL, otherwise refuse to go further.

    Fails closed: an unparseable URL is rejected too, rather than being passed
    to SQLAlchemy to interpret. The backend name is taken from the parsed URL,
    so ``sqlite+pysqlite://`` is accepted and ``postgresql+psycopg://`` is not.
    """
    try:
        backend = make_url(url).get_backend_name()
    except ArgumentError as exc:
        raise UnsupportedDatabaseError(
            f"DATABASE_URL is not a valid SQLAlchemy URL: {url!r}"
        ) from exc

    if backend != "sqlite":
        raise UnsupportedDatabaseError(
            f"local_setup.py only runs against SQLite, but DATABASE_URL names the "
            f"{backend!r} backend.\n"
            "This script creates the schema from the models and can seed a demo "
            "account with a published password, so it must never touch a shared "
            "database.\n"
            "For PostgreSQL, run the Alembic migrations instead:\n"
            "  python -m alembic upgrade head"
        )
    return url


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit(
            "DATABASE_URL is not set.\n"
            "Example (Windows):\n"
            "  set DATABASE_URL=sqlite:///C:/Users/you/Projects/ApplyWise/local.db\n"
            "Example (macOS/Linux):\n"
            "  export DATABASE_URL=sqlite:///./local.db"
        )
    return url


def create_schema(url: str) -> None:
    require_sqlite(url)
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    print(f"Schema ready in {url}")
    for table in sorted(Base.metadata.tables):
        print(f"  - {table}")


def seed(url: str) -> None:
    """Add a demo job seeker with approved evidence.

    Evidence is created through the F02 service rather than by inserting rows,
    so the records go through the same validation and approval transition the
    application uses. Seeded data that bypassed those rules would not prove the
    app works.
    """
    require_sqlite(url)

    from app.modules.auth.schemas import RegisterRequest
    from app.modules.auth.service import get_user_by_email, register_user
    from app.modules.evidence.schemas import EvidenceCreate
    from app.modules.evidence.service import EvidenceService

    engine = create_engine(url)
    session = sessionmaker(bind=engine)()

    try:
        existing_user = get_user_by_email(session, DEMO_EMAIL)
        if existing_user is None:
            user = register_user(
                session,
                RegisterRequest(
                    email=DEMO_EMAIL, password=DEMO_PASSWORD, full_name="Demo Job Seeker"
                ),
            )
            session.commit()
            user_id = user.id
            print(f"Created {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            user_id = existing_user.id
            print(f"{DEMO_EMAIL} already exists; adding evidence to it.")

        evidence = EvidenceService(session)
        existing = {item.title for item in evidence.list_owned(user_id=user_id)}
        added = 0
        for payload in DEMO_EVIDENCE:
            if payload["title"] in existing:
                continue
            record = evidence.create(user_id=user_id, data=EvidenceCreate(**payload))
            evidence.approve(user_id=user_id, evidence_id=record.id)
            added += 1
        session.commit()
        print(f"Approved evidence added: {added}")
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed",
        action="store_true",
        help="also create a demo account with four approved evidence items",
    )
    args = parser.parse_args()

    url = database_url()
    try:
        create_schema(url)
        if args.seed:
            seed(url)
    except UnsupportedDatabaseError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
