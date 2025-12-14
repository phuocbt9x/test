"""Main entry point for the FastAPI application."""

import uvicorn

from src.core import settings, logging_settings
from src import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
        log_level=logging_settings.LOGGING_LEVEL.lower(),
    )
