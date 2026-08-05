from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request

from app.auth.firebase_auth import validate_firebase_token
from app.auth.hasher import verify_password
from app.auth.models import (
    LoginRequest,
    LoginResponse,
    User,
    UserCreateRequest,
    UserPermissionsResponse,
    UserUpdateRequest,
    normalize_email,
)
from app.auth.token import create_access_token
from app.auth.repository import get_user_by_email
from app.auth.dependencies import get_current_application_user
from app.services.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.services.user_service import (
    get_authenticated_user,
    create_user,
    delete_user,
    get_user_with_permissions,
    update_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    email = normalize_email(request.email)
    user = get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user["id"], "email": user["email"]})
    return LoginResponse(access_token=token, token_type="bearer")


@router.get("/me")
def auth_me(request: Request):
    auth_header = request.headers.get("Authorization")
    if auth_header is None or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = auth_header[len("Bearer ") :]
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    firebase_user = validate_firebase_token(token)
    if firebase_user is not None:
        return {
            "auth_method": "firebase",
            "firebase_uid": firebase_user.get("firebase_uid"),
            "email": firebase_user.get("email"),
            "email_verified": firebase_user.get("email_verified"),
        }
    from app.auth.token import verify_token
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id = payload.get("sub")
    email = payload.get("email")
    if user_id is None or email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing required claims")
    return {
        "auth_method": "internal",
        "user_id": int(user_id),
        "email": email,
    }


@router.get("/me/user", response_model=User)
def auth_me_user(current_user: User = Depends(get_current_application_user)) -> User:
    return current_user


@router.get("/users/{user_id}", response_model=User)
def auth_get_user(
    user_id: int,
    current_user: User = Depends(get_current_application_user),
) -> User:
    """Retrieve a User by internal ID.

    The authenticated user may only retrieve their own record.
    """
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return current_user


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def auth_create_user(
    request: UserCreateRequest,
    current_user: User = Depends(get_current_application_user),
) -> User:
    """Create a new application User record.

    Requires authentication. The authenticated user's identity
    establishes the context for the operation.
    """
    try:
        return create_user(request)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or Firebase identity already exists",
        )


@router.patch("/me/user", response_model=User)
def auth_update_user(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_application_user),
) -> User:
    """Update the authenticated user's application-owned fields.

    Only ``email`` and ``is_active`` may be modified. The
    ``firebase_uid``, ``id``, ``created_at``, and ``password_hash``
    are not updatable through this endpoint.
    """
    try:
        updated = update_user(current_user.id, request)
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )
    return updated


@router.delete("/me/user", status_code=status.HTTP_204_NO_CONTENT)
def auth_delete_user(
    current_user: User = Depends(get_current_application_user),
) -> None:
    """Deactivate the authenticated user's application record.

    This is a soft delete: the PostgreSQL row remains but
    ``is_active`` is set to ``False``. The Firebase identity
    is not modified because Firebase owns authentication
    credentials independently of the application User record.
    """
    success = delete_user(current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None


@router.get("/me/user/permissions", response_model=UserPermissionsResponse)
def auth_me_user_permissions(
    current_user: User = Depends(get_current_application_user),
) -> UserPermissionsResponse:
    """Retrieve the authenticated user with their granted permissions.

    This endpoint demonstrates a relational aggregation: a single
    query joins the ``users`` table with ``user_permissions_index``
    to assemble the user identity and their permissions into one
    coherent response object. The client receives the result as
    application-level JSON rather than needing to understand the
    foreign-key relationship or make separate requests.
    """
    try:
        return get_user_with_permissions(current_user.id)
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")