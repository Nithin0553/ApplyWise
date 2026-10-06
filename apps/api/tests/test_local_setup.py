"""The Docker-free setup helper must refuse any database but SQLite.

``local_setup.py --seed`` creates a well-known account whose password is written
in this repository. If it ran against a shared PostgreSQL database -- which it
would, if ``DATABASE_URL`` happened to be exported in the shell -- it would plant
credentials that anyone who has read the file already knows.

These tests pin the refusal at the two functions that touch a database, not only
at the command line, so importing the module cannot route around the check.
"""

from __future__ import annotations

import pytest

from local_setup import UnsupportedDatabaseError, create_schema, require_sqlite, seed

SQLITE_URLS = [
    "sqlite://",
    "sqlite:///./local.db",
    "sqlite:///C:/Users/someone/Projects/ApplyWise/local.db",
    "sqlite+pysqlite:///./local.db",
]

NON_SQLITE_URLS = [
    "postgresql://applywise:applywise@localhost:5432/applywise",
    "postgresql+psycopg://applywise:applywise@db.example.edu:5432/applywise",
    "mysql+pymysql://user:pass@localhost/applywise",
    "mssql+pyodbc://user:pass@localhost/applywise",
]


@pytest.mark.parametrize("url", SQLITE_URLS)
def test_sqlite_urls_are_accepted(url: str) -> None:
    assert require_sqlite(url) == url


@pytest.mark.parametrize("url", NON_SQLITE_URLS)
def test_non_sqlite_urls_are_refused(url: str) -> None:
    with pytest.raises(UnsupportedDatabaseError):
        require_sqlite(url)


def test_the_refusal_names_the_backend_and_points_at_alembic() -> None:
    """The message has to be actionable: a bare refusal invites --force."""
    with pytest.raises(UnsupportedDatabaseError) as error:
        require_sqlite("postgresql+psycopg://applywise@localhost:5432/applywise")

    message = str(error.value)
    assert "postgresql" in message
    assert "alembic" in message.lower()


def test_an_unparseable_url_is_refused_rather_than_guessed() -> None:
    """Fails closed. An URL we cannot parse is not an URL we can vouch for."""
    with pytest.raises(UnsupportedDatabaseError):
        require_sqlite("not a database url")


def test_create_schema_refuses_postgres_before_connecting() -> None:
    """The guard runs first, so no engine is created and nothing is contacted.

    The host below does not exist. If this test ever starts failing with a
    connection error instead of UnsupportedDatabaseError, the guard has moved
    after create_engine and the protection is gone.
    """
    with pytest.raises(UnsupportedDatabaseError):
        create_schema("postgresql+psycopg://applywise@no-such-host.invalid:5432/applywise")


def test_seed_refuses_postgres_before_connecting() -> None:
    """Seeding is the dangerous half: it writes a published password."""
    with pytest.raises(UnsupportedDatabaseError):
        seed("postgresql+psycopg://applywise@no-such-host.invalid:5432/applywise")
