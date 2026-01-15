import asyncio
import gzip
import inspect
import logging
import random
from dataclasses import dataclass
from typing import AsyncIterator, BinaryIO, List, Optional, Union

import aioboto3  # type: ignore[import-untyped]
import boto3  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from boto3.s3.transfer import TransferConfig  # type: ignore[import-untyped]
from fastapi import UploadFile

from src.core.utils import ensure_utc

from .base import (
    BaseStorageProvider,
    CopyResult,
    DeleteResult,
    FileInfo,
    FileMetadata,
    UploadResult,
)

logger = logging.getLogger(__name__)

VALID_ACLS = ("private", "public-read", "public-read-write", "authenticated-read")
DEFAULT_CHUNK_SIZE = 1024 * 1024
DEFAULT_MULTIPART_THRESHOLD = 8 * 1024 * 1024
DEFAULT_MULTIPART_CHUNK_SIZE = 8 * 1024 * 1024


@dataclass(frozen=True)
class S3PerformanceConfig:
    compress: bool = False
    compress_min_size: int = 1024
    compress_max_size: int = 5 * 1024 * 1024
    compress_content_types: Optional[tuple[str, ...]] = None
    multipart_threshold: int = DEFAULT_MULTIPART_THRESHOLD
    multipart_chunk_size: int = DEFAULT_MULTIPART_CHUNK_SIZE
    max_pool_connections: int = 20
    retry_max_attempts: int = 5
    retry_base_delay: float = 0.2
    retry_max_delay: float = 2.0


class S3StorageProvider(BaseStorageProvider):
    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        public_url: Optional[str] = None,
        acl: str = "private",
        performance: Optional[S3PerformanceConfig] = None,
    ):
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.endpoint_url = endpoint_url
        self.public_url = public_url
        perf = performance or S3PerformanceConfig()
        self.acl = acl if acl in VALID_ACLS else "private"
        self.compress = perf.compress
        self.compress_min_size = perf.compress_min_size
        self.compress_max_size = perf.compress_max_size
        self.compress_content_types = perf.compress_content_types or (
            "text/plain",
            "text/html",
            "text/css",
            "application/json",
            "application/javascript",
            "application/xml",
            "text/xml",
        )
        self.multipart_threshold = perf.multipart_threshold
        self.multipart_chunk_size = perf.multipart_chunk_size
        self.max_pool_connections = perf.max_pool_connections
        self.retry_max_attempts = perf.retry_max_attempts
        self.retry_base_delay = perf.retry_base_delay
        self.retry_max_delay = perf.retry_max_delay
        self._client: Optional[aioboto3.client] = None
        self._client_lock = asyncio.Lock()

        self.session = aioboto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region_name,
        )
        self._client_config = Config(
            retries={"max_attempts": self.retry_max_attempts, "mode": "adaptive"},
            max_pool_connections=self.max_pool_connections,
        )
        self._transfer_config = TransferConfig(
            multipart_threshold=self.multipart_threshold,
            multipart_chunksize=self.multipart_chunk_size,
            max_concurrency=max(1, min(10, self.max_pool_connections)),
            use_threads=True,
        )

    def _get_client_kwargs(self) -> dict:
        kwargs = {"config": self._client_config}
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        return kwargs

    async def _get_client(self):
        if self._client is not None:
            return self._client
        async with self._client_lock:
            if self._client is None:
                self._client = await self.session.client(
                    "s3", **self._get_client_kwargs()
                ).__aenter__()
        return self._client

    def _build_extra_args(
        self,
        content_type: Optional[str] = None,
        content_encoding: Optional[str] = None,
    ) -> dict:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if content_encoding:
            extra_args["ContentEncoding"] = content_encoding
        if self.acl:
            extra_args["ACL"] = self.acl
        return extra_args

    def _maybe_compress(
        self, file_data: bytes, content_type: Optional[str]
    ) -> tuple[bytes, Optional[str]]:
        if not self.compress or not content_type:
            return file_data, None
        if content_type not in self.compress_content_types:
            return file_data, None
        data_len = len(file_data)
        if data_len < self.compress_min_size or data_len > self.compress_max_size:
            return file_data, None
        return gzip.compress(file_data), "gzip"

    async def _with_retries(self, func, *args, **kwargs):
        attempt = 0
        while True:
            try:
                return await func(*args, **kwargs)
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code not in {
                    "RequestTimeout",
                    "Throttling",
                    "ThrottlingException",
                    "SlowDown",
                    "InternalError",
                    "ServiceUnavailable",
                    "RequestTimeoutException",
                }:
                    raise
            except Exception:
                if attempt >= self.retry_max_attempts - 1:
                    raise
            delay = min(
                self.retry_max_delay,
                self.retry_base_delay * (2**attempt),
            )
            delay += random.uniform(0, delay / 4)
            await asyncio.sleep(delay)
            attempt += 1

    async def save(
        self,
        file_data: bytes,
        path: str,
        content_type: Optional[str] = None,
    ) -> UploadResult:
        try:
            s3 = await self._get_client()
            file_data, content_encoding = self._maybe_compress(file_data, content_type)
            put_args = {
                "Bucket": self.bucket_name,
                "Key": path,
                "Body": file_data,
                **self._build_extra_args(content_type, content_encoding),
            }

            await self._with_retries(s3.put_object, **put_args)

            return UploadResult(
                success=True,
                path=path,
                size=len(file_data),
            )
        except ClientError as e:
            logger.error(
                "S3 save failed",
                exc_info=True,
                extra={
                    "error_code": e.response.get("Error", {}).get("Code"),
                    "bucket": self.bucket_name,
                    "path": path,
                },
            )
            return UploadResult(success=False, error="File save failed")
        except Exception:
            logger.exception(
                "S3 save error",
                extra={"bucket": self.bucket_name, "path": path},
            )
            return UploadResult(success=False, error="Save failed")

    async def save_file(
        self,
        file: Union[UploadFile, BinaryIO],
        path: str,
        content_type: Optional[str] = None,
    ) -> UploadResult:
        try:
            s3 = await self._get_client()
            if isinstance(file, UploadFile):
                content_type = content_type or file.content_type
                file_obj = file.file
            else:
                if hasattr(file, "read") and inspect.iscoroutinefunction(file.read):
                    file_data = await file.read()
                    file_data, content_encoding = self._maybe_compress(
                        file_data, content_type
                    )
                    put_args = {
                        "Bucket": self.bucket_name,
                        "Key": path,
                        "Body": file_data,
                        **self._build_extra_args(content_type, content_encoding),
                    }
                    await self._with_retries(s3.put_object, **put_args)
                    return UploadResult(
                        success=True,
                        path=path,
                        size=len(file_data),
                    )
                file_obj = file

            extra_args = self._build_extra_args(content_type)

            await self._with_retries(
                s3.upload_fileobj,
                file_obj,
                self.bucket_name,
                path,
                ExtraArgs=extra_args if extra_args else None,
                Config=self._transfer_config,
            )

            size: Optional[int] = None
            try:
                file_obj.seek(0, 2)
                size = file_obj.tell()
                file_obj.seek(0)
            except (AttributeError, OSError):
                size = None

            return UploadResult(
                success=True,
                path=path,
                size=size,
            )
        except ClientError as e:
            logger.error(
                "S3 save_file failed",
                exc_info=True,
                extra={
                    "error_code": e.response.get("Error", {}).get("Code"),
                    "bucket": self.bucket_name,
                    "path": path,
                },
            )
            return UploadResult(success=False, error="File save failed")
        except Exception:
            logger.exception(
                "S3 save_file error",
                extra={"bucket": self.bucket_name, "path": path},
            )
            return UploadResult(success=False, error="Save failed")

    async def read(self, path: str) -> Optional[bytes]:
        try:
            s3 = await self._get_client()
            response = await self._with_retries(
                s3.get_object, Bucket=self.bucket_name, Key=path
            )
            async with response["Body"] as stream:
                return await stream.read()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code != "NoSuchKey":
                logger.warning(
                    "S3 read failed",
                    extra={
                        "error_code": error_code,
                        "bucket": self.bucket_name,
                        "path": path,
                    },
                )
            return None
        except Exception:
            logger.exception(
                "S3 read error",
                extra={"bucket": self.bucket_name, "path": path},
            )
            return None

    async def delete(self, path: str) -> DeleteResult:
        try:
            s3 = await self._get_client()
            await self._with_retries(
                s3.delete_object, Bucket=self.bucket_name, Key=path
            )
            return DeleteResult(success=True)
        except ClientError as e:
            logger.error(
                "S3 delete failed",
                exc_info=True,
                extra={
                    "error_code": e.response.get("Error", {}).get("Code"),
                    "bucket": self.bucket_name,
                    "path": path,
                },
            )
            return DeleteResult(success=False, error="File deletion failed")
        except Exception:
            logger.exception(
                "S3 delete error",
                extra={"bucket": self.bucket_name, "path": path},
            )
            return DeleteResult(success=False, error="Deletion failed")

    async def exists(self, path: str) -> bool:
        try:
            s3 = await self._get_client()
            await self._with_retries(s3.head_object, Bucket=self.bucket_name, Key=path)
            return True
        except (ClientError, Exception):
            return False

    def get_url(self, path: str) -> str:
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{path}"

        if self.endpoint_url:
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{path}"

        return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{path}"

    def get_provider_name(self) -> str:
        return "s3"

    async def copy(self, source: str, destination: str) -> CopyResult:
        try:
            s3 = await self._get_client()
            copy_source = {"Bucket": self.bucket_name, "Key": source}
            extra_args = self._build_extra_args()

            await self._with_retries(
                s3.copy_object,
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=destination,
                **extra_args,
            )

            head = await self._with_retries(
                s3.head_object, Bucket=self.bucket_name, Key=destination
            )

            return CopyResult(
                success=True,
                path=destination,
                size=head.get("ContentLength", 0),
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey":
                return CopyResult(success=False, error="Source file not found")
            logger.error(
                "S3 copy failed",
                exc_info=True,
                extra={
                    "error_code": error_code,
                    "bucket": self.bucket_name,
                    "source": source,
                    "destination": destination,
                },
            )
            return CopyResult(success=False, error="Copy failed")
        except Exception:
            logger.exception(
                "S3 copy error",
                extra={
                    "bucket": self.bucket_name,
                    "source": source,
                    "destination": destination,
                },
            )
            return CopyResult(success=False, error="Copy failed")

    async def move(self, source: str, destination: str) -> CopyResult:
        result = await self.copy(source, destination)
        if result.success:
            await self.delete(source)
        return result

    async def get_metadata(self, path: str) -> Optional[FileMetadata]:
        try:
            s3 = await self._get_client()
            head = await self._with_retries(
                s3.head_object, Bucket=self.bucket_name, Key=path
            )

            return FileMetadata(
                path=path,
                size=head.get("ContentLength", 0),
                content_type=head.get("ContentType"),
                last_modified=ensure_utc(head.get("LastModified")),
                etag=head.get("ETag", "").strip('"'),
                extra=head.get("Metadata", {}),
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code not in ("NoSuchKey", "404"):
                logger.warning(
                    "S3 get_metadata failed",
                    extra={
                        "error_code": error_code,
                        "bucket": self.bucket_name,
                        "path": path,
                    },
                )
            return None
        except Exception:
            logger.exception(
                "S3 get_metadata error",
                extra={"bucket": self.bucket_name, "path": path},
            )
            return None

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
    ) -> List[FileInfo]:
        try:
            s3 = await self._get_client()
            results: List[FileInfo] = []
            paginator = s3.get_paginator("list_objects_v2")

            async for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
                PaginationConfig={"MaxItems": limit},
            ):
                for obj in page.get("Contents", []):
                    results.append(
                        FileInfo(
                            path=obj["Key"],
                            size=obj.get("Size", 0),
                            is_directory=obj["Key"].endswith("/"),
                            last_modified=ensure_utc(obj.get("LastModified")),
                        )
                    )

            return results
        except ClientError as e:
            logger.error(
                "S3 list_files failed",
                extra={
                    "error_code": e.response.get("Error", {}).get("Code"),
                    "bucket": self.bucket_name,
                    "prefix": prefix,
                },
            )
            return []
        except Exception:
            logger.exception(
                "S3 list_files error",
                extra={"bucket": self.bucket_name, "prefix": prefix},
            )
            return []

    async def read_stream(
        self,
        path: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> Optional[AsyncIterator[bytes]]:
        async def _stream() -> AsyncIterator[bytes]:
            try:
                s3 = await self._get_client()
                response = await self._with_retries(
                    s3.get_object, Bucket=self.bucket_name, Key=path
                )
                async with response["Body"] as stream:
                    while True:
                        chunk = await stream.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if error_code != "NoSuchKey":
                    logger.warning(
                        "S3 read_stream failed",
                        extra={
                            "error_code": error_code,
                            "bucket": self.bucket_name,
                            "path": path,
                        },
                    )
            except Exception:
                logger.exception(
                    "S3 read_stream error",
                    extra={"bucket": self.bucket_name, "path": path},
                )

        return _stream()

    def generate_signed_url(
        self,
        path: str,
        expires_in: int = 3600,
        method: str = "GET",
    ) -> Optional[str]:
        try:
            client_kwargs = self._get_client_kwargs()

            s3_client = boto3.client(
                "s3",
                region_name=self.region_name,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                config=Config(
                    signature_version="s3v4",
                    retries={
                        "max_attempts": self.retry_max_attempts,
                        "mode": "adaptive",
                    },
                    max_pool_connections=self.max_pool_connections,
                ),
                **client_kwargs,
            )

            client_method = "get_object" if method.upper() == "GET" else "put_object"

            return s3_client.generate_presigned_url(
                ClientMethod=client_method,
                Params={"Bucket": self.bucket_name, "Key": path},
                ExpiresIn=expires_in,
            )
        except Exception:
            logger.exception(
                "S3 generate_signed_url error",
                extra={"bucket": self.bucket_name, "path": path},
            )
            return None
