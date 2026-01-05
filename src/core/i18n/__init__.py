"""
Internationalization (i18n) Support using Babel with JSON format

Provides multi-language support with Babel's powerful i18n features while
keeping simple JSON format for translation files.

Features:
- Babel's industry-standard i18n features
- Simple JSON format (no .po/.mo compilation needed)
- Date/time/number formatting per locale
- Pluralization support
- Context-aware translation following request lifecycle
- Security hardening (input validation, DoS protection)
- Thread-safe singleton pattern

Usage:
    from src.core.i18n import _, get_locale, get_babel_locale
    from src.core.i18n.manager import LocaleManager
    from src.core.middlewares.locale import setup_locale_middleware
    from babel.dates import format_datetime
    from babel.numbers import format_currency

    # Initialize translations
    locale_manager = LocaleManager()
    locale_manager.load_translations(
        translations_dir=Path("src/translations"),
        default_locale="en",
        fallback_locale="en",
        preload_all=True
    )

    # Setup middleware
    setup_locale_middleware(app, default_locale="en")

    # Translate messages
    message = _("validation.required", attribute="Email")

    # Format dates with Babel
    babel_locale = get_babel_locale()
    formatted_date = format_datetime(datetime.now(), locale=babel_locale)

    # Format currency
    price = format_currency(1000000, 'VND', locale=babel_locale)
"""

from .context import LocaleContext
from .manager import (
    LocaleManager,
    current_locale,
    get_babel_locale,
    get_locale,
    get_translations,
)
from .manager import translate as _

__all__ = [
    "LocaleManager",
    "LocaleContext",
    "get_locale",
    "current_locale",
    "get_translations",
    "get_babel_locale",
    "_",
]
