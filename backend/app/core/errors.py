"""PRD §9.0 error contract (Phase 4.9).

Every error response carries

    {"detail": "<human message>",
     "error": {"code": "STABLE_CODE", "message": "<human message>",
               "field_errors": [{"field": "...", "message": "..."}]}}

``error`` is the documented contract. ``detail`` is kept, with the same
message, so existing clients (the frontend's ApiError, older scripts) keep
working unchanged.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "AUTH_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    423: "LOCKED",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


class ApiError(HTTPException):
    """An HTTPException with an explicit stable code."""

    def __init__(self, status_code: int, code: str, message: str, field_errors: list[dict] | None = None,
                 headers: dict[str, str] | None = None) -> None:
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.field_errors = field_errors or []


def error_body(status_code: int, message: Any, code: str | None = None,
               field_errors: list[dict] | None = None, **extra: Any) -> dict:
    text = message if isinstance(message, str) else "Request failed"
    return {
        "detail": message,
        "error": {
            "code": code or STATUS_CODES.get(status_code, "ERROR"),
            "message": text,
            "field_errors": field_errors or [],
        },
        **extra,
    }


def error_response(status_code: int, message: Any, code: str | None = None,
                   field_errors: list[dict] | None = None, headers: dict | None = None, **extra: Any) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(error_body(status_code, message, code, field_errors, **extra)),
        headers=headers,
    )


def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return error_response(
        exc.status_code,
        exc.detail,
        code=getattr(exc, "code", None),
        field_errors=getattr(exc, "field_errors", None),
        headers=getattr(exc, "headers", None),
    )


def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    messages: list[str] = []
    field_errors: list[dict] = []
    for error in exc.errors():
        location_parts = [str(part) for part in error.get("loc", []) if part not in {"body", "query", "path"}]
        location = ".".join(location_parts)
        message = str(error.get("msg", "Invalid value"))
        messages.append(f"{location}: {message}" if location else message)
        field_errors.append({"field": location or None, "message": message})
    detail = messages[0] if len(messages) == 1 else "Request validation failed"
    return error_response(422, detail, code="VALIDATION_ERROR", field_errors=field_errors, errors=messages)
