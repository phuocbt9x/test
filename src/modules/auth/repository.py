from typing import Optional
from uuid import UUID

from sqlalchemy import select

from src.core.orm.base_repository import BaseRepository

from .models import AccessToken, RefreshToken


class AccessTokenRepository(BaseRepository[AccessToken]):
    model = AccessToken

    async def find_by_jti(self, jti: str) -> Optional[AccessToken]:
        return await self.query().where(jti=jti).first()

    async def find_active_by_jti(self, jti: str) -> Optional[AccessToken]:
        return await self.query().where(jti=jti, is_revoked=False).first()

    async def revoke_token(self, jti: str) -> bool:
        from src.core.utils.timezone import utcnow

        token = await self.find_by_jti(jti)
        if not token:
            return False
        await self.update(token.id, {"is_revoked": True, "revoked_at": utcnow()})
        return True

    async def revoke_all_user_tokens(self, user_id: UUID) -> int:
        from src.core.utils.timezone import utcnow

        return await self.bulk_update(
            {"user_id": user_id, "is_revoked": False},
            {"is_revoked": True, "revoked_at": utcnow()},
        )

    async def cleanup_expired_tokens(self) -> int:
        from src.core.utils.timezone import utcnow

        query = select(AccessToken).where(AccessToken.expires_at < utcnow())
        result = await self.write_session.execute(query)
        tokens = result.scalars().all()
        count = 0
        for token in tokens:
            await self.write_session.delete(token)
            count += 1
        return count


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def find_by_token(self, token: str) -> Optional[RefreshToken]:
        return await self.query().where(token=token).first()

    async def find_by_jti(self, jti: str) -> Optional[RefreshToken]:
        return await self.query().where(jti=jti).first()

    async def find_active_by_token(self, token: str) -> Optional[RefreshToken]:
        return await self.query().where(token=token, is_revoked=False).first()

    async def revoke_token(self, token: str) -> bool:
        from src.core.utils.timezone import utcnow

        refresh_token = await self.find_by_token(token)
        if not refresh_token:
            return False
        await self.update(
            refresh_token.id, {"is_revoked": True, "revoked_at": utcnow()}
        )
        return True

    async def revoke_all_user_tokens(self, user_id: UUID) -> int:
        from src.core.utils.timezone import utcnow

        return await self.bulk_update(
            {"user_id": user_id, "is_revoked": False},
            {"is_revoked": True, "revoked_at": utcnow()},
        )

    async def cleanup_expired_tokens(self) -> int:
        from src.core.utils.timezone import utcnow

        query = select(RefreshToken).where(RefreshToken.expires_at < utcnow())
        result = await self.write_session.execute(query)
        tokens = result.scalars().all()
        count = 0
        for token in tokens:
            await self.write_session.delete(token)
            count += 1
        return count
