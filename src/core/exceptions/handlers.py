from typing import Any, Dict, Optional
from src.core.i18n import __
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from .base import BaseAppException
from slowapi.errors import RateLimitExceeded


def create_validation_error_response(
    errors: Dict[str, list[str]],
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "success": False,
        "status_code": status_code,
        "message": message,
        "errors": errors,
    }


def create_general_error_response(
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> Dict[str, Any]:
    return {
        "success": False,
        "status_code": status_code,
        "message": message,
        "errors": None,
    }


def format_field_errors(details: list[Dict[str, Any]]) -> Dict[str, list[str]]:
    errors_dict: Dict[str, list[str]] = {}
    for detail in details:
        if isinstance(detail, dict) and "field" in detail:
            field = detail.get("field") or "general"
            error_message = detail.get(
                "message", __("exceptions.validation_error_default")
            )
            if field not in errors_dict:
                errors_dict[field] = []
            errors_dict[field].append(error_message)
    return errors_dict


def format_pydantic_error(error: Dict[str, Any]) -> tuple[Optional[str], str]:
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

    return (field_path, msg)


def format_http_exception_detail(detail: Any) -> Dict[str, list[str]]:
    errors_dict: Dict[str, list[str]] = {}

    if isinstance(detail, list):
        for item in detail:
            if isinstance(item, dict):
                field = item.get("field") or "general"
                message = item.get("message", str(item))
                if field not in errors_dict:
                    errors_dict[field] = []
                errors_dict[field].append(message)
            else:
                if "general" not in errors_dict:
                    errors_dict["general"] = []
                errors_dict["general"].append(str(item))
    else:
        errors_dict["general"] = [str(detail)]

    return errors_dict


def get_integrity_error_message(exc: IntegrityError) -> str:
    error_str = str(exc).lower()

    if "unique constraint" in error_str or "duplicate" in error_str:
        return __("exceptions.duplicate_entry_found")
    elif "foreign key constraint" in error_str:
        return __("exceptions.referenced_resource_not_exist")
    elif "not null constraint" in error_str:
        return __("exceptions.required_field_missing")

    return __("exceptions.database_constraint_violation")


def get_operational_error_message(exc: OperationalError) -> str:
    if "timeout" in str(exc).lower():
        return __("exceptions.database_operation_timeout")
    return __("exceptions.database_connection_error")


def setup_exception_handlers(app: FastAPI, debug: bool = False) -> None:
    @app.exception_handler(BaseAppException)
    async def app_exception_handler(
        request: Request, exc: BaseAppException
    ) -> JSONResponse:
        if isinstance(exc.details, list) and exc.details:
            first_detail = exc.details[0]
            if isinstance(first_detail, dict) and "field" in first_detail:
                errors_dict = format_field_errors(exc.details)
                default_validation_message = __("exceptions.validation_error")
                response_content = create_validation_error_response(
                    errors=errors_dict,
                    status_code=exc.status_code,
                    message=exc.message
                    if exc.message != default_validation_message
                    else None,
                )
            else:
                response_content = create_general_error_response(
                    message=exc.message,
                    status_code=exc.status_code,
                )
        else:
            response_content = create_general_error_response(
                message=exc.message,
                status_code=exc.status_code,
            )

        return JSONResponse(
            status_code=exc.status_code,
            content=response_content,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors_dict: Dict[str, list[str]] = {}

        for error in exc.errors():
            field_path, message = format_pydantic_error(error)
            field_key = field_path or "general"

            if field_key not in errors_dict:
                errors_dict[field_key] = []
            errors_dict[field_key].append(message)

        response_content = create_validation_error_response(
            errors=errors_dict,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=__("exceptions.validation_error"),
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response_content,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        if exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            errors_dict = format_http_exception_detail(exc.detail)
            response_content = create_validation_error_response(
                errors=errors_dict,
                status_code=exc.status_code,
                message=__("exceptions.validation_error"),
            )
        else:
            response_content = create_general_error_response(
                message=str(exc.detail),
                status_code=exc.status_code,
            )

        return JSONResponse(
            status_code=exc.status_code,
            content=response_content,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        error_message = get_integrity_error_message(exc)
        response_content = create_general_error_response(
            message=error_message,
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
        error_message = get_operational_error_message(exc)
        response_content = create_general_error_response(
            message=error_message,
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
        response_content = create_general_error_response(
            message=__("exceptions.database_operation_failed"),
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
        response_content = create_general_error_response(
            message=__("exceptions.rate_limit_exceeded_message"),
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
        response_content = create_general_error_response(
            message=__("exceptions.unexpected_error_occurred"),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_content,
        )
