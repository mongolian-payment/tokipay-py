"""Custom error classes for the TokiPay payment SDK."""

from typing import Any, Optional


class TokiPayError(Exception):
    """Custom error class for TokiPay API errors.

    Includes the HTTP status code and raw response body when available.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code, if available.
        response: Raw response body, if available.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response
