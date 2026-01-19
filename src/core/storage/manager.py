from typing import Optional
from src.core.configs import settings
from .base import BaseStorageProvider
from .factory import StorageProviderFactory


class StorageManager:
    _instance: Optional[BaseStorageProvider] = None
    _initialized: bool = False

    @classmethod
    def initialize(
        cls,
        provider_name: str | None = None,
        **kwargs,
    ) -> None:
        if cls._initialized:
            return

        provider = provider_name or settings.STORAGE_PROVIDER

        if provider == "local":
            cls._instance = StorageProviderFactory.create_provider(
                provider_name=provider,
                base_dir=kwargs.get("base_dir", settings.STORAGE_LOCAL_BASE_DIR),
                base_url=kwargs.get(
                    "base_url", f"{settings.APP_HOST}:{settings.APP_PORT}"
                ),
            )
        else:
            raise ValueError(f"Unknown storage provider: {provider}")

        cls._initialized = True

    @classmethod
    def get_instance(cls) -> BaseStorageProvider:
        if not cls._initialized or cls._instance is None:
            raise RuntimeError(
                "StorageManager not initialized. "
                "Call StorageManager.initialize() at application startup."
            )
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        cls._initialized = False


storage_manager = StorageManager
