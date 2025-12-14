from fastapi import FastAPI
from .logging import LoggingMiddleware
from .request_id import RequestIDMiddleware
from .cors import setup_cors
from .rate_limit import setup_rate_limit, limiter

def setup_middlewares(app: FastAPI) -> None:
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    setup_cors(app)
    setup_rate_limit(app)

__all__ = [
    "LoggingMiddleware",
    "RequestIDMiddleware",
    "setup_cors",
    "setup_rate_limit",
    "limiter",
    "setup_middlewares",
]