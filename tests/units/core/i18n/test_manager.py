"""
Tests for translation manager.

Tests LocaleManager, JSONTranslations, and translation functions.
"""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.i18n.manager import (
    LocaleManager,
    JSONTranslations,
    _,
    ngettext,
    get_locale,
    get_translations,
)
from src.core.i18n.context import LocaleContext


@pytest.fixture(autouse=True)
def reset_locale_manager():
    """Reset LocaleManager singleton before each test."""
    # Clear singleton instance
    LocaleManager._instance = None
    LocaleManager._translations = {}
    LocaleManager._supported_locales = set()
    LocaleManager._translations_dir = None
    LocaleContext.clear()
    yield
    # Cleanup after test
    LocaleContext.clear()


@pytest.fixture
def temp_translations_dir():
    """Create temporary directory with test translation files."""
    with TemporaryDirectory() as tmpdir:
        translations_dir = Path(tmpdir) / "translations"
        translations_dir.mkdir()

        # English translations (source language)
        en_data = {
            "validation": {
                "required": "%(attribute)s is required",
                "min": "%(attribute)s must be at least %(min)s characters",
            },
            "auth": {
                "failed": "Invalid credentials",
                "success": "Login successful",
            },
            "Hello World!": "Hello World!",
        }

        # Japanese translations
        ja_data = {
            "validation": {
                "required": "%(attribute)sは必須です",
                "min": "%(attribute)sは%(min)s文字以上である必要があります",
            },
            "auth": {
                "failed": "認証情報が無効です",
                "success": "ログイン成功",
            },
            "Hello World!": "こんにちは世界！",
        }

        # Write translation files
        with open(translations_dir / "en.json", "w", encoding="utf-8") as f:
            json.dump(en_data, f, ensure_ascii=False, indent=2)

        with open(translations_dir / "ja.json", "w", encoding="utf-8") as f:
            json.dump(ja_data, f, ensure_ascii=False, indent=2)

        yield translations_dir


class TestJSONTranslations:
    """Test JSONTranslations class."""

    def test_load_from_json_success(self, temp_translations_dir):
        """Test loading translations from JSON file."""
        # Arrange
        trans = JSONTranslations("en")
        json_path = temp_translations_dir / "en.json"

        # Act
        result = trans.load_from_json(json_path)

        # Assert
        assert result is True
        assert len(trans._catalog) > 0
        assert "validation.required" in trans._catalog

    def test_load_from_json_invalid_path(self):
        """Test loading from non-existent file."""
        # Arrange
        trans = JSONTranslations("en")
        json_path = Path("/nonexistent/path.json")

        # Act
        result = trans.load_from_json(json_path)

        # Assert
        assert result is False

    def test_gettext_with_dot_notation(self, temp_translations_dir):
        """Test translation with dot notation key."""
        # Arrange
        trans = JSONTranslations("ja")
        trans.load_from_json(temp_translations_dir / "ja.json")

        # Act
        result = trans.gettext("auth.failed")

        # Assert
        assert result == "認証情報が無効です"

    def test_gettext_with_source_text(self, temp_translations_dir):
        """Test translation with source text key (requires English catalog)."""
        # Arrange
        trans_en = JSONTranslations("en")
        trans_en.load_from_json(temp_translations_dir / "en.json")

        trans_ja = JSONTranslations("ja")
        trans_ja.load_from_json(temp_translations_dir / "ja.json", trans_en._catalog)

        # Act - use dot notation key
        result = trans_ja.gettext("validation.required")

        # Assert
        assert result == "%(attribute)sは必須です"

    def test_gettext_returns_key_when_not_found(self, temp_translations_dir):
        """Test that gettext returns key when translation not found."""
        # Arrange
        trans = JSONTranslations("en")
        trans.load_from_json(temp_translations_dir / "en.json")

        # Act
        result = trans.gettext("nonexistent.key")

        # Assert
        assert result == "nonexistent.key"

    def test_ngettext_singular(self, temp_translations_dir):
        """Test ngettext with singular form."""
        # Arrange
        trans = JSONTranslations("en")
        trans.load_from_json(temp_translations_dir / "en.json")

        # Act
        result = trans.ngettext("auth.success", "auth.failed", 1)

        # Assert
        assert result == "Login successful"

    def test_ngettext_plural(self, temp_translations_dir):
        """Test ngettext with plural form."""
        # Arrange
        trans = JSONTranslations("en")
        trans.load_from_json(temp_translations_dir / "en.json")

        # Act
        result = trans.ngettext("auth.success", "auth.failed", 5)

        # Assert
        assert result == "Invalid credentials"


class TestLocaleManager:
    """Test LocaleManager class."""

    def test_singleton_pattern(self):
        """Test that LocaleManager is a singleton."""
        # Act
        manager1 = LocaleManager()
        manager2 = LocaleManager()

        # Assert
        assert manager1 is manager2

    def test_load_translations_success(self, temp_translations_dir):
        """Test loading translations successfully."""
        # Arrange
        manager = LocaleManager()

        # Act
        manager.load_translations(temp_translations_dir, preload_all=True)

        # Assert
        assert "en" in manager.supported_locales
        assert "ja" in manager.supported_locales
        assert manager.supported_locales == {"en", "ja"}
        assert manager.default_locale == "en"

    def test_load_translations_invalid_directory(self):
        """Test loading from invalid directory."""
        # Arrange
        manager = LocaleManager()

        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            manager.load_translations("/nonexistent/path")

    def test_is_supported_locale(self, temp_translations_dir):
        """Test checking if locale is supported."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir)

        # Act & Assert
        assert manager.is_supported("en") is True
        assert manager.is_supported("ja") is True
        assert manager.is_supported("vi") is False
        assert manager.is_supported("fr") is False

    def test_get_translations_for_locale(self, temp_translations_dir):
        """Test getting translations for specific locale."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir)

        # Act
        trans = manager.get_translations("ja")

        # Assert
        assert trans is not None
        assert trans.gettext("auth.failed") == "認証情報が無効です"

    def test_get_babel_locale(self, temp_translations_dir):
        """Test getting Babel locale object."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir)

        # Act
        locale = manager.get_babel_locale("en")

        # Assert
        assert locale is not None
        assert locale.language == "en"

    def test_reload_locale(self, temp_translations_dir):
        """Test reloading locale from disk."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir)

        # Act
        result = manager.reload_locale("ja")

        # Assert
        assert result is True


class TestTranslationFunctions:
    """Test translation helper functions."""

    def test_translate_with_dot_notation(self, temp_translations_dir):
        """Test _() function with dot notation."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir)
        LocaleContext.set("ja")

        # Act
        result = _("auth.failed")

        # Assert
        assert result == "認証情報が無効です"

    def test_translate_with_source_text(self, temp_translations_dir):
        """Test _() function with dot notation keys."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir)
        LocaleContext.set("ja")

        # Act
        result = _("validation.required", attribute="メール")

        # Assert
        assert result == "メールは必須です"

    def test_translate_with_placeholders(self, temp_translations_dir):
        """Test translation with placeholder formatting."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir)
        LocaleContext.set("ja")

        # Act
        result = _("validation.min", attribute="パスワード", min=8)

        # Assert
        assert result == "パスワードは8文字以上である必要があります"

    def test_translate_fallback_to_english(self, temp_translations_dir):
        """Test fallback to English when translation not found."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir, default_locale="en")
        LocaleContext.set("fr")  # Unsupported locale

        # Act
        result = _("auth.success")

        # Assert - falls back to English
        assert result == "Login successful"

    def test_ngettext_function(self, temp_translations_dir):
        """Test ngettext() function."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir, default_locale="en")
        LocaleContext.set("en")

        # Act
        singular = ngettext("auth.success", "auth.failed", 1)
        plural = ngettext("auth.success", "auth.failed", 5)

        # Assert
        assert singular == "Login successful"
        assert plural == "Invalid credentials"

    def test_get_locale_function(self, temp_translations_dir):
        """Test get_locale() function."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir)
        LocaleContext.set("ja")

        # Act
        result = get_locale()

        # Assert
        assert result == "ja"

    def test_get_translations_function(self, temp_translations_dir):
        """Test get_translations() function."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir, default_locale="en")

        # Act
        trans = get_translations("ja")

        # Assert
        assert trans is not None
        assert trans.gettext("auth.success") == "ログイン成功"

    def test_translate_japanese(self, temp_translations_dir):
        """Test translation to Japanese."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir)
        LocaleContext.set("ja")

        # Act
        result = _("validation.required", attribute="メール")

        # Assert
        assert result == "メールは必須です"

    def test_translate_returns_key_when_format_error(self, temp_translations_dir):
        """Test that translation returns formatted string even with missing placeholders."""
        # Arrange
        manager = LocaleManager()
        manager.load_translations(temp_translations_dir)
        LocaleContext.set("en")

        # Act - Missing 'min' placeholder
        result = _("validation.min", attribute="Password")

        # Assert - Should return the template without crashing
        assert "%(min)s" in result or result == "validation.min"
