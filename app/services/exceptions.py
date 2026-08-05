from __future__ import annotations


class UserServiceError(Exception):
    """Base exception for user service operations."""


class UserNotFoundError(UserServiceError):
    """Raised when an application user cannot be found."""


class UserAlreadyExistsError(UserServiceError):
    """Raised when a user creation or update would violate a uniqueness constraint."""
