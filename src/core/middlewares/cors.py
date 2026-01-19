from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core import settings


def setup_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS.split(","),
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS.split(","),
        allow_headers=settings.CORS_HEADERS.split(","),
        expose_headers=["X-Request-ID", "X-Response-Time"],
        max_age=600,
    )
