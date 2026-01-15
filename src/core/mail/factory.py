from pathlib import Path
from typing import Optional, cast

from src.core.configs import settings

from .base import BaseMailProvider
from .fastapi_mail import FastApiMailProvider
from fastapi_mail import ConnectionConfig  # type: ignore[import-untyped]
from pydantic import SecretStr


class MailProviderFactory:
    _instance: Optional[BaseMailProvider] = None
    _current_provider: Optional[str] = None

    @classmethod
    def _validate_fastapi_mail_config(cls) -> None:
        if not settings.MAIL_FROM:
            raise ValueError("MAIL_FROM is required")
        if not settings.MAIL_SERVER:
            raise ValueError("MAIL_SERVER is required")
        if not settings.MAIL_PORT:
            raise ValueError("MAIL_PORT is required")
        if settings.MAIL_USE_CREDENTIALS:
            if not settings.MAIL_USERNAME:
                raise ValueError("MAIL_USERNAME is required")
            if not settings.MAIL_PASSWORD:
                raise ValueError("MAIL_PASSWORD is required")

    @classmethod
    def _create_fastapi_mail_provider(cls) -> BaseMailProvider:
        cls._validate_fastapi_mail_config()
        config = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME or "",
            MAIL_PASSWORD=SecretStr(settings.MAIL_PASSWORD or ""),
            MAIL_FROM=cast(str, settings.MAIL_FROM),
            MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
            MAIL_SERVER=cast(str, settings.MAIL_SERVER),
            MAIL_PORT=cast(int, settings.MAIL_PORT),
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=settings.MAIL_USE_CREDENTIALS,
            VALIDATE_CERTS=settings.MAIL_VALIDATE_CERTS,
            TEMPLATE_FOLDER=Path(settings.MAIL_TEMPLATE_FOLDER),
        )
        return FastApiMailProvider(config)

    @classmethod
    def create_provider(cls, provider_name: str | None = None) -> BaseMailProvider:
        name = provider_name or settings.MAIL_PROVIDER
        if cls._instance and cls._current_provider == name:
            return cls._instance

        if name == "fastapi-mail":
            cls._instance = cls._create_fastapi_mail_provider()
        else:
            raise ValueError(f"Unknown mail provider: {name}. Available: fastapi-mail")

        cls._current_provider = name
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        cls._current_provider = None
