"""Stable error codes and error-shape handlers for Warrant X-Ray API.

All errors conform to the contract:
{"error": {"code": str, "message": str, "field": str | None, "retry_after": int | None}}
"""

from __future__ import annotations

from typing import Any
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from warrantx.api.logging import get_logger

logger = get_logger("warrantx.errors")


class ErrorDetail(BaseModel):
    """Normalized error detail payload."""

    code: str = Field(description="Stable machine-readable error code")
    message: str = Field(description="Human-readable explanation of error")
    field: str | None = Field(default=None, description="Request field causing the error, if any")
    retry_after: int | None = Field(
        default=None, description="Suggested retry delay in seconds for rate limits"
    )


class ErrorResponse(BaseModel):
    """Top-level error response envelope."""

    error: ErrorDetail


class AppError(Exception):
    """Base exception for domain and API errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        field: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field = field
        self.retry_after = retry_after

    def to_dict(self) -> dict[str, Any]:
        """Convert error to response dictionary."""
        d: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.field is not None:
            d["field"] = self.field
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return {"error": d}


class InvalidInputError(AppError):
    """400 Invalid user input."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(
            code="invalid_input",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            field=field,
        )


class NotFoundError(AppError):
    """404 Resource not found."""

    def __init__(self, message: str = "Resource not found", field: str | None = None) -> None:
        super().__init__(
            code="not_found",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            field=field,
        )


class RateLimitedError(AppError):
    """429 Request rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60) -> None:
        super().__init__(
            code="rate_limited",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            retry_after=retry_after,
        )


RateLimitError = RateLimitedError



class BudgetExhaustedError(AppError):
    """429 Daily spend or credit budget exhausted."""

    def __init__(self, message: str = "Daily service budget limit reached") -> None:
        super().__init__(
            code="budget_exhausted",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class SourceUnavailableError(AppError):
    """503 Upstream data source is unreachable or down."""

    def __init__(self, message: str = "Market data source is currently unavailable") -> None:
        super().__init__(
            code="source_unavailable",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class ModelUnavailableError(AppError):
    """503 LLM or inference provider is unavailable."""

    def __init__(self, message: str = "Inference service is currently unavailable") -> None:
        super().__init__(
            code="model_unavailable",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class UnauthorizedError(AppError):
    """401 Missing or invalid admin token."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(
            code="unauthorized",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle custom AppError exceptions."""
    headers: dict[str, str] = {}
    if exc.retry_after is not None:
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers=headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Translate Pydantic/FastAPI validation errors into standard error envelope."""
    errors = exc.errors()
    field = None
    msg = "Invalid input"
    if errors:
        first = errors[0]
        loc = first.get("loc", ())
        if len(loc) > 1:
            field = str(loc[-1])
        msg = first.get("msg", "Invalid input")

    payload = {
        "error": {
            "code": "invalid_input",
            "message": msg,
        }
    }
    if field:
        payload["error"]["field"] = field

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=payload,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Translate standard HTTPExceptions into standard error envelope."""
    code = "error"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "not_found"
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "unauthorized"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = "forbidden"
    elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        code = "rate_limited"

    message = str(exc.detail) if exc.detail else "An error occurred"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
        headers=exc.headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler ensuring no raw stack traces leak to users."""
    logger.error("unhandled_server_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred. Please try again later.",
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers onto a FastAPI app instance."""
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
