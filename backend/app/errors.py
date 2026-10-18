"""Domain errors that map cleanly onto HTTP responses."""

from typing import Any


class DomainError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.data = data or {}


class NotFound(DomainError):
    status_code = 404
    code = "not_found"


class Unauthorized(DomainError):
    status_code = 401
    code = "unauthorized"


class RateLimited(DomainError):
    status_code = 429
    code = "rate_limited"


class Conflict(DomainError):
    status_code = 409
    code = "conflict"
