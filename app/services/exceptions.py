from __future__ import annotations


class ServiceError(Exception):
    """Base exception for service-layer operations."""


class UserServiceError(ServiceError):
    """Base exception for user service operations."""


class UserNotFoundError(UserServiceError):
    """Raised when an application user cannot be found."""


class UserAlreadyExistsError(UserServiceError):
    """Raised when a user creation or update would violate a uniqueness constraint."""


class UserValidationError(UserServiceError):
    """Raised when an application-level validation rule is violated."""


class DataServiceError(ServiceError):
    """Base exception for data service operations."""


class TickerNotFoundError(DataServiceError):
    """Raised when a requested ticker cannot be found in the data store."""


class FilingNotFoundError(DataServiceError):
    """Raised when a requested filing cannot be found in the data store."""


class DataValidationError(DataServiceError):
    """Raised when a data service operation receives invalid input."""


class DataRetrievalError(DataServiceError):
    """Raised when an underlying database failure prevents data retrieval."""
