"""The declarative base every ORM model inherits from.

Kept in its own module so model packages can import it without importing each
other, which is what lets Alembic see all tables from one metadata object.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
