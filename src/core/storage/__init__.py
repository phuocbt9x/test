"""
Storage Providers

Strategy pattern implementation for file storage.
Supports local filesystem, AWS S3, and S3-compatible services.
"""

from .base import BaseStorageProvider, UploadResult, DeleteResult
from .local_storage import LocalStorageProvider
from .s3_storage import S3StorageProvider
from .factory import StorageProviderFactory
from .manager import StorageManager, storage_manager
from .utils import extract_path_from_url, sanitize_filename, get_file_url

__all__ = [
    "BaseStorageProvider",
    "UploadResult",
    "DeleteResult",
    "LocalStorageProvider",
    "S3StorageProvider",
    "StorageProviderFactory",
    "StorageManager",
    "storage_manager",
    "extract_path_from_url",
    "sanitize_filename",
    "get_file_url",
]
