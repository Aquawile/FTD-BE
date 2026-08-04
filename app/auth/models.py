from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    email: str
    permissions: set[str] = set()


class User(BaseModel):
    """Application-level identity representation for a PostgreSQL user record.

    This is a domain/schema model, not an ORM model. The repository uses raw SQL
    rather than an ORM, so this Pydantic model serves as the canonical typed
    representation of the users table shape for response serialization and
    internal typing. It intentionally omits ``password_hash`` because
    authentication credentials must not be exposed through the application
    domain layer.
    """

    id: int
    firebase_uid: Optional[str] = None
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


def normalize_email(email: str) -> str:
    return email.strip().lower()