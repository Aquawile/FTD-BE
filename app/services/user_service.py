from __future__ import annotations

from app.auth.models import User
from app.auth.repository import get_user_by_firebase_uid, get_user_by_id
from app.db import query_dict


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
    return query_dict(
        "SELECT permission_name FROM user_permissions_index WHERE user_id = %s",
        (user_id,),
    )