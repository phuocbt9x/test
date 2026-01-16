import secrets

from datetime import timedelta
from typing import Dict, Any
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from src.core import (
    __,
    PasswordHasher,
    unique,
    now,
    MailMessage,
    mail_manager,
    settings,
    get_logger,
)
from .models import User
from .repository import UserRepository, PasswordResetTokenRepository
from .schemas import (
    UserListRequest,
    UserCreateRequest,
    UserResponse,
)
from src.utils import upload_avatar

logger = get_logger(__name__)


class UserService:
    def __init__(
        self,
        read_session: AsyncSession,
        write_session: AsyncSession,
    ):
        self.read_session = read_session
        self.write_session = write_session
        self.repository = UserRepository(read_session, write_session)
        self.password_hasher = PasswordHasher()

    async def list(self, payload: UserListRequest) -> Dict[str, Any]:
        try:
            return await self.repository.list_with_filters(payload)
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise

    async def create(
        self, data: UserCreateRequest, background_tasks: BackgroundTasks
    ) -> UserResponse:
        try:
            await unique(data.email, User, "email", field_label=__("fields.user.email"))
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
                avatar_path = await upload_avatar(data.avatar)
                await self.repository.update(user.id, {"avatar_path": avatar_path})

            await self.write_session.commit()

            token = await self._generate_reset_password_token(user)
            background_tasks.add_task(self._send_created_user_email, user, token)

            return UserResponse.model_validate(user)
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
