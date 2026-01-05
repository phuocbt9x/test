"""
Translation Manager using source text as keys (Gettext-style)

Uses source language text (e.g., English) as translation keys.
Simple and intuitive: _("Hello World!") instead of _("greeting.hello")
Follows industry-standard Gettext patterns.
"""

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from babel import Locale as BabelLocale

from .context import LocaleContext

logger = logging.getLogger(__name__)


class JSONTranslations:
    """
    JSON-based translations supporting both approaches:
    1. Dot notation keys: _("validation.required")
    2. Source text keys: _("%(attribute)s is required")

    JSON format (nested, easy to organize):
    {
      "validation": {
        "required": "%(attribute)s is required",
        "min": "%(attribute)s must be at least %(min)s characters"
      },
      "auth": {
        "failed": "Invalid credentials"
      }
    }
    """

    def __init__(self, locale: str):
        """
        Initialize JSON-based translations.

        Args:
            locale: Locale code (e.g., 'en', 'vi', 'ja')
        """
        self._locale = locale
        self._catalog: Dict[str, str] = {}  # All keys (dot notation + source text)
        self._nested: Dict[str, Any] = {}  # Original nested structure

    def load_from_json(
        self, json_path: Path, english_catalog: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Load translations from JSON file.

        Supports nested structure and flattens to both:
        - Dot notation keys (validation.required)
        - Source text keys (if english_catalog provided)

        Args:
            json_path: Path to JSON translation file
            english_catalog: English source text catalog for source-text mapping
                           (only used for non-English locales)

        Returns:
            True if loaded successfully
        """
        try:
            # Security: Check file size (max 10MB)
            file_size = json_path.stat().st_size
            if file_size > 10 * 1024 * 1024:
                logger.error(f"JSON file too large ({file_size} bytes): {json_path}")
                return False

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                logger.error(f"Invalid JSON format (not a dict): {json_path}")
                return False

            self._nested = data

            # Flatten nested dict to catalog with dot notation
            self._catalog = self._flatten_dict(data)

            # If this is English, add self-mapping (text -> text)
            if self._locale == "en":
                for key, value in list(self._catalog.items()):
                    # Add mapping for the English text itself
                    if value and not value.startswith(key):
                        self._catalog[value] = value

            # If this is NOT English and we have English catalog,
            # add source-text to translation mapping
            elif english_catalog:
                # Create reverse mapping: English text -> dot key
                english_text_to_key = {}
                for key, value in english_catalog.items():
                    if (
                        not key.startswith("validation.")
                        and not key.startswith("auth.")
                        and "." not in key
                    ):
                        # This is a source text key (English text mapping)
                        english_text_to_key[value] = key

                # Now map English source text to Vietnamese translation
                for english_text, dot_key in english_text_to_key.items():
                    if dot_key in self._catalog:
                        # Map English source text to Vietnamese translation
                        self._catalog[english_text] = self._catalog[dot_key]

            logger.info(
                f"Loaded {len(self._catalog)} translations for '{self._locale}' "
                f"({file_size} bytes)"
            )
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {json_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load {json_path}: {e}")
            return False

    def _flatten_dict(
        self, nested_dict: Dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> Dict[str, str]:
        """
        Flatten nested dictionary to dot-notation keys.

        Example:
            {
              "validation": {
                "required": "%(attribute)s is required"
              }
            }
        becomes:
            {
              "validation.required": "%(attribute)s is required"
            }
        """
        items: list[tuple[str, str]] = []
        for key, value in nested_dict.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key, sep).items())
            else:
                items.append((new_key, str(value)))

        return dict(items)

    def gettext(self, message: str) -> str:
        """
        Get translation for message.

        Supports both:
        - Dot notation: "validation.required"
        - Source text: "%(attribute)s is required"

        If not found, returns the source message.
        """
        return self._catalog.get(message, message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        """
        Get plural form translation.
        Args:
            singular: Singular form
            plural: Plural form
            n: Count for plural selection
        """
        if n == 1:
            return self.gettext(singular)
        else:
            return self.gettext(plural)


class LocaleManager:
    """
    Translation manager using source text as keys (Gettext-style).

    Features:
    - Use source text directly as keys: _("Hello World!")
    - Simple flat JSON format
    - Python % formatting for placeholders
    - Date/time/number formatting via Babel
    - Thread-safe singleton
    - Auto-fallback to English if translation not found
    """

    _instance: Optional["LocaleManager"] = None
    _lock = Lock()
    _translations: Dict[str, JSONTranslations] = {}
    _default_locale: str = "en"
    _fallback_locale: str = "en"
    _supported_locales: set[str] = set()
    _translations_dir: Optional[Path] = None

    def __new__(cls):
        """Thread-safe singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize singleton."""
        if not hasattr(self, "_initialized"):
            self._initialized = True

    def load_translations(
        self,
        translations_dir: Path | str,
        default_locale: str = "en",
        fallback_locale: str = "en",
        preload_all: bool = True,
    ) -> None:
        """
        Load translation files from directory.

        Directory structure:
            src/translations/
                en.json
                vi.json
                ja.json

        File format (nested, easy to organize):
            {
              "validation": {
                "required": "%(attribute)s is required",
                "min": "%(attribute)s must be at least %(min)s characters"
              },
              "auth": {
                "failed": "Invalid credentials"
              }
            }

        Supports BOTH usage styles:
        - Dot notation: _("validation.required")
        - Source text: _("%(attribute)s is required")

        Args:
            translations_dir: Path to translations directory
            default_locale: Default language
            fallback_locale: Fallback language (usually 'en')
            preload_all: Preload all at startup (recommended)
        """
        translations_dir = Path(translations_dir)
        self._translations_dir = translations_dir
        self._default_locale = default_locale
        self._fallback_locale = fallback_locale

        if not translations_dir.exists():
            raise ValueError(f"Translations directory not found: {translations_dir}")

        # Discover locales
        self._discover_locales(translations_dir)

        # Load English first (if not already loaded)
        if default_locale != "en" and "en" in self._supported_locales:
            self._load_locale("en")

        # Preload
        if preload_all:
            for locale in list(self._supported_locales):
                self._load_locale(locale)
        else:
            self._load_locale(default_locale)
            if fallback_locale != default_locale:
                self._load_locale(fallback_locale)

        logger.info(
            f"LocaleManager initialized: "
            f"{len(self._supported_locales)} locales, supports both dot notation "
            f"and source text keys"
        )

    def _discover_locales(self, translations_dir: Path) -> None:
        """Discover available locale files."""
        self._supported_locales.clear()

        for locale_file in translations_dir.glob("*.json"):
            locale = locale_file.stem

            if self._is_valid_locale_code(locale):
                self._supported_locales.add(locale)

        logger.info(f"Discovered locales: {self._supported_locales}")

    @staticmethod
    def _is_valid_locale_code(locale: str) -> bool:
        """Validate locale code (2-5 lowercase letters)."""
        return locale.isalpha() and locale.islower() and 2 <= len(locale) <= 5

    def _load_locale(self, locale: str) -> bool:
        """Load translation file for locale."""
        if locale in self._translations:
            return True

        if not self._translations_dir:
            logger.error("Translations directory not set")
            return False

        locale_file = self._translations_dir / f"{locale}.json"

        if not locale_file.exists():
            logger.warning(f"Translation file not found: {locale_file}")
            return False

        try:
            translations = JSONTranslations(locale=locale)

            # If this is not English, pass English catalog for source-text mapping
            english_catalog = None
            if locale != "en" and "en" in self._translations:
                english_catalog = self._translations["en"]._catalog

            if not translations.load_from_json(locale_file, english_catalog):
                return False

            self._translations[locale] = translations
            return True

        except Exception as e:
            logger.error(f"Failed to load {locale_file}: {e}")
            return False

    def get_translations(self, locale: Optional[str] = None) -> JSONTranslations:
        """
        Get JSONTranslations object.

        Args:
            locale: Locale code (uses current context if None)

        Returns:
            JSONTranslations object
        """
        if locale is None:
            locale = LocaleContext.get_or_default(self._default_locale)

        if not self._is_valid_locale_code(locale):
            logger.warning(f"Invalid locale: {locale}")
            locale = self._default_locale

        if locale not in self._translations:
            self._load_locale(locale)

        if locale in self._translations:
            return self._translations[locale]

        # Fallback to default/fallback locale
        if self._fallback_locale in self._translations:
            return self._translations[self._fallback_locale]
        if self._default_locale in self._translations:
            return self._translations[self._default_locale]

        # Return empty translations that returns source text
        return JSONTranslations(locale)

    def is_supported(self, locale: str) -> bool:
        """Check if locale is supported."""
        return locale in self._supported_locales

    @property
    def supported_locales(self) -> set[str]:
        """Get supported locales."""
        return self._supported_locales.copy()

    @property
    def default_locale(self) -> str:
        """Get default locale."""
        return self._default_locale

    def get_babel_locale(self, locale: Optional[str] = None) -> BabelLocale:
        """
        Get Babel Locale object for date/number formatting.

        Args:
            locale: Locale code (uses current if None)

        Returns:
            Babel Locale object
        """
        if locale is None:
            locale = LocaleContext.get_or_default(self._default_locale)

        try:
            return BabelLocale.parse(locale)
        except Exception as e:
            logger.warning(f"Failed to parse locale '{locale}': {e}")
            return BabelLocale.parse(self._default_locale)

    def reload_locale(self, locale: str) -> bool:
        """Reload locale from disk."""
        if locale in self._translations:
            del self._translations[locale]
        return self._load_locale(locale)


# Singleton instance
_manager = LocaleManager()


def get_locale() -> str:
    """
    Get current request locale.

    Returns:
        Locale code (e.g., 'en', 'vi')
    """
    return LocaleContext.get_or_default(_manager.default_locale)


def current_locale() -> str:
    """Alias for get_locale()."""
    return get_locale()


def _(message: str, **kwargs: Any) -> str:
    """
    Translate message using flexible key system.

    Supports BOTH styles:
    1. Dot notation (organized by category):
       _("validation.required", attribute="Email")

    2. Source text (natural language):
       _("%(attribute)s is required", attribute="Email")

    Uses Python's % formatting for placeholders.
    If translation not found, returns the source message.

    Args:
        message: Translation key (dot notation or source text)
        **kwargs: Values for % formatting placeholders

    Returns:
        Translated string (or source if translation not found)

    Examples:
        # Dot notation style
        >>> _("validation.required", attribute="Email")
        'Email is required'  # English

        # Source text style
        >>> _("%(attribute)s is required", attribute="Email")
        'Email is required'  # English

        # Auth messages
        >>> _("auth.failed")
        'Invalid credentials'

        # Nested categories
        >>> _("auth.token_expired")
        'Your session has expired. Please log in again'
    """
    trans = _manager.get_translations()
    message_str = trans.gettext(message)

    # Format with % if kwargs provided
    if kwargs:
        try:
            return message_str % kwargs
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Format error for '{message}': {e}")
            return message_str

    return message_str


def ngettext(singular: str, plural: str, n: int, **kwargs: Any) -> str:
    """
    Get plural form translation using source text as keys.

    Args:
        singular: Singular form source text
        plural: Plural form source text
        n: Count for plural selection
        **kwargs: Values for % formatting

    Returns:
        Translated string in correct plural form

    Examples:
        # JSON (vi.json):
        # "You have 1 item": "Bạn có 1 mục",
        # "You have %(count)s items": "Bạn có %(count)s mục"

        >>> ngettext("You have 1 item", "You have %(count)s items", 1, count=1)
        'Bạn có 1 mục'

        >>> ngettext("You have 1 item", "You have %(count)s items", 5, count=5)
        'Bạn có 5 mục'
    """
    trans = _manager.get_translations()
    message_str = trans.ngettext(singular, plural, n)

    if kwargs:
        try:
            return message_str % kwargs
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Format error: {e}")
            return message_str

    return message_str


def get_translations(locale: Optional[str] = None) -> JSONTranslations:
    """
    Get JSONTranslations object for advanced usage.

    Args:
        locale: Locale code

    Returns:
        JSONTranslations object
    """
    return _manager.get_translations(locale)


def get_babel_locale(locale: Optional[str] = None) -> BabelLocale:
    """
    Get Babel Locale object for date/number formatting.

    Args:
        locale: Locale code

    Returns:
        Babel Locale object

    Example:
        >>> from babel.dates import format_datetime
        >>> from src.core.i18n import get_babel_locale
        >>>
        >>> locale = get_babel_locale()
        >>> format_datetime(datetime.now(), locale=locale)
        '31 December 2025'
    """
    return _manager.get_babel_locale(locale)


# Alias for backward compatibility
translate = _
