from typing import Optional

from src.core.configs import settings

from .base import BaseMailProvider, MailMessage
from .factory import MailProviderFactory


class MailManager:
    _instance: Optional[BaseMailProvider] = None
    _initialized: bool = False

    @classmethod
    def initialize(cls, provider_name: str | None = None) -> None:
        if cls._initialized:
            return
        provider = provider_name or settings.MAIL_PROVIDER
        cls._instance = MailProviderFactory.create_provider(provider)
        cls._initialized = True

    @classmethod
    def get_instance(cls) -> BaseMailProvider:
        if not cls._initialized or cls._instance is None:
            raise RuntimeError(
                "MailManager not initialized. Call MailManager.initialize() at startup."
            )
        return cls._instance

    @classmethod
    async def send(cls, message: MailMessage) -> None:
        provider = cls.get_instance()
        await provider.send(message)

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        cls._initialized = False


mail_manager = MailManager
