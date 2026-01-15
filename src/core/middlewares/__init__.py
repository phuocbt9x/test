from fastapi import FastAPI
from .logging import LoggingMiddleware
from .request_id import RequestIDMiddleware
from .cors import setup_cors
from .rate_limit import setup_rate_limit, limiter
from .security import setup_security_headers
from .locale import LanguageMiddleware
from src.core.configs import settings, Environment


def setup_middlewares(app: FastAPI) -> None:
    app.add_middleware(LanguageMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    setup_cors(app)
    setup_rate_limit(app)
    if getattr(settings, "ENABLE_SECURITY_HEADERS", True):
        setup_security_headers(
            app, enable_hsts=(settings.APP_ENV == Environment.PRODUCTION)
        )


__all__ = [
    "LoggingMiddleware",
    "RequestIDMiddleware",
    "setup_cors",
    "setup_rate_limit",
    "setup_security_headers",
    "limiter",
    "setup_middlewares",
]
