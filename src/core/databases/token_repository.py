from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from typing import Optional
from .token_model import Token

class TokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_token(self, user_id: str, jti: str, token_type: str, issued_at: datetime, expires_at: datetime, token: str) -> Token:
        db_token = Token(
            user_id=user_id,
            jti=jti,
            token_type=token_type,
            issued_at=issued_at,
            expires_at=expires_at,
            token=token,
            revoked=False,
        )
        self.session.add(db_token)
        await self.session.commit()
        await self.session.refresh(db_token)
        return db_token

    async def revoke_token(self, jti: str) -> bool:
        q = update(Token).where(Token.jti == jti).values(revoked=True)
        await self.session.execute(q)
        await self.session.commit()
        return True

    async def is_token_active(self, jti: str) -> bool:
        q = select(Token).where(Token.jti == jti, Token.revoked == False, Token.expires_at > datetime.utcnow())
        result = await self.session.execute(q)
        token = result.scalar_one_or_none()
        return token is not None

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        q = update(Token).where(Token.user_id == user_id, Token.revoked == False).values(revoked=True)
        result = await self.session.execute(q)
        await self.session.commit()
        return result.rowcount
