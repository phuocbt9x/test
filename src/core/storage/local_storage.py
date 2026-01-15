import asyncio
import aiofiles  # type: ignore[import-untyped]
import os
from pathlib import Path
from typing import Optional

from .base import BaseStorageProvider, UploadResult, DeleteResult


class LocalStorageProvider(BaseStorageProvider):
    def __init__(
        self,
        base_dir: str = "public",
        base_url: str = "http://localhost:8000",
    ):
        self.base_dir = Path(base_dir)
        self.base_url = base_url.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _validate_path(self, file_path: str) -> Path:
        full_path = (self.base_dir / file_path).resolve()
        base_resolved = self.base_dir.resolve()

        if not str(full_path).startswith(str(base_resolved)):
            raise ValueError("Invalid file path: directory traversal detected")

        return full_path

    async def upload(
        self,
        file_data: bytes,
        file_path: str,
        content_type: Optional[str] = None,
    ) -> UploadResult:
        try:
            full_path = self._validate_path(file_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(full_path, "wb") as f:
                await f.write(file_data)

            url = self.get_url(file_path)

            return UploadResult(
                success=True, url=url, path=file_path, size=len(file_data)
            )

        except Exception as e:
            return UploadResult(success=False, error=f"Upload failed: {str(e)}")

    async def download(self, file_path: str) -> Optional[bytes]:
        try:
            full_path = self._validate_path(file_path)

            if not full_path.exists():
                return None

            async with aiofiles.open(full_path, "rb") as f:
                return await f.read()

        except Exception:
            return None

    async def delete(self, file_path: str) -> DeleteResult:
        try:
            full_path = self._validate_path(file_path)

            if not full_path.exists():
                return DeleteResult(success=False, error="File not found")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, os.remove, full_path)

            try:
                full_path.parent.rmdir()
            except OSError:
                pass

            return DeleteResult(success=True)

        except Exception as e:
            return DeleteResult(success=False, error=f"Delete failed: {str(e)}")

    async def exists(self, file_path: str) -> bool:
        try:
            full_path = self._validate_path(file_path)
            return full_path.exists() and full_path.is_file()
        except ValueError:
            return False

    @staticmethod
    def url_for(file_path: str, base_url: Optional[str] = None) -> str:
        if base_url is None:
            from src.core.configs import settings

            base_url = settings.STORAGE_LOCAL_BASE_URL
        url_path = file_path.replace(os.sep, "/")
        base_url_clean = base_url.rstrip("/")
        return f"{base_url_clean}/{url_path}"

    def get_url(self, file_path: str) -> str:
        return self.url_for(file_path, self.base_url)

    def get_provider_name(self) -> str:
        return "local"
