from typing import Optional
from uuid import UUID
from src.core import BaseRepository, now
from .models import User, PasswordResetToken


class UserRepository(BaseRepository[User]):
    model = User

    async def find_by_email(self, email: str) -> Optional[User]:
        return await self.query().where(email=email.lower()).first()


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    model = PasswordResetToken

    async def find_by_token(self, token: str) -> Optional[PasswordResetToken]:
        return await self.query().where(token=token).first()

    async def find_by_token_not_used(self, token: str) -> Optional[PasswordResetToken]:
        return await self.query().where(token=token).where_null("used_at").first()

    async def mark_as_used(self, token_id: UUID) -> bool:
        result = await self.update(token_id, {"used_at": now()})
        return result is not None

    async def delete_expired_tokens(self) -> int:
        expired_tokens = await self.query().where_null("used_at").all()
        count = 0
        for token in expired_tokens:
            if token.expires_at < now():
                await self.delete(token.id)
                count += 1
        return count
