from typing import Optional, Dict, Any
from uuid import UUID
from src.core import BaseRepository, now
from .models import User, PasswordResetToken
from .schemas import UserListRequest


class UserRepository(BaseRepository[User]):
    model = User

    async def find_by_email(self, email: str) -> Optional[User]:
        return await self.query().where(email=email.lower()).first()

    async def list_with_filters(self, payload: UserListRequest) -> Dict[str, Any]:
        query = self.query()

        if payload.search is not None:
            search_pattern = f"%{payload.search}%"
            query = query.where_or(
                name__ilike=search_pattern,
                email__ilike=search_pattern,
                phone__ilike=search_pattern,
                line_user_id__ilike=search_pattern,
            )

        if payload.type is not None:
            query = query.where(is_admin=bool(payload.type))

        if payload.status is not None:
            query = query.where(is_active=bool(payload.status))

        query = query.order_by(payload.sort_by, payload.sort_order)

        return await query.paginate(page=payload.page, per_page=payload.per_page)


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
