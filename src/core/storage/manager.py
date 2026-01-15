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
                base_url=kwargs.get("base_url", settings.STORAGE_LOCAL_BASE_URL),
            )
        elif provider == "s3":
            cls._instance = StorageProviderFactory.create_provider(
                provider_name=provider,
                bucket_name=kwargs.get("bucket_name", settings.STORAGE_S3_BUCKET_NAME),
                region_name=kwargs.get("region_name", settings.STORAGE_S3_REGION),
                access_key_id=kwargs.get(
                    "access_key_id", settings.STORAGE_S3_ACCESS_KEY_ID
                ),
                secret_access_key=kwargs.get(
                    "secret_access_key", settings.STORAGE_S3_SECRET_ACCESS_KEY
                ),
                endpoint_url=kwargs.get(
                    "endpoint_url", settings.STORAGE_S3_ENDPOINT_URL
                ),
                public_url=kwargs.get("public_url", settings.STORAGE_S3_PUBLIC_URL),
                acl=kwargs.get("acl", settings.STORAGE_S3_ACL),
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
