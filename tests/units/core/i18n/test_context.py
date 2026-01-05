"""
Tests for locale context management.

Tests thread-safe context storage for current locale across request lifecycle.
"""

import pytest
from src.core.i18n.context import LocaleContext


class TestLocaleContext:
    """Test LocaleContext class."""

    def test_set_and_get_locale(self):
        """Test setting and getting locale."""
        # Arrange
        locale = "ja"

        # Act
        LocaleContext.set(locale)
        result = LocaleContext.get()

        # Assert
        assert result == locale

    def test_get_none_when_not_set(self):
        """Test getting None when locale not set."""
        # Arrange
        LocaleContext.clear()

        # Act
        result = LocaleContext.get()

        # Assert
        assert result is None

    def test_get_or_default_with_set_locale(self):
        """Test get_or_default returns set locale."""
        # Arrange
        locale = "ja"
        LocaleContext.set(locale)

        # Act
        result = LocaleContext.get_or_default("en")

        # Assert
        assert result == locale

    def test_get_or_default_without_set_locale(self):
        """Test get_or_default returns default when not set."""
        # Arrange
        LocaleContext.clear()
        default = "en"

        # Act
        result = LocaleContext.get_or_default(default)

        # Assert
        assert result == default

    def test_get_or_default_uses_en_by_default(self):
        """Test get_or_default uses 'en' as default."""
        # Arrange
        LocaleContext.clear()

        # Act
        result = LocaleContext.get_or_default()

        # Assert
        assert result == "en"

    def test_clear_locale(self):
        """Test clearing locale."""
        # Arrange
        LocaleContext.set("ja")

        # Act
        LocaleContext.clear()
        result = LocaleContext.get()

        # Assert
        assert result is None

    def test_overwrite_locale(self):
        """Test overwriting existing locale."""
        # Arrange
        LocaleContext.set("en")

        # Act
        LocaleContext.set("ja")
        result = LocaleContext.get()

        # Assert
        assert result == "ja"

    @pytest.mark.asyncio
    async def test_context_isolation_across_tasks(self):
        """Test that locale context is isolated across async tasks."""
        import asyncio

        # Arrange
        results = []

        async def task_with_locale(locale: str):
            LocaleContext.set(locale)
            await asyncio.sleep(0.01)  # Simulate async work
            results.append(LocaleContext.get())

        # Act
        await asyncio.gather(
            task_with_locale("en"),
            task_with_locale("ja"),
        )

        # Assert
        assert "en" in results
        assert "ja" in results
        assert len(results) == 2
