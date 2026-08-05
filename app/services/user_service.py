from __future__ import annotations

from app.auth.models import User, UserCreateRequest, UserUpdateRequest
from app.auth.repository import (
    create_user,
    deactivate_user,
    get_user_by_firebase_uid,
    get_user_by_id,
    get_user_with_permissions,
    update_user,
)
from app.auth.hasher import hash_password
from app.auth.models import normalize_email


def get_authenticated_user(firebase_uid: str) -> User | None:
    """Retrieve the application User corresponding to the authenticated Firebase identity.

    This service operation expresses the intent of finding the application-level
    identity record for a verified Firebase user. The database-access layer
    (``app.auth.repository``) knows how to query PostgreSQL; this function
    orchestrates the call and returns the typed domain object.
    """
    user_data = get_user_by_firebase_uid(firebase_uid)
    if user_data is None:
        return None
    return User(**user_data)


def get_authenticated_user_by_id(user_id: int) -> User | None:
    """Retrieve the application User by internal PostgreSQL user ID.

    This service operation expresses the intent of finding the application-level
    identity record by its internal database identifier. The database-access
    layer knows how to query PostgreSQL; this function orchestrates the call
    and returns the typed domain object.
    """
    user_data = get_user_by_id(user_id)
    if user_data is None:
        return None
    return User(**user_data)


def get_user_permissions(user_id: int) -> list[dict[str, object]]:
    """Retrieve the permission names for the given user.

    This service operation expresses the intent of finding what permissions
    are granted to a specific application user. The database-access layer
    knows how to query PostgreSQL; this function orchestrates the call and
    returns the raw rows.
    """
    from app.db import query_dict
    return query_dict(
        "SELECT permission_name FROM user_permissions_index WHERE user_id = %s",
        (user_id,),
    )


def get_user_with_permissions(user_id: int) -> dict | None:
    """Retrieve a user and their permissions in a single relational query.

    This service operation expresses the intent of assembling an
    application-level response that combines user identity with
    their granted permissions. The database-access layer performs
    the join; this function orchestrates the call and returns
    the raw result row.
    """
    return get_user_with_permissions(user_id)


def create_user(request: UserCreateRequest) -> User:
    """Create a new application User record.

    This service operation expresses the intent of registering a new
    application-level identity. The email is normalized and the password
    is hashed before being persisted. The ``firebase_uid`` is optional
    and only links an existing Firebase identity to the new User.
    """
    email = normalize_email(request.email)
    password_hash = hash_password(request.password)
    return User(**create_user(email, password_hash, request.firebase_uid))


def update_user(user_id: int, request: UserUpdateRequest) -> User | None:
    """Update an existing application User's application-owned fields.

    This service operation expresses the intent of modifying a User's
    email or active status. Only fields that the application owns
    (``email``, ``is_active``) are updated. The ``firebase_uid``,
    ``id``, ``created_at``, and ``password_hash`` are not modified.
    """
    email = normalize_email(request.email) if request.email is not None else None
    is_active = request.is_active
    result = update_user(user_id, email, is_active)
    if result is None:
        return None
    return User(**result)


def delete_user(user_id: int) -> bool:
    """Deactivate an application User record (soft delete).

    This service operation expresses the intent of deactivating a User's
    application record. The PostgreSQL row is not removed; instead,
    ``is_active`` is set to ``False``. The Firebase identity is not
    modified because Firebase owns authentication credentials independently
    of the application User record.
    """
    return deactivate_user(user_id)