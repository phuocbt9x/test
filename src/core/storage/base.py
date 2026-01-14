from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class UploadResult:
    success: bool
    url: Optional[str] = None
    path: Optional[str] = None
    error: Optional[str] = None
    size: Optional[int] = None


@dataclass
class DeleteResult:
    success: bool
    error: Optional[str] = None


class BaseStorageProvider(ABC):
    @abstractmethod
    async def upload(
        self,
        file_data: bytes,
        file_path: str,
        content_type: Optional[str] = None,
    ) -> UploadResult:
        pass

    @abstractmethod
    async def download(self, file_path: str) -> Optional[bytes]:
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> DeleteResult:
        pass

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        pass

    @abstractmethod
    def get_url(self, file_path: str) -> str:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass
