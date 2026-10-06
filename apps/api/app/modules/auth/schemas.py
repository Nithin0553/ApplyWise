"""F01: request/response contracts for the auth module."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.modules.auth.models import UserRole

_PASSWORD_MIN_LENGTH = 8
_PASSWORD_HAS_LETTER = re.compile(r"[A-Za-z]")
_PASSWORD_HAS_DIGIT = re.compile(r"\d")


def _validate_password_strength(value: str) -> str:
    if len(value) < _PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {_PASSWORD_MIN_LENGTH} characters long.")
    if not _PASSWORD_HAS_LETTER.search(value):
        raise ValueError("Password must contain at least one letter.")
    if not _PASSWORD_HAS_DIGIT.search(value):
        raise ValueError("Password must contain at least one digit.")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_is_strong(cls, value: str) -> str:
        return _validate_password_strength(value)

    @field_validator("full_name")
    @classmethod
    def full_name_is_present(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Full name is required.")
        return stripped


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
