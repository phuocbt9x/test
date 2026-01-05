"""
Tests for locale detection middleware.

Tests Accept-Language header parsing and locale detection.
"""

import pytest
from unittest.mock import Mock
from fastapi import Request

from src.core.middlewares.locale import LocaleMiddleware
from src.core.i18n.context import LocaleContext


class TestLocaleMiddleware:
    """Test LocaleMiddleware functionality."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = Mock()
        return LocaleMiddleware(app, default_locale="en")

    def test_validate_locale_valid(self, middleware):
        """Test valid locale validation."""
        assert middleware._validate_locale("en") == "en"
        assert middleware._validate_locale("ja") == "ja"

    def test_validate_locale_invalid(self, middleware):
        """Test invalid locale validation raises ValueError."""
        # Should raise ValueError for invalid inputs
        with pytest.raises(ValueError):
            middleware._validate_locale("invalid123")

        with pytest.raises(ValueError):
            middleware._validate_locale("../../../etc/passwd")

        with pytest.raises(ValueError):
            middleware._validate_locale("en<script>")

    def test_detect_locale_from_header(self, middleware):
        """Test locale detection from X-Locale header."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Locale": "ja"}
        request.query_params = {}
        request.cookies = {}

        # Act
        locale = middleware._detect_locale(request)

        # Assert
        assert locale == "ja"

    def test_detect_locale_from_accept_language(self, middleware):
        """Test locale detection from Accept-Language header."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"Accept-Language": "ja,en;q=0.9"}
        request.query_params = {}
        request.cookies = {}

        # Act
        locale = middleware._detect_locale(request)

        # Assert
        assert locale == "ja"

    def test_detect_locale_default(self, middleware):
        """Test default locale when no headers present."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.query_params = {}
        request.cookies = {}

        # Act
        locale = middleware._detect_locale(request)

        # Assert
        assert locale == "en"

    @pytest.mark.asyncio
    async def test_dispatch_sets_locale_context(self, middleware):
        """Test that dispatch sets locale in context."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Locale": "ja"}
        request.query_params = {}
        request.cookies = {}

        response = Mock()
        response.headers = {}

        async def call_next(req):
            # Check locale is set during request processing
            assert LocaleContext.get() == "ja"
            return response

        # Act
        result = await middleware.dispatch(request, call_next)

        # Assert
        assert result == response
        assert result.headers.get("Content-Language") == "ja"

    def test_header_size_protection(self, middleware):
        """Test protection against oversized headers."""
        # Arrange
        large_header = "en," + ",".join(["xx"] * 1000)
        request = Mock(spec=Request)
        request.headers = {"Accept-Language": large_header}
        request.query_params = {}
        request.cookies = {}

        # Act
        locale = middleware._detect_locale(request)

        # Assert - should return default due to size limit
        assert locale == "en"

    def test_parse_accept_language_simple(self, middleware):
        """Test parsing simple Accept-Language header."""
        # Act
        locale = middleware._parse_accept_language("en")

        # Assert
        assert locale == "en"

    def test_parse_accept_language_with_quality(self, middleware):
        """Test parsing Accept-Language with quality values."""
        # Act
        locale = middleware._parse_accept_language("ja;q=0.9,en;q=0.8")

        # Assert
        assert locale == "ja"

    def test_parse_accept_language_empty(self, middleware):
        """Test parsing empty Accept-Language header."""
        # Act
        locale = middleware._parse_accept_language("")

        # Assert
        assert locale is None

    def test_security_injection_attempt(self, middleware):
        """Test protection against injection attacks."""
        # Arrange
        malicious_locales = [
            "../../../etc/passwd",
            "en<script>alert('xss')</script>",
            "en; DROP TABLE users;",
        ]

        for malicious in malicious_locales:
            request = Mock(spec=Request)
            request.headers = {"X-Locale": malicious}
            request.query_params = {}
            request.cookies = {}

            # Act
            locale = middleware._detect_locale(request)

            # Assert - should return default locale
            assert locale == "en", f"Failed to sanitize: {malicious}"
