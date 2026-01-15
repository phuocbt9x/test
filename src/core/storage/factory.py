from typing import Optional
from .base import BaseStorageProvider
from .local_storage import LocalStorageProvider
from .s3_storage import S3PerformanceConfig, S3StorageProvider


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
        elif provider_name == "s3":
            bucket_name = kwargs.get("bucket_name")
            if not bucket_name or not isinstance(bucket_name, str):
                raise ValueError("bucket_name is required for S3 storage provider")
            cls._instance = S3StorageProvider(
                bucket_name=bucket_name,
                region_name=kwargs.get("region_name", "us-east-1"),
                access_key_id=kwargs.get("access_key_id"),
                secret_access_key=kwargs.get("secret_access_key"),
                endpoint_url=kwargs.get("endpoint_url"),
                public_url=kwargs.get("public_url"),
                acl=kwargs.get("acl", "private"),
                performance=S3PerformanceConfig(
                    compress=kwargs.get("compress", False),
                    compress_min_size=kwargs.get("compress_min_size", 1024),
                    compress_max_size=kwargs.get("compress_max_size", 5 * 1024 * 1024),
                    compress_content_types=kwargs.get("compress_content_types"),
                    multipart_threshold=kwargs.get(
                        "multipart_threshold", 8 * 1024 * 1024
                    ),
                    multipart_chunk_size=kwargs.get(
                        "multipart_chunk_size", 8 * 1024 * 1024
                    ),
                    max_pool_connections=kwargs.get("max_pool_connections", 20),
                    retry_max_attempts=kwargs.get("retry_max_attempts", 5),
                    retry_base_delay=kwargs.get("retry_base_delay", 0.2),
                    retry_max_delay=kwargs.get("retry_max_delay", 2.0),
                ),
            )
        else:
            raise ValueError(
                f"Unknown storage provider: {provider_name}. Available: local, s3"
            )

        cls._current_provider = provider_name
        return cls._instance

    @classmethod
    def get_available_providers(cls) -> list[str]:
        return ["local", "s3"]

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        cls._current_provider = None
