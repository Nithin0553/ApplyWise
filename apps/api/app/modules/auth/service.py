"""F01: use-case logic for registration and login.

This is the module's public contract for the data it owns. Other feature
modules should call through here (or through ``dependencies.py``) rather
than querying the ``users`` table directly, per the dependency rule in
docs/ARCHITECTURE.md.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.auth.models import User, UserRole
from app.modules.auth.schemas import RegisterRequest
from app.modules.auth.security import hash_password, verify_password


class EmailAlreadyRegisteredError(Exception):
    """Raised when registration is attempted with an email already on file."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not match an active account."""


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = email.strip().lower()
    return db.query(User).filter(User.email == normalized_email).one_or_none()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.id == user_id).one_or_none()


def register_user(db: Session, payload: RegisterRequest) -> User:
    """Create a new Job Seeker account.

    Self-registration can only ever produce a JOB_SEEKER account:
    Administrator accounts are provisioned out of band, never through this
    endpoint, so no request body can grant elevated access.
    """
    normalized_email = payload.email.strip().lower()
    if get_user_by_email(db, normalized_email) is not None:
        raise EmailAlreadyRegisteredError(normalized_email)

    user = User(
        email=normalized_email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.JOB_SEEKER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        # Same error for "no such user" and "wrong password": the API must
        # not reveal which part of the credential pair was wrong.
        raise InvalidCredentialsError()
    return user
