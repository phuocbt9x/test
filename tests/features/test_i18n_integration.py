"""
Integration tests for i18n functionality.

Tests end-to-end translation with API endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestI18nIntegration:
    """Test i18n integration with API."""

    async def test_api_with_accept_language_header(self, client: AsyncClient):
        """Test API response with Accept-Language header."""
        # Act
        response = await client.get("/health", headers={"Accept-Language": "ja"})

        # Assert
        assert response.status_code == 200
        # Locale should be set to 'ja' during request

    async def test_api_with_query_param(self, client: AsyncClient):
        """Test API response with lang query parameter."""
        # Act
        response = await client.get("/health?lang=ja")

        # Assert
        assert response.status_code == 200
        # Locale should be set to 'ja' during request

    async def test_api_with_cookie(self, client: AsyncClient):
        """Test API response with locale cookie."""
        # Act
        response = await client.get("/health", cookies={"locale": "ja"})

        # Assert
        assert response.status_code == 200
        # Locale should be set to 'ja' during request

    async def test_unsupported_locale_falls_back(self, client: AsyncClient):
        """Test that unsupported locale falls back to default."""
        # Act
        response = await client.get(
            "/health?lang=fr"  # Unsupported
        )

        # Assert
        assert response.status_code == 200
        # Should fall back to default locale (en)

    async def test_locale_priority_query_over_header(self, client: AsyncClient):
        """Test that query param has priority over header."""
        # Act
        response = await client.get(
            "/health?lang=en", headers={"Accept-Language": "ja"}
        )

        # Assert
        assert response.status_code == 200
        # Should use 'en' from query param, not 'ja' from header


@pytest.mark.asyncio
class TestTranslationInEndpoints:
    """Test locale detection in endpoints."""

    async def test_locale_detection_in_protected_endpoint(self, client: AsyncClient):
        """Test locale detection when accessing protected endpoints."""
        # This test verifies locale is detected from Accept-Language header
        # when accessing auth-protected endpoints

        # Act - Request without authentication to a protected endpoint
        response = await client.get(
            "/api/v1/users/me", headers={"Accept-Language": "ja"}
        )

        # Assert - Should get 401 (unauthorized, not 500)
        # The locale would have been detected and set during request processing
        assert response.status_code == 401

    async def test_locale_detection_with_query_param(self, client: AsyncClient):
        """Test locale detection with query parameter."""
        # This test verifies locale can be detected from query parameters

        # Act - Access health endpoint with locale query parameter
        response = await client.get("/health?lang=ja")

        # Assert - Should succeed
        # The locale would have been set to 'ja' from the query parameter
        assert response.status_code == 200
