"""F01: authentication, RBAC, and ownership enforcement."""

from app.modules.auth.router import router as auth_router

__all__ = ["auth_router"]
