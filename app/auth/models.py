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


class UserCreateRequest(BaseModel):
    """Request model for creating a new application User.

    Only application-owned fields are accepted. The ``firebase_uid`` is
    optional because a User can exist without a linked Firebase identity
    (internal authentication only). The ``password`` is required for
    internal authentication but is never stored or returned in this model;
    it is consumed by the service layer and forwarded to the hasher.
    """

    email: str
    password: str
    firebase_uid: Optional[str] = None


class UserUpdateRequest(BaseModel):
    """Request model for updating an existing application User.

    Only application-owned fields that the user is permitted to modify
    are accepted. The ``firebase_uid``, ``id``, ``created_at``, and
    ``password_hash`` are not updatable through this model.
    """

    email: Optional[str] = None
    is_active: Optional[bool] = None


class UserPermissionsResponse(BaseModel):
    """Response model for a user with their granted permissions.

    This model assembles the user identity fields with a list of
    permission names retrieved through a relational join. It exposes
    only the fields the API contract intends to return, not the
    full PostgreSQL row.
    """

    id: int
    firebase_uid: Optional[str] = None
    email: str
    is_active: bool
    permissions: list[str]


def normalize_email(email: str) -> str:
    return email.strip().lower()