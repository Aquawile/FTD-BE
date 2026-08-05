from __future__ import annotations

import psycopg2

from app.auth.models import User, UserCreateRequest, UserPermissionsResponse, UserUpdateRequest
from app.auth.hasher import hash_password
from app.auth.models import normalize_email
from app.auth.repository import (
    create_user as repo_create_user,
    deactivate_user,
    get_user_by_firebase_uid,
    get_user_by_id,
    get_user_permissions as repo_get_user_permissions,
    get_user_with_permissions as repo_get_user_with_permissions,
    update_user as repo_update_user,
)
from app.services.exceptions import UserAlreadyExistsError, UserNotFoundError


def get_authenticated_user(firebase_uid: str) -> User:
    """Locate the application user record that corresponds to a verified Firebase identity.

    This service operation expresses the intent of finding the application-level
    identity record for a verified Firebase user. The database-access layer
    (``app.auth.repository``) knows how to query PostgreSQL; this function
    orchestrates the call and returns the typed domain object.

    Raises ``UserNotFoundError`` when no application user is linked to the
    provided Firebase identity.
    """
    user_data = get_user_by_firebase_uid(firebase_uid)
    if user_data is None:
        raise UserNotFoundError(
            f"No application user found for Firebase identity: {firebase_uid}"
        )
    return User(**user_data)


def get_authenticated_user_by_id(user_id: int) -> User:
    """Retrieve an application user by its internal database identifier.

    This service operation expresses the intent of finding the application-level
    identity record by its internal database identifier. The database-access
    layer knows how to query PostgreSQL; this function orchestrates the call
    and returns the typed domain object.

    Raises ``UserNotFoundError`` when no application user matches the provided
    internal identifier.
    """
    user_data = get_user_by_id(user_id)
    if user_data is None:
        raise UserNotFoundError(f"No application user found with id: {user_id}")
    return User(**user_data)


def get_user_permissions(user_id: int) -> list[dict[str, object]]:
    """Determine which permission names are granted to a specific application user.

    This service operation expresses the intent of finding what permissions
    are granted to a specific application user. The database-access layer
    knows how to query PostgreSQL; this function orchestrates the call and
    returns the raw rows.
    """
    return repo_get_user_permissions(user_id)


def get_user_with_permissions(user_id: int) -> UserPermissionsResponse:
    """Assemble an application user's identity together with their granted permissions in a single result.

    This service operation expresses the intent of combining a user's identity
    with their permission grants. The database-access layer performs the
    relational join; this function enforces the application contract by
    transforming the raw row into a typed response model and ensuring the
    permissions collection is always a list.

    Raises ``UserNotFoundError`` when no application user matches the provided
    internal identifier.
    """
    raw = repo_get_user_with_permissions(user_id)
    if raw is None:
        raise UserNotFoundError(f"No application user found with id: {user_id}")
    permissions = raw.get("permissions") or []
    if not isinstance(permissions, list):
        permissions = list(permissions) if permissions else []
    return UserPermissionsResponse(
        id=raw["id"],
        firebase_uid=raw.get("firebase_uid"),
        email=raw["email"],
        is_active=raw["is_active"],
        permissions=permissions,
    )


def create_user(request: UserCreateRequest) -> User:
    """Register a new application user with a normalized email and hashed password, optionally linking a Firebase identity.

    This service operation expresses the intent of registering a new
    application-level identity. The email is normalized and the password
    is hashed before being persisted. The ``firebase_uid`` is optional
    and only links an existing Firebase identity to the new User.

    Raises ``UserAlreadyExistsError`` when the normalized email or Firebase
    identity is already linked to another application user.
    """
    email = normalize_email(request.email)
    password_hash = hash_password(request.password)
    try:
        return User(**repo_create_user(email, password_hash, request.firebase_uid))
    except psycopg2.IntegrityError as exc:
        raise UserAlreadyExistsError(
            "An application user with this email or Firebase identity already exists"
        ) from exc


def update_user(user_id: int, request: UserUpdateRequest) -> User:
    """Modify the application-owned fields of an existing user.

    This service operation expresses the intent of modifying a User's
    email or active status. Only fields that the application owns
    (``email``, ``is_active``) are updated. The ``firebase_uid``,
    ``id``, ``created_at``, and ``password_hash`` are not modified.

    Raises ``UserNotFoundError`` when no application user matches the provided
    internal identifier.
    Raises ``UserAlreadyExistsError`` when the update would violate a uniqueness
    constraint (for example, changing the email to one already in use).
    """
    email = normalize_email(request.email) if request.email is not None else None
    is_active = request.is_active
    try:
        result = repo_update_user(user_id, email, is_active)
    except psycopg2.IntegrityError as exc:
        raise UserAlreadyExistsError(
            "An application user with this email already exists"
        ) from exc
    if result is None:
        raise UserNotFoundError(f"No application user found with id: {user_id}")
    return User(**result)


def delete_user(user_id: int) -> bool:
    """Soft-delete an application user by deactivating their account status.

    This service operation expresses the intent of deactivating a User's
    application record. The PostgreSQL row is not removed; instead,
    ``is_active`` is set to ``False``. The Firebase identity is not
    modified because Firebase owns authentication credentials independently
    of the application User record.

    Returns ``True`` when the user was active and is now deactivated.
    Returns ``False`` when the user was already inactive or does not exist.
    """
    return deactivate_user(user_id)
