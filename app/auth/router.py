from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request

from app.auth.firebase_auth import validate_firebase_token
from app.auth.hasher import verify_password
from app.auth.models import LoginRequest, LoginResponse, User, normalize_email
from app.auth.token import create_access_token
from app.auth.repository import get_user_by_email
from app.auth.dependencies import get_current_application_user
from app.services.user_service import get_authenticated_user

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