from fastapi import FastAPI
from .logging import LoggingMiddleware
from .request_id import RequestIDMiddleware
from .cors import setup_cors
from .rate_limit import setup_rate_limit, limiter
from .security import setup_security_headers
from src.core.configs import settings, Environment


def setup_middlewares(app: FastAPI) -> None:
    """
    Setup middlewares in the correct execution order.

    Middleware execution order (LIFO - Last In First Out):
    - Added LAST executes FIRST on incoming requests
    - Added FIRST executes LAST on incoming requests

    Execution flow (request -> response):
    1. LoggingMiddleware (logs everything including errors)
    2. RequestIDMiddleware (adds tracking ID)
    3. CORS (handles cross-origin)
    4. SecurityHeaders (adds security headers)
    5. RateLimit (checks request limits)
    6. -> Your endpoint handler

    So we add in REVERSE order:
    """
    # Add middlewares in reverse order (LIFO)
    setup_rate_limit(app)  # 5th to execute (check limits early)
    if getattr(settings, "ENABLE_SECURITY_HEADERS", True):
        setup_security_headers(
            app, enable_hsts=(settings.APP_ENV == Environment.PRODUCTION)
        )  # 4th
    setup_cors(app)  # 3rd to execute
    app.add_middleware(RequestIDMiddleware)  # 2nd to execute
    app.add_middleware(LoggingMiddleware)  # 1st to execute (logs everything)


__all__ = [
    "LoggingMiddleware",
    "RequestIDMiddleware",
    "setup_cors",
    "setup_rate_limit",
    "setup_security_headers",
    "limiter",
    "setup_middlewares",
]
