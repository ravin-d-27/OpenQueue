"""
OpenQueue custom exceptions.
"""


class OpenQueueError(Exception):
    """Base exception for all OpenQueue errors."""

    pass


class JobNotFoundError(OpenQueueError):
    """Raised when a job is not found."""

    pass


class LeaseTokenError(OpenQueueError):
    """Raised when the lease token is invalid or missing."""

    pass


class RateLimitError(OpenQueueError):
    """Raised when rate limit is exceeded."""

    pass


class AuthenticationError(OpenQueueError):
    """Raised when authentication fails."""

    pass


class ValidationError(OpenQueueError):
    """Raised when request validation fails (e.g., invalid UUID format)."""

    pass
