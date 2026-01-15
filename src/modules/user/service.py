import logging
import uuid
import secrets

from datetime import timedelta
from typing import Optional
from fastapi import UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core import (
    __,
    PasswordHasher,
    unique,
    now,
    BaseStorageProvider,
    MailMessage,
    mail_manager,
    settings,
    BaseAppException,
    ErrorCode,
)
from .models import User
from .repository import UserRepository, PasswordResetTokenRepository
from .schemas import (
    UserCreateRequest,
    UserResponse,
)

logger = logging.getLogger(__name__)


class UserService:
    def __init__(
        self,
        storage_provider: BaseStorageProvider,
        read_session: AsyncSession,
        write_session: AsyncSession,
    ):
        self.read_session = read_session
        self.write_session = write_session
        self.repository = UserRepository(read_session, write_session)
        self.password_hasher = PasswordHasher()
        self.storage = storage_provider

    async def create(self, data: UserCreateRequest) -> UserResponse:
        try:
            await unique(data.email, User, "email", field_label=__("field.email"))
            if data.password:
                data.password = self.password_hasher.hash(data.password)

            user_data = {
                "email": data.email.lower(),
                "name": data.name,
                "password": data.password,
                "phone": data.phone,
                "line_user_id": data.line_user_id,
                "is_admin": data.is_admin,
                "is_active": data.is_active,
            }

            user = await self.repository.create(user_data)

            if data.avatar:
                avatar_path = await self._upload_avatar(data.avatar)
                await self.repository.update(user.id, {"avatar_path": avatar_path})

            user_response = UserResponse.model_validate(user)
            user_response.avatar_url = (
                self.storage.get_url(user_response.avatar_path)
                if user_response.avatar_path
                else None
            )

            if data.password is None:
                token = await self._generate_reset_password_token(user)
                await self._send_created_user_email(user, token)

            await self.write_session.commit()
            return user_response
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            await self.write_session.rollback()
            raise

    async def _send_created_user_email(self, user: User, token: str) -> None:
        try:
            message = MailMessage(
                subject=__("mails.reset_password.subject"),
                recipients=[user.email],
                template_body={
                    "name": user.name or user.email,
                    "action_url": f"{settings.APP_URL_FRONTEND}/reset-password?token={token}",
                },
                subtype="html",
            )
            message.template_name = "reset-password.html"
            await mail_manager.send(message)
        except Exception as e:
            logger.error(f"Failed to send user creation email: {e}")

    async def _upload_avatar(
        self,
        avatar_file: UploadFile,
        old_avatar_path: Optional[str] = None,
    ) -> str:
        try:
            if old_avatar_path:
                await self.storage.delete(old_avatar_path)

            ext = (
                avatar_file.filename.rsplit(".", 1)[-1]
                if avatar_file.filename
                else "jpg"
            )
            timestamp = now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.{ext}"
            file_path = f"avatars/{filename}"

            result = await self.storage.save_file(
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

    async def _generate_reset_password_token(self, user: User) -> str:
        token = secrets.token_urlsafe(64)
        expires_at = now() + timedelta(seconds=settings.APP_TOKEN_TTL)

        token_data = {
            "user_id": user.id,
            "token": token,
            "expires_at": expires_at,
        }

        token_repo = PasswordResetTokenRepository(self.read_session, self.write_session)
        await token_repo.create(token_data)

        return token
