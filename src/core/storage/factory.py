from typing import Optional
from .base import BaseStorageProvider
from .local_storage import LocalStorageProvider


class StorageProviderFactory:
    _instance: Optional[BaseStorageProvider] = None
    _current_provider: Optional[str] = None

    @classmethod
    def create_provider(
        cls, provider_name: str = "local", **kwargs
    ) -> BaseStorageProvider:
        if cls._instance and cls._current_provider == provider_name:
            return cls._instance

        if provider_name == "local":
            cls._instance = LocalStorageProvider(
                base_dir=kwargs.get("base_dir", "public"),
                base_url=kwargs.get("base_url", "http://localhost:8000"),
            )
        else:
            raise ValueError(
                f"Unknown storage provider: {provider_name}. Available: local, s3"
            )

        cls._current_provider = provider_name
        return cls._instance

    @classmethod
    def get_available_providers(cls) -> list[str]:
        return ["local"]

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        cls._current_provider = None
