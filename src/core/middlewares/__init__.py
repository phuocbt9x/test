from fastapi import FastAPI
from pathlib import Path
from .logging import LoggingMiddleware
from .request_id import RequestIDMiddleware
from .cors import setup_cors
from .rate_limit import setup_rate_limit, limiter
from .security import setup_security_headers
from .locale import setup_locale_middleware
from src.core.configs import settings, Environment
from src.core.i18n.manager import LocaleManager


def setup_middlewares(app: FastAPI) -> None:
    import logging

    logger = logging.getLogger(__name__)
    """
    Setup middlewares in the correct execution order.

    Middleware execution order (LIFO - Last In First Out):
    - Added LAST executes FIRST on incoming requests
    - Added FIRST executes LAST on incoming requests

    Execution flow (request -> response):
    1. LocaleMiddleware (detects locale from headers - must be first for i18n)
    2. LoggingMiddleware (logs everything including errors)
    3. RequestIDMiddleware (adds tracking ID)
    4. CORS (handles cross-origin)
    5. SecurityHeaders (adds security headers)
    6. RateLimit (checks request limits)
    7. -> Your endpoint handler

    So we add in REVERSE order:
    """
    # Initialize LocaleManager and load translations

    default_locale = "en"
    try:
        translations_dir = Path("src/translations")
        locale_manager = LocaleManager()
        locale_manager.load_translations(
            translations_dir=translations_dir,
            default_locale=default_locale,
            fallback_locale="en",
            preload_all=True,
        )
    except Exception as e:
        logger.warning(
            f"Failed to load translations: {e}. Continuing with English defaults."
        )

    # Add middlewares in reverse order (LIFO)
    setup_rate_limit(app)  # 5th to execute (check limits early)
    if getattr(settings, "ENABLE_SECURITY_HEADERS", True):
        setup_security_headers(
            app, enable_hsts=(settings.APP_ENV == Environment.PRODUCTION)
        )  # 5th
    setup_cors(app)  # 4th to execute
    app.add_middleware(RequestIDMiddleware)  # 3rd to execute
    app.add_middleware(LoggingMiddleware)  # 2nd to execute (logs everything)
    setup_locale_middleware(
        app,
        default_locale=default_locale,
        locale_header="X-Locale",
        accept_language=True,
    )


__all__ = [
    "LoggingMiddleware",
    "RequestIDMiddleware",
    "setup_cors",
    "setup_rate_limit",
    "setup_security_headers",
    "setup_locale_middleware",
    "limiter",
    "setup_middlewares",
]
