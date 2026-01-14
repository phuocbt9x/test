import logging
from typing import Optional
import aioboto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from .base import BaseStorageProvider, UploadResult, DeleteResult

logger = logging.getLogger(__name__)


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
    ):
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.endpoint_url = endpoint_url
        self.public_url = public_url
        self.acl = (
            acl
            if acl
            in ("private", "public-read", "public-read-write", "authenticated-read")
            else "private"
        )

        self.session = aioboto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region_name,
        )

    def _get_client_kwargs(self) -> dict:
        kwargs = {}
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        return kwargs

    async def upload(
        self,
        file_data: bytes,
        file_path: str,
        content_type: Optional[str] = None,
    ) -> UploadResult:
        try:
            async with self.session.client("s3", **self._get_client_kwargs()) as s3:
                put_args = {
                    "Bucket": self.bucket_name,
                    "Key": file_path,
                    "Body": file_data,
                }

                if content_type:
                    put_args["ContentType"] = content_type

                if self.acl:
                    put_args["ACL"] = self.acl

                await s3.put_object(**put_args)

                url = self.get_url(file_path)

                return UploadResult(
                    success=True, url=url, path=file_path, size=len(file_data)
                )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "S3 upload failed",
                exc_info=True,
                extra={
                    "error_code": error_code,
                    "bucket": self.bucket_name,
                    "file_path": file_path,
                },
            )
            return UploadResult(
                success=False,
                error="File upload failed. Please try again.",
            )
        except Exception as e:
            logger.exception(
                "S3 upload unexpected error",
                extra={
                    "error_type": type(e).__name__,
                    "bucket": self.bucket_name,
                    "file_path": file_path,
                },
            )
            return UploadResult(success=False, error="Upload failed. Please try again.")

    async def download(self, file_path: str) -> Optional[bytes]:
        try:
            async with self.session.client("s3", **self._get_client_kwargs()) as s3:
                response = await s3.get_object(Bucket=self.bucket_name, Key=file_path)

                async with response["Body"] as stream:
                    return await stream.read()

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchKey":
                logger.debug(
                    "File not found in S3",
                    extra={"bucket": self.bucket_name, "file_path": file_path},
                )
                return None
            logger.warning(
                "S3 download failed",
                extra={
                    "error_code": error_code,
                    "bucket": self.bucket_name,
                    "file_path": file_path,
                },
            )
            return None
        except Exception as e:
            logger.exception(
                "S3 download unexpected error",
                extra={
                    "error_type": type(e).__name__,
                    "bucket": self.bucket_name,
                    "file_path": file_path,
                },
            )
            return None

    async def delete(self, file_path: str) -> DeleteResult:
        try:
            async with self.session.client("s3", **self._get_client_kwargs()) as s3:
                await s3.delete_object(Bucket=self.bucket_name, Key=file_path)

                return DeleteResult(success=True)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "S3 delete failed",
                exc_info=True,
                extra={
                    "error_code": error_code,
                    "bucket": self.bucket_name,
                    "file_path": file_path,
                },
            )
            return DeleteResult(
                success=False,
                error="File deletion failed. Please try again.",
            )
        except Exception as e:
            logger.exception(
                "S3 delete unexpected error",
                extra={
                    "error_type": type(e).__name__,
                    "bucket": self.bucket_name,
                    "file_path": file_path,
                },
            )
            return DeleteResult(
                success=False, error="Deletion failed. Please try again."
            )

    async def exists(self, file_path: str) -> bool:
        try:
            async with self.session.client("s3", **self._get_client_kwargs()) as s3:
                await s3.head_object(Bucket=self.bucket_name, Key=file_path)
                return True

        except ClientError:
            return False
        except Exception:
            return False

    def get_url(self, file_path: str) -> str:
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{file_path}"

        if self.endpoint_url:
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{file_path}"

        return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{file_path}"

    def get_provider_name(self) -> str:
        return "s3"
