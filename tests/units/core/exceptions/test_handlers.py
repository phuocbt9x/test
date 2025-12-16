"""
Unit tests for Exception Handlers.

Tests cover:
- BaseAppException handling
- Validation error handling
- Database error handling (IntegrityError, OperationalError)
- Rate limit exception handling
- Generic exception fallback
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from slowapi.errors import RateLimitExceeded
from unittest.mock import MagicMock

from src.core.exceptions.base import (
    BaseAppException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ConflictException,
)
from src.core.exceptions.types import ErrorCode
from src.core.exceptions.handlers import create_error_response, setup_exception_handlers


class TestCreateErrorResponse:
    """Test error response creation."""

    def test_create_error_response_basic(self):
        """Test basic error response creation."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.state.request_id = "test-request-id"

        response = create_error_response(
            request=request,
            error_code="TEST_ERROR",
            message="Test error message",
            status_code=400,
        )

        assert response["success"] is False
        assert response["error"]["code"] == "TEST_ERROR"
        assert response["error"]["message"] == "Test error message"
        assert response["path"] == "/api/test"
        assert response["request_id"] == "test-request-id"
        assert "timestamp" in response

    def test_create_error_response_with_details(self):
        """Test error response with details."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.state.request_id = None

        details = {"field": "email", "error": "invalid format"}

        response = create_error_response(
            request=request,
            error_code="VALIDATION_ERROR",
            message="Validation failed",
            details=details,
            status_code=422,
        )

        assert response["error"]["details"] == details

    def test_create_error_response_no_request_id(self):
        """Test error response without request ID."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        # No request_id in state

        response = create_error_response(
            request=request, error_code="TEST_ERROR", message="Test", status_code=500
        )

        assert response["request_id"] is None


class TestExceptionHandlers:
    """Test exception handler setup and functionality."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app with exception handlers."""
        app = FastAPI()
        setup_exception_handlers(app, debug=False)
        return app

    @pytest.fixture
    def debug_app(self):
        """Create test app with debug mode."""
        app = FastAPI()
        setup_exception_handlers(app, debug=True)
        return app

    @pytest.mark.asyncio
    async def test_base_app_exception_handler(self, app):
        """Test handling of BaseAppException."""
        exc = AuthenticationException(
            message="Invalid credentials", error_code=ErrorCode.INVALID_CREDENTIALS
        )

        request = MagicMock(spec=Request)
        request.url.path = "/api/login"
        request.state.request_id = "test-id"

        # Get the handler
        handler = app.exception_handlers[BaseAppException]
        response = await handler(request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        content = response.body.decode()
        assert "Invalid credentials" in content
        assert ErrorCode.INVALID_CREDENTIALS in content

    @pytest.mark.asyncio
    async def test_validation_error_handler(self, app):
        """Test RequestValidationError handling."""
        # Create validation error
        from pydantic import BaseModel, Field, ValidationError

        class TestModel(BaseModel):
            email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
            age: int = Field(..., ge=0, le=150)

        try:
            TestModel(email="invalid-email", age=200)
        except ValidationError as e:
            pydantic_errors = e.errors()

        exc = RequestValidationError(pydantic_errors)

        request = MagicMock(spec=Request)
        request.url.path = "/api/users"
        request.state.request_id = "val-test"

        handler = app.exception_handlers[RequestValidationError]
        response = await handler(request, exc)

        assert response.status_code == 422
        content_str = response.body.decode()
        assert "validation" in content_str.lower()

    @pytest.mark.asyncio
    async def test_integrity_error_unique_constraint(self, app):
        """Test IntegrityError for unique constraint violation."""
        exc = IntegrityError(
            "INSERT INTO users (email) VALUES (?)",
            {},
            Exception("UNIQUE constraint failed: users.email"),
        )

        request = MagicMock(spec=Request)
        request.url.path = "/api/users"
        request.state.request_id = "integrity-test"

        handler = app.exception_handlers[IntegrityError]
        response = await handler(request, exc)

        assert response.status_code == 409
        content_str = response.body.decode()
        assert "Duplicate" in content_str or "duplicate" in content_str.lower()

    @pytest.mark.asyncio
    async def test_integrity_error_foreign_key(self, app):
        """Test IntegrityError for foreign key constraint."""
        exc = IntegrityError(
            "INSERT INTO posts (user_id) VALUES (?)",
            {},
            Exception("FOREIGN KEY constraint failed"),
        )

        request = MagicMock(spec=Request)
        request.url.path = "/api/posts"
        request.state.request_id = "fk-test"

        handler = app.exception_handlers[IntegrityError]
        response = await handler(request, exc)

        assert response.status_code == 409
        content_str = response.body.decode()
        assert (
            "Referenced resource" in content_str or "not exist" in content_str.lower()
        )

    @pytest.mark.asyncio
    async def test_integrity_error_not_null(self, app):
        """Test IntegrityError for not null constraint."""
        exc = IntegrityError(
            "INSERT INTO users (name) VALUES (NULL)",
            {},
            Exception("NOT NULL constraint failed: users.name"),
        )

        request = MagicMock(spec=Request)
        request.url.path = "/api/users"
        request.state.request_id = "null-test"

        handler = app.exception_handlers[IntegrityError]
        response = await handler(request, exc)

        assert response.status_code == 409
        content_str = response.body.decode()
        assert "Required field" in content_str or "missing" in content_str.lower()

    @pytest.mark.asyncio
    async def test_operational_error_connection(self, app):
        """Test OperationalError for database connection issues."""
        exc = OperationalError(
            "SELECT * FROM users", {}, Exception("could not connect to server")
        )

        request = MagicMock(spec=Request)
        request.url.path = "/api/users"
        request.state.request_id = "conn-test"

        handler = app.exception_handlers[OperationalError]
        response = await handler(request, exc)

        assert response.status_code == 503
        content_str = response.body.decode()
        assert "connection" in content_str.lower()

    @pytest.mark.asyncio
    async def test_operational_error_timeout(self, app):
        """Test OperationalError for timeout."""
        exc = OperationalError("SELECT * FROM users", {}, Exception("timeout expired"))

        request = MagicMock(spec=Request)
        request.url.path = "/api/users"
        request.state.request_id = "timeout-test"

        handler = app.exception_handlers[OperationalError]
        response = await handler(request, exc)

        assert response.status_code == 503
        content_str = response.body.decode()
        assert "timeout" in content_str.lower()

    @pytest.mark.asyncio
    async def test_sqlalchemy_error_generic(self, app):
        """Test generic SQLAlchemyError."""
        exc = SQLAlchemyError("Generic database error")

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.state.request_id = "db-error"

        handler = app.exception_handlers[SQLAlchemyError]
        response = await handler(request, exc)

        assert response.status_code == 500
        content_str = response.body.decode()
        assert "Database operation failed" in content_str

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, app):
        """Test RateLimitExceeded error."""
        exc = RateLimitExceeded("1 per 1 minute")
        exc.retry_after = 60

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.state.request_id = "rate-limit"

        handler = app.exception_handlers[RateLimitExceeded]
        response = await handler(request, exc)

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        content_str = response.body.decode()
        assert "Rate limit" in content_str

    @pytest.mark.asyncio
    async def test_generic_exception_handler(self, app):
        """Test generic exception fallback."""
        exc = Exception("Unexpected error occurred")

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.state.request_id = "generic-error"

        handler = app.exception_handlers[Exception]
        response = await handler(request, exc)

        assert response.status_code == 500
        content_str = response.body.decode()
        assert "unexpected error" in content_str.lower()

    @pytest.mark.asyncio
    async def test_debug_mode_includes_details(self, debug_app):
        """Test that debug mode includes error details."""
        exc = SQLAlchemyError("Detailed database error message")

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.state.request_id = "debug-test"

        handler = debug_app.exception_handlers[SQLAlchemyError]
        response = await handler(request, exc)

        content_str = response.body.decode()
        # In debug mode, should include error details
        assert (
            "Detailed database error message" in content_str
            or "details" in content_str.lower()
        )

    @pytest.mark.asyncio
    async def test_production_mode_hides_details(self, app):
        """Test that production mode hides sensitive error details."""
        exc = SQLAlchemyError("Sensitive internal error with credentials")

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.state.request_id = "prod-test"

        handler = app.exception_handlers[SQLAlchemyError]
        response = await handler(request, exc)

        content_str = response.body.decode()
        # In production, should NOT include sensitive details
        assert "credentials" not in content_str.lower()
        assert "Database operation failed" in content_str


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_authentication_exception(self):
        """Test AuthenticationException."""
        exc = AuthenticationException(
            message="Token expired", error_code=ErrorCode.TOKEN_EXPIRED
        )

        assert exc.status_code == 401
        assert exc.error_code == ErrorCode.TOKEN_EXPIRED
        assert exc.message == "Token expired"
        assert "WWW-Authenticate" in exc.headers

    def test_authorization_exception(self):
        """Test AuthorizationException."""
        exc = AuthorizationException(
            message="Access denied", error_code=ErrorCode.FORBIDDEN
        )

        assert exc.status_code == 403
        assert exc.error_code == ErrorCode.FORBIDDEN

    def test_not_found_exception(self):
        """Test NotFoundException."""
        exc = NotFoundException(resource="User", resource_id="123")

        assert exc.status_code == 404
        assert "User" in exc.message
        assert "123" in exc.message

    def test_conflict_exception(self):
        """Test ConflictException."""
        exc = ConflictException(
            message="Email already exists", error_code=ErrorCode.DUPLICATE_ENTRY
        )

        assert exc.status_code == 409
        assert exc.error_code == ErrorCode.DUPLICATE_ENTRY
