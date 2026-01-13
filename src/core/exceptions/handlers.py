from typing import Any, Dict
from src.core.utils.timezone import utcnow
from src.core.i18n import __
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from .base import BaseAppException
from .types import ErrorCode
from slowapi.errors import RateLimitExceeded


def create_error_response(
    request: Request,
    error_code: str,
    message: str,
    details: Any = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> Dict[str, Any]:
    request_id = getattr(request.state, "request_id", None)

    return {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
        },
        "timestamp": utcnow().isoformat(),
        "path": str(request.url.path),
        "request_id": request_id,
    }


def setup_exception_handlers(app: FastAPI, debug: bool = False) -> None:
    @app.exception_handler(BaseAppException)
    async def app_exception_handler(
        request: Request, exc: BaseAppException
    ) -> JSONResponse:
        response_content = create_error_response(
            request=request,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            status_code=exc.status_code,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=response_content,
            headers=exc.headers,
        )

    def _format_validation_error(error: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single validation error"""
        loc_start_index = 1 if error["loc"] and error["loc"][0] == "body" else 0
        field_path = (
            ".".join(str(loc) for loc in error["loc"][loc_start_index:])
            if error.get("loc")
            else None
        )

        error_type = error["type"]
        msg = error["msg"]

        if error_type == "missing":
            field_name = field_path or "field"
            field_key = f"field.{field_name}"
            field_label = __(field_key)
            if field_label == field_key:
                field_label = field_name.replace("_", " ").title()
            msg = __("validation.required", attribute=field_label)
        elif msg.startswith("Value error, "):
            msg = msg.replace("Value error, ", "", 1)

        return {
            "field": field_path,
            "message": msg,
            "type": error_type,
        }

    def _create_validation_error_response(
        request: Request,
        details: list,
        status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
    ) -> JSONResponse:
        response_content = create_error_response(
            request=request,
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Input validation failed",
            details=details,
            status_code=status_code,
        )
        return JSONResponse(status_code=status_code, content=response_content)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [_format_validation_error(error) for error in exc.errors()]
        return _create_validation_error_response(request, errors)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        if exc.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )

        details = (
            exc.detail
            if isinstance(exc.detail, list)
            else [
                {
                    "field": None,
                    "message": exc.detail,
                    "type": "http_exception",
                }
            ]
        )

        return _create_validation_error_response(request, details)

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        error_message = "Database constraint violation"
        error_code = ErrorCode.DATABASE_INTEGRITY_ERROR

        if "unique constraint" in str(exc).lower() or "duplicate" in str(exc).lower():
            error_message = "Duplicate entry found"
            error_code = ErrorCode.DUPLICATE_ENTRY
        elif "foreign key constraint" in str(exc).lower():
            error_message = "Referenced resource does not exist"
        elif "not null constraint" in str(exc).lower():
            error_message = "Required field is missing"

        response_content = create_error_response(
            request=request,
            error_code=error_code,
            message=error_message,
            details=str(exc) if debug else None,
            status_code=status.HTTP_409_CONFLICT,
        )

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=response_content,
        )

    @app.exception_handler(OperationalError)
    async def operational_error_handler(
        request: Request, exc: OperationalError
    ) -> JSONResponse:
        error_message = "Database connection error"
        error_code = ErrorCode.DATABASE_CONNECTION_ERROR

        if "timeout" in str(exc).lower():
            error_message = "Database operation timeout"
            error_code = ErrorCode.DATABASE_TIMEOUT

        response_content = create_error_response(
            request=request,
            error_code=error_code,
            message=error_message,
            details=str(exc) if debug else None,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response_content,
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        response_content = create_error_response(
            request=request,
            error_code=ErrorCode.DATABASE_ERROR,
            message="Database operation failed",
            details=str(exc) if debug else None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_content,
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(
        request: Request, exc: RateLimitExceeded
    ) -> JSONResponse:
        response_content = create_error_response(
            request=request,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded. Too many requests.",
            details={"error": str(exc)} if debug else None,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=response_content,
            headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        response_content = create_error_response(
            request=request,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            details={"error": str(exc)} if debug else None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_content,
        )
