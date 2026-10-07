import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from app.api.router import api_router
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings, validate_settings
from app.core.errors import error_response, http_exception_handler, validation_exception_handler
from app.core.security_headers import SecurityHeadersMiddleware
from app.repositories.versioning import StaleWriteConflict


def _database_unavailable_response(_request: Request, _exc: OperationalError) -> JSONResponse:
    return error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Database is currently unavailable. Please restore SQL Server connectivity and try again.",
        code="DATABASE_UNAVAILABLE",
    )


def _stale_write_response(_request: Request, exc: StaleWriteConflict) -> JSONResponse:
    """Phase 4.3: the record changed after the client loaded it. The fresh
    record comes back so the client can show what changed and reload."""
    from fastapi.encoders import jsonable_encoder

    return error_response(
        status.HTTP_409_CONFLICT,
        "This record was changed by someone else after you opened it. Reload to see the latest version, then make your change again.",
        code="STALE_WRITE",
        current_version=exc.current_version,
        current=jsonable_encoder(exc.current) if exc.current is not None else None,
    )


def _integrity_error_response(_request: Request, exc: IntegrityError) -> JSONResponse:
    original = str(getattr(exc, "orig", exc)).lower()
    if "unique" in original or "duplicate" in original:
        detail = "A record with the same unique value already exists"
    elif "foreign key" in original or "reference constraint" in original:
        detail = "The request references a missing or protected related record"
    else:
        detail = "The request conflicts with existing data"
    return error_response(status.HTTP_409_CONFLICT, detail, code="DATA_CONFLICT")


def _sqlalchemy_error_response(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    # The client gets a generic message; the real cause goes to the server
    # log so a failing query can be found (it was invisible before).
    logging.getLogger("recruitops.db").error(
        "database error on %s %s: %s", request.method, request.url.path, exc, exc_info=exc
    )
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "A database error prevented this request from completing",
        code="DATABASE_ERROR",
    )


def create_application() -> FastAPI:
    config_errors = validate_settings(settings)
    if config_errors:
        raise RuntimeError("Refusing to start with unsafe configuration: " + "; ".join(config_errors))
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    # Exact-match allowlist (no wildcard). The UI is served same-origin via
    # frontend/server.js's /api proxy, so browsers only need CORS in dev.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,  # refresh cookie; origins are exact (no "*") — validate_settings
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Idempotency-Key"],
    )
    if settings.security_headers_enabled:
        application.add_middleware(SecurityHeadersMiddleware)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(StaleWriteConflict, _stale_write_response)
    application.add_exception_handler(IntegrityError, _integrity_error_response)
    application.add_exception_handler(OperationalError, _database_unavailable_response)
    application.add_exception_handler(SQLAlchemyError, _sqlalchemy_error_response)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_application()


@app.get("/", include_in_schema=False)
def api_root() -> RedirectResponse:
    return RedirectResponse(url="/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
