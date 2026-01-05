"""
Locale Context Management

Thread-safe context storage for current locale across request lifecycle.
"""

from contextvars import ContextVar
from typing import Optional

# Context variable for storing current locale
# This persists across async operations within the same request
_locale_context: ContextVar[Optional[str]] = ContextVar("locale", default=None)


class LocaleContext:
    """
    Manage locale context for current request.

    Uses contextvars for async-safe storage that follows request lifecycle.
    """

    @staticmethod
    def set(locale: str) -> None:
        """
        Set locale for current request context.

        Args:
            locale: Language code (e.g., 'en', , 'ja')
        """
        _locale_context.set(locale)

    @staticmethod
    def get() -> Optional[str]:
        """
        Get locale from current request context.

        Returns:
            Current locale code or None if not set
        """
        return _locale_context.get()

    @staticmethod
    def clear() -> None:
        """Clear locale from current context."""
        _locale_context.set(None)

    @staticmethod
    def get_or_default(default: str = "en") -> str:
        """
        Get locale or return default.

        Args:
            default: Default locale if not set (default: 'en')

        Returns:
            Current locale or default
        """
        locale = _locale_context.get()
        return locale if locale else default
