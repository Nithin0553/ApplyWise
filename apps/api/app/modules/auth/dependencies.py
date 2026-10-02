"""F01: FastAPI dependencies other modules import to enforce RBAC.

``get_current_user`` and ``require_role`` are this module's public contract
for authorization. A feature module protects a route by depending on one
of these rather than reimplementing token handling, which keeps
"authorization is enforced server-side" (docs/ARCHITECTURE.md) true for
every module, not just auth's own routes.
"""

from __future__ import annotations

from collections.abc import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.models import User, UserRole
from app.modules.auth.security import InvalidTokenError, decode_access_token
from app.modules.auth.service import get_user_by_id

_bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _CREDENTIALS_ERROR
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise _CREDENTIALS_ERROR from exc

    user_id = payload.get("sub")
    if not user_id:
        raise _CREDENTIALS_ERROR

    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user


def require_role(*allowed_roles: UserRole) -> Iterable[UserRole]:
    """Return a FastAPI dependency restricting a route to the given roles.

    Usage: ``Depends(require_role(UserRole.ADMINISTRATOR))``. Ownership
    checks on a specific resource (e.g. "is this the job seeker's own
    evidence?") are a separate, per-module concern on top of this role
    check and are not this dependency's responsibility.
    """

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return _dependency
