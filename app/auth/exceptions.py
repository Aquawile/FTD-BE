from __future__ import annotations

from fastapi import status


class AuthenticationError(Exception):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.code = code or "authentication_error"


class AuthenticationInternalError(AuthenticationError):
    def __init__(self, detail: str = "Internal server error") -> None:
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, code="authentication_internal_error")
