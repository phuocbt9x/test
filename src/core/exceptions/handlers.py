from datetime import datetime
from typing import Any, Dict
from fastapi import FastAPI, Request, status
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
        "timestamp": datetime.utcnow().isoformat(),
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


    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            field_path = ".".join(str(loc) for loc in error["loc"][1:]) if len(error["loc"]) > 1 else str(error["loc"][0])
            errors.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
            })
        
        response_content = create_error_response(
            request=request,
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Input validation failed",
            details=errors,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response_content,
        )
    
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
            headers={"Retry-After": str(getattr(exc, 'retry_after', 60))},
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

