from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, BinaryIO, List, Optional, Union
from fastapi import UploadFile


@dataclass
class UploadResult:
    success: bool
    path: Optional[str] = None
    size: Optional[int] = None
    error: Optional[str] = None


@dataclass
class DeleteResult:
    success: bool
    error: Optional[str] = None


@dataclass
class CopyResult:
    success: bool
    path: Optional[str] = None
    size: Optional[int] = None
    error: Optional[str] = None


@dataclass
class FileMetadata:
    path: str
    size: int
    content_type: Optional[str] = None
    last_modified: Optional[datetime] = None
    etag: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass
class FileInfo:
    path: str
    size: int
    is_directory: bool = False
    last_modified: Optional[datetime] = None


class BaseStorageProvider(ABC):
    @abstractmethod
    async def save(
        self,
        file_data: bytes,
        path: str,
        content_type: Optional[str] = None,
    ) -> UploadResult:
        pass

    @abstractmethod
    async def save_file(
        self,
        file: Union[UploadFile, BinaryIO],
        path: str,
        content_type: Optional[str] = None,
    ) -> UploadResult:
        pass

    @abstractmethod
    async def read(self, path: str) -> Optional[bytes]:
        pass

    @abstractmethod
    async def delete(self, path: str) -> DeleteResult:
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        pass

    @abstractmethod
    def get_url(self, path: str) -> str:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    async def copy(self, source: str, destination: str) -> CopyResult:
        file_data = await self.read(source)
        if file_data is None:
            return CopyResult(success=False, error="Source file not found")

        metadata = await self.get_metadata(source)
        content_type = metadata.content_type if metadata else None

        result = await self.save(file_data, destination, content_type)
        return CopyResult(
            success=result.success,
            path=result.path,
            size=result.size,
            error=result.error,
        )

    async def move(self, source: str, destination: str) -> CopyResult:
        result = await self.copy(source, destination)
        if result.success:
            await self.delete(source)
        return result

    async def get_metadata(self, path: str) -> Optional[FileMetadata]:
        _ = path
        return None

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
    ) -> List[FileInfo]:
        _ = prefix
        _ = limit
        return []

    async def read_stream(
        self,
        path: str,
        chunk_size: int = 1024 * 1024,
    ) -> Optional[AsyncIterator[bytes]]:
        _ = path
        _ = chunk_size
        return None

    def generate_signed_url(
        self,
        path: str,
        expires_in: int = 3600,
        method: str = "GET",
    ) -> Optional[str]:
        _ = path
        _ = expires_in
        _ = method
        return None
