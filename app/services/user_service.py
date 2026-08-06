from __future__ import annotations

import logging
import psycopg2

from app.auth.models import User, UserCreateRequest, UserPermissionsResponse, UserUpdateRequest, UserWithPermissionDetails, PermissionDetail
from app.auth.hasher import hash_password
from app.auth.models import normalize_email
from app.auth.repository import (
    create_user as repo_create_user,
    deactivate_user,
    get_user_by_firebase_uid,
    get_user_by_id,
    get_user_permission_details as repo_get_user_permission_details,
    get_user_permissions as repo_get_user_permissions,
    get_user_with_permissions as repo_get_user_with_permissions,
    update_user as repo_update_user,
)
from app.services.exceptions import UserAlreadyExistsError, UserNotFoundError, UserValidationError

logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 8
MAX_FIREBASE_UID_LENGTH = 200
MIN_FIREBASE_UID_LENGTH = 10


def _validate_email(email: str) -> None:
    normalized = normalize_email(email)
    if not normalized:
        raise UserValidationError("Email must not be empty")


def _validate_password(password: str) -> None:
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise UserValidationError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )


def _validate_firebase_uid(firebase_uid: str | None) -> None:
    if firebase_uid is None:
        return
    if not isinstance(firebase_uid, str) or not firebase_uid.strip():
        raise UserValidationError("Firebase UID must not be empty")
    length = len(firebase_uid.strip())
    if length < MIN_FIREBASE_UID_LENGTH or length > MAX_FIREBASE_UID_LENGTH:
        raise UserValidationError(
            f"Firebase UID must be between {MIN_FIREBASE_UID_LENGTH} and {MAX_FIREBASE_UID_LENGTH} characters"
        )


def get_authenticated_user(firebase_uid: str) -> User:
    """Locate the application user record that corresponds to a verified Firebase identity.

    This service operation expresses the intent of finding the application-level
    identity record for a verified Firebase user. The database-access layer
    (``app.auth.repository``) knows how to query PostgreSQL; this function
    orchestrates the call and returns the typed domain object.

    Raises ``UserNotFoundError`` when no application user is linked to the
    provided Firebase identity.
    """
    logger.info("service:get_authenticated_user firebase_uid=%s", firebase_uid)
    user_data = get_user_by_firebase_uid(firebase_uid)
    if user_data is None:
        logger.warning("service:get_authenticated_user user_not_found firebase_uid=%s", firebase_uid)
        raise UserNotFoundError(
            f"No application user found for Firebase identity: {firebase_uid}"
        )
    logger.info("service:get_authenticated_user success user_id=%s", user_data.get("id"))
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
    logger.info("service:get_authenticated_user_by_id user_id=%s", user_id)
    user_data = get_user_by_id(user_id)
    if user_data is None:
        logger.warning("service:get_authenticated_user_by_id user_not_found user_id=%s", user_id)
        raise UserNotFoundError(f"No application user found with id: {user_id}")
    logger.info("service:get_authenticated_user_by_id success firebase_uid=%s", user_data.get("firebase_uid"))
    return User(**user_data)


def get_user_permissions(user_id: int) -> list[dict[str, object]]:
    """Determine which permission names are granted to a specific application user.

    This service operation expresses the intent of finding what permissions
    are granted to a specific application user. The database-access layer
    knows how to query PostgreSQL; this function orchestrates the call and
    returns the raw rows.
    """
    logger.debug("service:get_user_permissions user_id=%s", user_id)
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
    logger.debug("service:get_user_with_permissions user_id=%s", user_id)
    raw = repo_get_user_with_permissions(user_id)
    if raw is None:
        logger.warning("service:get_user_with_permissions user_not_found user_id=%s", user_id)
        raise UserNotFoundError(f"No application user found with id: {user_id}")
    permissions = raw.get("permissions") or []
    if not isinstance(permissions, list):
        permissions = list(permissions) if permissions else []
    logger.info("service:get_user_with_permissions success user_id=%s permission_count=%s", user_id, len(permissions))
    return UserPermissionsResponse(
        id=raw["id"],
        firebase_uid=raw.get("firebase_uid"),
        email=raw["email"],
        is_active=raw["is_active"],
        permissions=permissions,
    )


def get_user_with_permission_details(user_id: int) -> UserWithPermissionDetails:
    """Assemble an application user's identity with full permission details through the normalized relational schema.

    This service operation expresses the intent of combining a user's identity
    with rich permission metadata (id, name, description) retrieved by joining
    ``user_permissions`` with ``permissions``. The relational work is performed
    entirely inside the backend boundary; the client receives a single
    application-level response and does not need to understand the junction
    table or issue separate requests.

    Raises ``UserNotFoundError`` when no application user matches the provided
    internal identifier.
    """
    logger.debug("service:get_user_with_permission_details user_id=%s", user_id)
    rows = repo_get_user_permission_details(user_id)
    if not rows:
        logger.warning("service:get_user_with_permission_details user_not_found user_id=%s", user_id)
        raise UserNotFoundError(f"No application user found with id: {user_id}")
    first = rows[0]
    permissions = [
        PermissionDetail(
            id=row["permission_id"],
            name=row["permission_name"],
            description=row.get("permission_description"),
        )
        for row in rows
        if row.get("permission_id") is not None
    ]
    logger.info("service:get_user_with_permission_details success user_id=%s permission_count=%s", user_id, len(permissions))
    return UserWithPermissionDetails(
        id=first["id"],
        firebase_uid=first.get("firebase_uid"),
        email=first["email"],
        is_active=first["is_active"],
        permissions=permissions,
    )


def create_user(request: UserCreateRequest) -> User:
    """Register a new application user with a normalized email and hashed password, optionally linking a Firebase identity.

    This service operation expresses the intent of registering a new
    application-level identity. The email is normalized and the password
    is hashed before being persisted. The ``firebase_uid`` is optional
    and only links an existing Firebase identity to the new User.

    Raises ``UserValidationError`` when the request fails application-level
    validation (empty email, weak password, invalid Firebase UID).
    Raises ``UserAlreadyExistsError`` when the normalized email or Firebase
    identity is already linked to another application user.
    """
    _validate_email(request.email)
    _validate_password(request.password)
    _validate_firebase_uid(request.firebase_uid)

    email = normalize_email(request.email)
    logger.info("service:create_user email=%s firebase_uid=%s", email, request.firebase_uid)
    password_hash = hash_password(request.password)
    try:
        user = User(**repo_create_user(email, password_hash, request.firebase_uid))
        logger.info("service:create_user success user_id=%s", user.id)
        return user
    except psycopg2.IntegrityError as exc:
        logger.warning("service:create_user conflict email=%s firebase_uid=%s", email, request.firebase_uid)
        raise UserAlreadyExistsError(
            "An application user with this email or Firebase identity already exists"
        ) from exc


def update_user(user_id: int, request: UserUpdateRequest) -> User:
    """Modify the application-owned fields of an existing user.

    This service operation expresses the intent of modifying a User's
    email or active status. Only fields that the application owns
    (``email``, ``is_active``) are updated. The ``firebase_uid``,
    ``id``, ``created_at``, and ``password_hash`` are not modified.

    Raises ``UserValidationError`` when no updatable fields are provided or
    the email format is invalid.
    Raises ``UserNotFoundError`` when no application user matches the provided
    internal identifier.
    Raises ``UserAlreadyExistsError`` when the update would violate a uniqueness
    constraint (for example, changing the email to one already in use).
    """
    if request.email is None and request.is_active is None:
        raise UserValidationError("At least one updatable field must be provided")

    email = normalize_email(request.email) if request.email is not None else None
    if email is not None:
        _validate_email(email)

    logger.info("service:update_user user_id=%s email=%s is_active=%s", user_id, email, request.is_active)
    try:
        result = repo_update_user(user_id, email, request.is_active)
    except psycopg2.IntegrityError as exc:
        logger.warning("service:update_user conflict user_id=%s email=%s", user_id, email)
        raise UserAlreadyExistsError(
            "An application user with this email already exists"
        ) from exc
    if result is None:
        logger.warning("service:update_user user_not_found user_id=%s", user_id)
        raise UserNotFoundError(f"No application user found with id: {user_id}")
    logger.info("service:update_user success user_id=%s", result.get("id"))
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
    logger.info("service:delete_user user_id=%s", user_id)
    result = deactivate_user(user_id)
    logger.info("service:delete_user success user_id=%s deactivated=%s", user_id, result)
    return result
