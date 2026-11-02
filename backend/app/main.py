import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from app.api.probes import router as probes_router
from app.api.router import api_router
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings, validate_settings
from app.core.errors import error_response, http_exception_handler, validation_exception_handler
from app.core.observability import (
    REQUEST_ID_HEADER,
    RequestContextMiddleware,
    configure_logging,
    current_request_id,
    init_error_tracking,
)
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


def _integrity_error_response(request: Request, exc: IntegrityError) -> JSONResponse:
    original = str(getattr(exc, "orig", exc)).lower()
    if "unique" in original or "duplicate" in original:
        detail = "A record with the same unique value already exists"
    elif "foreign key" in original or "reference constraint" in original:
        detail = "The request references a missing or protected related record"
    else:
        detail = "The request conflicts with existing data"
    # The client only ever gets the generic detail above; without this, the
    # actual constraint that was violated (which table, which column) is
    # lost entirely -- there was previously no server-side trace of an
    # IntegrityError at all, unlike its sibling handler below.
    logging.getLogger("recruitops.db").error(
        "integrity error on %s %s: %s", request.method, request.url.path, exc, exc_info=exc
    )
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


# Phase 5.1: real production (not staging) must not run on placeholder
# legal text. Staging keeps the placeholders on purpose.
LIVE_ENVS = {"production", "prod"}


@asynccontextmanager
async def _live_lifespan(_app: FastAPI):
    from app.db.session import create_db_engine
    from app.services.legal import assert_no_placeholders_for_live

    assert_no_placeholders_for_live(create_db_engine())
    yield


def _unhandled_error_response(request: Request, exc: Exception) -> JSONResponse:
    """Last resort: log with the request id, answer the standard envelope,
    never the exception text."""
    # Runs in Starlette's outermost error middleware, after the request
    # context has been reset, so read the id the middleware left on the scope.
    request_id = getattr(request.state, "request_id", None) or current_request_id()
    logging.getLogger("recruitops.unhandled").exception(
        "unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    headers = {REQUEST_ID_HEADER: request_id} if request_id else None
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Something went wrong on our side. Quote the request id if you contact support.",
        code="INTERNAL_ERROR",
        headers=headers,
        request_id=request_id,
    )


def create_application() -> FastAPI:
    configure_logging()
    config_errors = validate_settings(settings)
    if config_errors:
        raise RuntimeError("Refusing to start with unsafe configuration: " + "; ".join(config_errors))
    init_error_tracking()
    docs = settings.api_docs_enabled
    application = FastAPI(
        lifespan=_live_lifespan if settings.app_env.strip().lower() in LIVE_ENVS else None,
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    # Exact-match allowlist (no wildcard). The UI is served same-origin via
    # frontend/server.js's /api proxy, so browsers only need CORS in dev.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,  # refresh cookie; origins are exact (no "*") — validate_settings
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Idempotency-Key", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )
    if settings.security_headers_enabled:
        application.add_middleware(SecurityHeadersMiddleware)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(StaleWriteConflict, _stale_write_response)
    application.add_exception_handler(IntegrityError, _integrity_error_response)
    application.add_exception_handler(OperationalError, _database_unavailable_response)
    application.add_exception_handler(SQLAlchemyError, _sqlalchemy_error_response)
    application.add_exception_handler(Exception, _unhandled_error_response)
    # Outermost: the request id exists before anything else runs and is on
    # every response, including CORS preflights and HTTPS redirects.
    application.add_middleware(RequestContextMiddleware)
    application.include_router(probes_router)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_application()


@app.get("/", include_in_schema=False, response_model=None)
def api_root() -> RedirectResponse | dict:
    if settings.api_docs_enabled:
        return RedirectResponse(url="/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    return {"name": settings.app_name, "version": settings.app_version}
