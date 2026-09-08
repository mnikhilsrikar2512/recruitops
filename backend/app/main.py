from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from app.api.router import api_router
from app.core.config import settings


def _database_unavailable_response(_request: Request, _exc: OperationalError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "Database is currently unavailable. Please restore SQL Server connectivity and try again."
        },
    )


def _integrity_error_response(_request: Request, exc: IntegrityError) -> JSONResponse:
    original = str(getattr(exc, "orig", exc)).lower()
    if "unique" in original or "duplicate" in original:
        detail = "A record with the same unique value already exists"
    elif "foreign key" in original or "reference constraint" in original:
        detail = "The request references a missing or protected related record"
    else:
        detail = "The request conflicts with existing data"
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": detail})


def _sqlalchemy_error_response(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database error prevented this request from completing"},
    )


def _validation_error_response(_request: Request, exc: RequestValidationError) -> JSONResponse:
    messages: list[str] = []
    for error in exc.errors():
        location_parts = [str(part) for part in error.get("loc", []) if part not in {"body", "query", "path"}]
        location = ".".join(location_parts)
        message = str(error.get("msg", "Invalid value"))
        messages.append(f"{location}: {message}" if location else message)
    detail = messages[0] if len(messages) == 1 else "Request validation failed"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": detail, "errors": messages},
    )


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_exception_handler(RequestValidationError, _validation_error_response)
    application.add_exception_handler(IntegrityError, _integrity_error_response)
    application.add_exception_handler(OperationalError, _database_unavailable_response)
    application.add_exception_handler(SQLAlchemyError, _sqlalchemy_error_response)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_application()
