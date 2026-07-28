from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.auth.hasher import verify_password
from app.auth.models import LoginRequest, LoginResponse, normalize_email
from app.auth.token import create_access_token
from app.auth.repository import get_user_by_email

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