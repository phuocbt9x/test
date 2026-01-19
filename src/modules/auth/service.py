from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import status

from sqlalchemy.ext.asyncio import AsyncSession

from src.core import (
    __,
    JWTManager,
    PasswordHasher,
    TokenPayload,
    utcnow,
    NotFoundException,
    AuthenticationException,
    BaseAppException,
    ErrorCode,
    validate_and_hash_password,
    unique,
    verify_password,
    get_logger,
    storage_manager,
)
from src.modules.auth.schemas.request import UpdateCurrentUserRequest
from src.modules.user import User, UserRepository
from .models import AccessToken, RefreshToken
from .repository import AccessTokenRepository, RefreshTokenRepository

from .schemas import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    LogoutResponse,
    UserInfo,
)
from src.utils import upload_avatar

logger = get_logger(__name__)


class AuthService:
    def __init__(
        self,
        read_session: AsyncSession,
        write_session: AsyncSession,
    ):
        self.read_session = read_session
        self.write_session = write_session
        self.user_repo = UserRepository(read_session, write_session)
        self.access_token_repo = AccessTokenRepository(read_session, write_session)
        self.refresh_token_repo = RefreshTokenRepository(read_session, write_session)
        self.password_hasher = PasswordHasher()

    async def verify_token_in_db(
        self, jti: str, token_type: str = "access"
    ) -> tuple[bool, Optional[AccessToken | RefreshToken]]:
        token: Optional[AccessToken | RefreshToken] = None
        if token_type == "access":
            token = await self.access_token_repo.find_by_jti(jti)
        else:
            token = await self.refresh_token_repo.find_by_jti(jti)

        if not token:
            return False, None

        if token.is_revoked:
            return False, token

        if token.expires_at < utcnow():
            return False, token

        return True, token

    async def register(self, data: RegisterRequest) -> RegisterResponse:
        avatar_path = None

        try:
            await unique(data.email, User, "email", field_label=__("fields.user.email"))

            user_data = {
                "email": data.email.lower(),
                "name": data.name,
                "password": self.password_hasher.hash(data.password),
                "phone": data.phone,
                "line_user_id": data.line_user_id,
                "is_admin": False,
                "is_active": True,
            }

            if data.avatar:
                avatar_path = await upload_avatar(data.avatar)
                user_data["avatar_path"] = avatar_path

            user = await self.user_repo.create(user_data)
            tokens = await self._create_token_pair(user)
            user_info = UserInfo.model_validate(user)

            await self.write_session.commit()

            return RegisterResponse(
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                token_type=tokens.token_type,
                expires_in=tokens.expires_in,
                user_info=user_info,
            )
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            if avatar_path:
                await storage_manager.get_instance().delete(avatar_path)
            await self.write_session.rollback()
            raise

    async def login(self, data: LoginRequest) -> RegisterResponse:
        try:
            user = await self.user_repo.find_by_email(data.email.lower())

            if not user:
                raise BaseAppException(
                    message=__("auth.account.not_found", field=__("fields.user.email")),
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code=ErrorCode.USER_NOT_FOUND,
                )

            if (
                not user.is_active
                or not user.password
                or not verify_password(data.password, user.password)
            ):
                raise AuthenticationException(
                    message=__("auth.login.failed"),
                )

            tokens = await self._create_token_pair(user)
            user_info = UserInfo.model_validate(user)

            await self.write_session.commit()

            return RegisterResponse(
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                token_type=tokens.token_type,
                expires_in=tokens.expires_in,
                user_info=user_info,
            )
        except Exception as e:
            logger.error("Login failed: %s", e)
            await self.write_session.rollback()
            raise

    async def logout(
        self,
        access_token: str,
    ) -> LogoutResponse:
        try:
            payload = JWTManager.decode_token(access_token, verify=False)
            user_id_str = payload.get("sub")

            if not user_id_str:
                raise AuthenticationException(
                    message="Invalid token: missing user id",
                    error_code=ErrorCode.TOKEN_INVALID,
                )

            user_id = UUID(user_id_str)
            await self.access_token_repo.revoke_all_user_tokens(user_id)
            await self.refresh_token_repo.revoke_all_user_tokens(user_id)

            await self.write_session.commit()
            return LogoutResponse(message=__("auth.logout.success"))
        except Exception as e:
            logger.error("Logout failed: %s", e)
            await self.write_session.rollback()
            return LogoutResponse(message=__("auth.logout.failed"))

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        try:
            payload = JWTManager.decode_token(refresh_token, verify=True)

            if payload.get("type") != "refresh":
                raise AuthenticationException(
                    message=__("auth.token.invalid_type").format(type="refresh"),
                    error_code=ErrorCode.INVALID_TOKEN_TYPE,
                )

            jti = payload.get("jti")
            if not jti:
                raise AuthenticationException(
                    message=__("auth.token.invalid"),
                    error_code=ErrorCode.TOKEN_INVALID,
                )

            is_valid, token_record = await self.verify_token_in_db(
                jti, token_type="refresh"
            )
            if not is_valid or not token_record:
                raise AuthenticationException(
                    message=__("auth.token.not_found"),
                    error_code=ErrorCode.TOKEN_REVOKED,
                )

            user = await self.user_repo.get(token_record.user_id)

            if not user or not user.is_active:
                raise AuthenticationException(
                    message=__("auth.account.not_found"),
                    error_code=ErrorCode.USER_INACTIVE,
                )

            user_id_uuid = UUID(str(user.id))
            await self.refresh_token_repo.revoke_all_user_tokens(user_id_uuid)
            await self.access_token_repo.revoke_all_user_tokens(user_id_uuid)

            tokens = await self._create_token_pair(user)
            await self.write_session.commit()

            return tokens
        except Exception as e:
            logger.error("Refresh token failed: %s", e)
            await self.write_session.rollback()
            raise

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        return await self.refresh_access_token(refresh_token)

    async def verify_token(
        self, token: str, token_type: Optional[str] = None
    ) -> TokenPayload:
        payload = JWTManager.decode_token(token, verify=True)

        if token_type and payload.get("type") != token_type:
            raise AuthenticationException(
                message=__("auth.token.invalid_type").format(type=token_type),
                error_code=ErrorCode.INVALID_TOKEN_TYPE,
            )

        jti = payload.get("jti")
        if jti:
            is_valid, _ = await self.verify_token_in_db(
                jti, token_type=token_type or payload.get("type", "access")
            )
            if not is_valid:
                raise AuthenticationException(
                    message=__("auth.token.revoked"),
                    error_code=ErrorCode.TOKEN_REVOKED,
                )

        return TokenPayload(**payload)

    async def update_current_user(
        self, user_id: UUID, data: UpdateCurrentUserRequest
    ) -> UserInfo:
        avatar_path = None
        try:
            update_data = data.model_dump(exclude_none=True)
            user = await self.user_repo.get(user_id)

            if "password" in update_data:
                update_data["password"] = validate_and_hash_password(
                    update_data["password"]
                )
            if "avatar" in update_data:
                avatar_file = update_data.get("avatar")
                if avatar_file:
                    avatar_path = await upload_avatar(avatar_file)
                    if avatar_path and user and user.avatar_path is not None:
                        await storage_manager.get_instance().delete(user.avatar_path)
                        update_data["avatar_path"] = avatar_path

            user = await self.user_repo.update(user_id, update_data)

            if "email" in update_data or "password" in update_data:
                await self.access_token_repo.revoke_all_user_tokens(user_id)
                await self.refresh_token_repo.revoke_all_user_tokens(user_id)

            await self.write_session.commit()

            return UserInfo.model_validate(user)
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            if avatar_path:
                await storage_manager.get_instance().delete(avatar_path)
            await self.write_session.rollback()
            raise

    async def get_current_user(self, user_id: str) -> UserInfo:
        user = await self.user_repo.get(UUID(user_id))

        if not user:
            raise NotFoundException(resource="User", resource_id=user_id)

        return UserInfo.model_validate(user)

    async def _create_token_pair(self, user: User) -> TokenResponse:
        token_pair = JWTManager.create_token_pair(
            user_id=str(user.id),
            email=user.email,
            username=user.name,
            roles=["admin"] if user.is_admin else ["user"],
        )

        access_payload = JWTManager.decode_token(token_pair.access_token, verify=False)
        refresh_payload = JWTManager.decode_token(
            token_pair.refresh_token, verify=False
        )

        access_jti = access_payload.get("jti")
        access_exp = access_payload.get("exp")
        refresh_jti = refresh_payload.get("jti")
        refresh_exp = refresh_payload.get("exp")

        if access_jti and access_exp:
            expires_at = datetime.fromtimestamp(access_exp, tz=utcnow().tzinfo)
            await self.access_token_repo.create(
                {
                    "user_id": user.id,
                    "jti": access_jti,
                    "expires_at": expires_at,
                    "is_revoked": False,
                }
            )

        if refresh_jti and refresh_exp:
            expires_at = datetime.fromtimestamp(refresh_exp, tz=utcnow().tzinfo)
            await self.refresh_token_repo.create(
                {
                    "user_id": user.id,
                    "token": token_pair.refresh_token,
                    "jti": refresh_jti,
                    "expires_at": expires_at,
                    "is_revoked": False,
                }
            )

        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
        )
