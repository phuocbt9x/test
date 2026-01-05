"""
Locale Detection Middleware

Automatically detects and sets locale for each request from headers.
Optimized with caching and security hardening.
"""

import logging
import re
from functools import lru_cache
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.i18n.context import LocaleContext
from src.core.i18n.manager import LocaleManager

logger = logging.getLogger(__name__)

LOCALE_PATTERN = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
MAX_HEADER_SIZE = 1024


class LocaleMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic locale detection from multiple sources.

    Features:
    - Automatic locale detection from headers, query params, and cookies
    - Request lifecycle context management
    - Performance optimized with caching
    - Security hardening against injection attacks

    Detects locale from (in order of priority):
    1. X-Locale header (highest priority)
    2. Query parameter (locale or lang)
    3. Cookie
    4. Accept-Language header
    5. Default locale (fallback)
    """

    def __init__(
        self,
        app,
        default_locale: str = "en",
        locale_header: str = "X-Locale",
        query_param_names: Optional[list[str]] = None,
        cookie_name: str = "locale",
        accept_language: bool = True,
        max_header_size: int = MAX_HEADER_SIZE,
    ):
        """
        Initialize locale middleware.

        Args:
            app: FastAPI application
            default_locale: Default language code
            locale_header: Custom header name for locale (default: X-Locale)
            query_param_names: List of query param names to check (default: ["locale", "lang"])
            cookie_name: Cookie name for locale (default: "locale")
            accept_language: Whether to parse Accept-Language header
            max_header_size: Max header size in bytes (DoS protection)
        """
        super().__init__(app)
        self.default_locale = self._validate_locale(default_locale)
        self.locale_header = locale_header
        self.query_param_names = query_param_names or ["locale", "lang"]
        self.cookie_name = cookie_name
        self.accept_language = accept_language
        self.max_header_size = max_header_size
        self.manager = LocaleManager()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request and set locale context.

        Performance:
        - Uses cached locale detection
        - Minimal memory overhead with context variables

        Security:
        - Validates locale against whitelist
        - Protects against header injection
        - Limits header size to prevent DoS

        Args:
            request: FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response with locale context maintained throughout
        """
        locale = self._detect_locale(request)

        # Set locale in context (available throughout request lifecycle)
        LocaleContext.set(locale)

        try:
            # Process request with locale context
            response = await call_next(request)

            # Add response header to inform client of used locale
            response.headers["Content-Language"] = locale

            return response

        finally:
            # Clean up context after request
            LocaleContext.clear()

    def _detect_locale(self, request: Request) -> str:
        """
        Detect locale from multiple sources with security validation.

        Security:
        - Validates locale format (only a-z, A-Z, hyphen)
        - Prevents header/param injection attacks
        - Limits header size

        Detection sources (priority order):
        1. X-Locale header
        2. Query parameters (locale, lang)
        3. Cookie
        4. Accept-Language header
        5. Default locale

        Args:
            request: FastAPI request

        Returns:
            Detected and validated locale code
        """
        # 1. Check custom locale header (highest priority)
        locale_header = request.headers.get(self.locale_header)
        if locale_header:
            # Security: Limit header size
            if len(locale_header) > 20:
                logger.warning(
                    f"Locale header too long ({len(locale_header)} chars), using default"
                )
            else:
                locale = self._sanitize_locale(locale_header)
                if locale and self.manager.is_supported(locale):
                    logger.debug(f"Locale from {self.locale_header} header: {locale}")
                    return locale
                elif locale:
                    logger.warning(
                        f"Unsupported locale '{locale}' from {self.locale_header} header"
                    )

        # 2. Check query parameters
        for param_name in self.query_param_names:
            query_locale = request.query_params.get(param_name)
            if query_locale:
                locale = self._sanitize_locale(query_locale)
                if locale and self.manager.is_supported(locale):
                    logger.debug(f"Locale from query param '{param_name}': {locale}")
                    return locale
                elif locale:
                    logger.warning(
                        f"Unsupported locale '{locale}' from query param '{param_name}'"
                    )

        # 3. Check cookie
        cookie_locale = request.cookies.get(self.cookie_name)
        if cookie_locale:
            locale = self._sanitize_locale(cookie_locale)
            if locale and self.manager.is_supported(locale):
                logger.debug(f"Locale from cookie '{self.cookie_name}': {locale}")
                return locale
            elif locale:
                logger.warning(
                    f"Unsupported locale '{locale}' from cookie '{self.cookie_name}'"
                )

        # 4. Parse Accept-Language header
        if self.accept_language:
            accept_language = request.headers.get("Accept-Language")
            if accept_language:
                # Security: Limit header size to prevent DoS
                if len(accept_language) <= self.max_header_size:
                    locale = self._parse_accept_language(accept_language)
                    if locale:
                        logger.debug(f"Locale from Accept-Language: {locale}")
                        return locale
                else:
                    logger.warning(
                        f"Accept-Language header too large ({len(accept_language)} bytes)"
                    )

        # 5. Use default locale
        return self.default_locale

    @staticmethod
    def _validate_locale(locale: str) -> str:
        """
        Validate locale format against security pattern.

        Security:
        - Only allows ISO 639-1 format (en, vi, en-US, etc.)
        - Prevents injection attacks

        Args:
            locale: Locale code to validate

        Returns:
            Validated locale code

        Raises:
            ValueError: If locale format is invalid
        """
        if not LOCALE_PATTERN.match(locale):
            raise ValueError(
                f"Invalid locale format: {locale}. "
                f"Must match pattern: {LOCALE_PATTERN.pattern}"
            )
        return locale

    @staticmethod
    def _sanitize_locale(locale: str) -> Optional[str]:
        """
        Sanitize and validate locale string.

        Security:
        - Strips whitespace
        - Validates format
        - Prevents injection

        Args:
            locale: Raw locale string from header

        Returns:
            Sanitized locale or None if invalid
        """
        try:
            # Strip whitespace
            locale = locale.strip()

            # Extract base locale (en-US -> en, en -> en)
            base_locale = locale.split("-")[0].lower()

            # Security: Validate format
            if not re.match(r"^[a-z]{2}$", base_locale):
                logger.warning(f"Invalid locale format: {locale}")
                return None

            return base_locale

        except Exception as e:
            logger.warning(f"Error sanitizing locale '{locale}': {e}")
            return None

    @lru_cache(maxsize=128)
    def _parse_accept_language(self, header: str) -> Optional[str]:
        """
        Parse Accept-Language header and return first supported locale.

        Performance:
        - Cached with LRU cache (128 entries)
        - Reduces parsing overhead for repeated values

        Security:
        - Validates each locale code
        - Protects against malformed headers

        Handles quality values and multiple locales:
            "en-US,en;q=0.9,vi;q=0.8" -> returns first supported

        Args:
            header: Accept-Language header value

        Returns:
            First supported locale or None
        """
        try:
            # Parse language preferences
            preferences = []

            for item in header.split(","):
                item = item.strip()
                if not item or len(item) > 50:  # Security: Skip oversized items
                    continue

                # Split locale and quality
                parts = item.split(";")
                locale_code = parts[0].strip()

                # Security: Validate locale format
                sanitized = self._sanitize_locale(locale_code)
                if not sanitized:
                    continue

                # Extract quality value (default 1.0)
                quality = 1.0
                if len(parts) > 1:
                    try:
                        q_part = parts[1].strip()
                        if q_part.startswith("q="):
                            quality = float(q_part[2:])
                            # Security: Validate quality range
                            quality = max(0.0, min(1.0, quality))
                    except (ValueError, IndexError):
                        pass

                preferences.append((sanitized, quality))

            # Sort by quality (highest first)
            preferences.sort(key=lambda x: x[1], reverse=True)

            # Return first supported locale
            for locale, _ in preferences:
                if self.manager.is_supported(locale):
                    return locale

        except Exception as e:
            logger.warning(f"Failed to parse Accept-Language header: {e}")

        return None


def setup_locale_middleware(
    app,
    default_locale: str = "en",
    locale_header: str = "X-Locale",
    query_param_names: Optional[list[str]] = None,
    cookie_name: str = "locale",
    accept_language: bool = True,
    max_header_size: int = MAX_HEADER_SIZE,
) -> None:
    """
    Setup locale middleware for FastAPI application.

    Usage in main.py:
        from src.core.middlewares.locale import setup_locale_middleware

        setup_locale_middleware(
            app,
            default_locale="en",
            locale_header="X-Locale",
            query_param_names=["locale", "lang"],
            cookie_name="locale",
            accept_language=True,
            max_header_size=1024  # DoS protection
        )

    Detection sources (priority order):
    1. X-Locale header
    2. Query parameters (locale, lang)
    3. Cookie
    4. Accept-Language header
    5. Default locale

    Args:
        app: FastAPI application
        default_locale: Default language code
        locale_header: Custom header name for locale
        query_param_names: List of query param names to check
        cookie_name: Cookie name for locale
        accept_language: Whether to parse Accept-Language header
        max_header_size: Max header size in bytes (DoS protection)
    """
    if query_param_names is None:
        query_param_names = ["locale", "lang"]

    app.add_middleware(
        LocaleMiddleware,
        default_locale=default_locale,
        locale_header=locale_header,
        query_param_names=query_param_names,
        cookie_name=cookie_name,
        accept_language=accept_language,
        max_header_size=max_header_size,
    )
    logger.info(
        f"Locale middleware initialized (default: {default_locale}, "
        f"header: {locale_header}, query_params: {query_param_names}, "
        f"cookie: {cookie_name}, max_size: {max_header_size})"
    )
