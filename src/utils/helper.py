import uuid

from typing import Optional
from fastapi import UploadFile, status
from src.core import (
    now,
    BaseAppException,
    ErrorCode,
    get_logger,
    storage_manager,
)

logger = get_logger(__name__)


async def upload_avatar(
    avatar_file: UploadFile,
    old_avatar_path: Optional[str] = None,
) -> str:
    try:
        storage = storage_manager.get_instance()

        if old_avatar_path:
            await storage.delete(old_avatar_path)

        ext = avatar_file.filename.rsplit(".", 1)[-1] if avatar_file.filename else "jpg"
        timestamp = now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.{ext}"
        file_path = f"avatars/{filename}"

        result = await storage.save_file(
            file=avatar_file,
            path=file_path,
            content_type=avatar_file.content_type,
        )

        if not result.success or not result.path:
            raise BaseAppException(
                message="Failed to upload avatar",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.USER_NOT_FOUND,
            )

        return result.path
    except Exception as e:
        logger.error(f"Failed to upload avatar: {e}")
        raise


__all__ = ["upload_avatar"]
