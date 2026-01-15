import asyncio
import inspect
import mimetypes
import os
import shutil

import aiofiles  # type: ignore[import-untyped]

from pathlib import Path
from typing import AsyncIterator, BinaryIO, List, Optional, Union
from fastapi import UploadFile
from src.core.utils import timestamp_to_datetime
from .base import (
    BaseStorageProvider,
    CopyResult,
    DeleteResult,
    FileInfo,
    FileMetadata,
    UploadResult,
)

DEFAULT_CHUNK_SIZE = 1024 * 1024


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

    async def save(
        self,
        file_data: bytes,
        path: str,
        content_type: Optional[str] = None,
    ) -> UploadResult:
        try:
            full_path = self._validate_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(full_path, "wb") as f:
                await f.write(file_data)

            return UploadResult(
                success=True,
                path=path,
                size=len(file_data),
            )
        except Exception as e:
            return UploadResult(success=False, error=str(e))

    async def save_file(
        self,
        file: Union[UploadFile, BinaryIO],
        path: str,
        content_type: Optional[str] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> UploadResult:
        try:
            full_path = self._validate_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)

            total_size = 0
            async with aiofiles.open(full_path, "wb") as f:
                if isinstance(file, UploadFile):
                    while True:
                        chunk = await file.read(chunk_size)
                        if not chunk:
                            break
                        await f.write(chunk)
                        total_size += len(chunk)
                else:
                    while True:
                        if inspect.iscoroutinefunction(file.read):
                            chunk = await file.read(chunk_size)
                        else:
                            chunk = await asyncio.to_thread(file.read, chunk_size)
                        if not chunk:
                            break
                        await f.write(chunk)
                        total_size += len(chunk)

            return UploadResult(
                success=True,
                path=path,
                size=total_size,
            )
        except Exception as e:
            return UploadResult(success=False, error=str(e))

    async def read(self, path: str) -> Optional[bytes]:
        try:
            full_path = self._validate_path(path)

            if not full_path.exists():
                return None

            async with aiofiles.open(full_path, "rb") as f:
                return await f.read()
        except Exception:
            return None

    async def delete(self, path: str) -> DeleteResult:
        try:
            full_path = self._validate_path(path)

            if not full_path.exists():
                return DeleteResult(success=False, error="File not found")

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, os.remove, full_path)

            self._try_remove_empty_parent(full_path)

            return DeleteResult(success=True)
        except Exception as e:
            return DeleteResult(success=False, error=str(e))

    def _try_remove_empty_parent(self, file_path: Path) -> None:
        try:
            file_path.parent.rmdir()
        except OSError:
            pass

    async def exists(self, path: str) -> bool:
        try:
            full_path = self._validate_path(path)
            return full_path.exists() and full_path.is_file()
        except ValueError:
            return False

    def get_url(self, path: str) -> str:
        url_path = path.replace(os.sep, "/")
        return f"{self.base_url}/{url_path}"

    def get_provider_name(self) -> str:
        return "local"

    async def copy(self, source: str, destination: str) -> CopyResult:
        try:
            source_full = self._validate_path(source)
            dest_full = self._validate_path(destination)

            if not source_full.exists():
                return CopyResult(success=False, error="Source file not found")

            dest_full.parent.mkdir(parents=True, exist_ok=True)

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, shutil.copy2, source_full, dest_full)

            return CopyResult(
                success=True,
                path=destination,
                size=dest_full.stat().st_size,
            )
        except Exception as e:
            return CopyResult(success=False, error=str(e))

    async def move(self, source: str, destination: str) -> CopyResult:
        try:
            source_full = self._validate_path(source)
            dest_full = self._validate_path(destination)

            if not source_full.exists():
                return CopyResult(success=False, error="Source file not found")

            dest_full.parent.mkdir(parents=True, exist_ok=True)

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, shutil.move, source_full, dest_full)

            return CopyResult(
                success=True,
                path=destination,
                size=dest_full.stat().st_size,
            )
        except Exception as e:
            return CopyResult(success=False, error=str(e))

    async def get_metadata(self, path: str) -> Optional[FileMetadata]:
        try:
            full_path = self._validate_path(path)

            if not full_path.exists() or not full_path.is_file():
                return None

            stat = full_path.stat()
            content_type, _ = mimetypes.guess_type(str(full_path))

            return FileMetadata(
                path=path,
                size=stat.st_size,
                content_type=content_type,
                last_modified=timestamp_to_datetime(stat.st_mtime),
            )
        except (ValueError, OSError):
            return None

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
    ) -> List[FileInfo]:
        try:
            search_path = self._validate_path(prefix) if prefix else self.base_dir

            if not search_path.exists():
                return []

            if search_path.is_file():
                stat = search_path.stat()
                return [
                    FileInfo(
                        path=prefix,
                        size=stat.st_size,
                        is_directory=False,
                        last_modified=timestamp_to_datetime(stat.st_mtime),
                    )
                ]

            results: List[FileInfo] = []

            for item in search_path.rglob("*"):
                if len(results) >= limit:
                    break

                if item.is_file():
                    stat = item.stat()
                    results.append(
                        FileInfo(
                            path=str(item.relative_to(self.base_dir)),
                            size=stat.st_size,
                            is_directory=False,
                            last_modified=timestamp_to_datetime(stat.st_mtime),
                        )
                    )

            return results
        except (ValueError, OSError):
            return []

    async def read_stream(
        self,
        path: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> Optional[AsyncIterator[bytes]]:
        try:
            full_path = self._validate_path(path)

            if not full_path.exists():
                return None

            async def _stream() -> AsyncIterator[bytes]:
                async with aiofiles.open(full_path, "rb") as f:
                    while chunk := await f.read(chunk_size):
                        yield chunk

            return _stream()
        except ValueError:
            return None
