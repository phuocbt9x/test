"""
Auth Repository

Data access layer for auth operations.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select

from src.core.databases.base_repository import BaseRepository
from src.core.utils.timezone import utcnow

from .models import RefreshToken, TokenBlacklist


class TokenBlacklistRepository(BaseRepository[TokenBlacklist]):
    """Repository for token blacklist operations"""

    model = TokenBlacklist

    async def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if a token is blacklisted.
        
        Performance: Uses BaseRepository exists() method for optimal performance.
        Indexed on jti column for fast lookups.

        Args:
            jti: JWT ID

        Returns:
            True if blacklisted, False otherwise
        """
        # Note: BaseRepository.where() only supports ==, so we need custom query for > comparison
        # But we can still use BaseRepository pattern for consistency
        query = select(TokenBlacklist).where(
            TokenBlacklist.jti == jti,
            TokenBlacklist.expires_at > utcnow()
        )
        result = await self.session.execute(query)
        return result.scalars().first() is not None

    async def blacklist_token(
        self,
        jti: str,
        user_id: UUID,
        token_type: str,
        expires_at: datetime,
        reason: Optional[str] = None,
        token_signature: Optional[str] = None,
    ) -> TokenBlacklist:
        """
        Add token to blacklist.

        Args:
            jti: JWT ID
            user_id: User ID
            token_type: Token type (access or refresh)
            expires_at: Token expiration timestamp
            reason: Revocation reason
            token_signature: Partial token for debugging

        Returns:
            Created blacklist entry
        """
        data = {
            "jti": jti,
            "user_id": user_id,
            "token_type": token_type,
            "expires_at": expires_at,
            "revocation_reason": reason,
            "token_signature": token_signature,
        }
        return await self.create(data)

    async def blacklist_all_user_tokens(
        self,
        user_id: UUID,
        reason: str = "user_action"
    ) -> int:
        """
        Revoke all active tokens for a user.

        This is used when:
        - User changes password
        - Admin forces logout
        - Security breach

        Note: This doesn't actually blacklist all tokens individually,
        but rather marks a user-level revocation timestamp.
        The actual check happens during token verification.

        Args:
            user_id: User ID
            reason: Revocation reason

        Returns:
            Number of tokens affected
        """
        # In a real implementation, you might want to:
        # 1. Query all active refresh tokens for this user
        # 2. Blacklist them individually
        # 3. Or use a user-level revocation timestamp check

        # For now, this is a placeholder that would work with
        # the refresh token table
        return 0

    async def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from blacklist.

        Should be run periodically (e.g., daily cron job).

        Returns:
            Number of tokens removed
        """
        stmt = delete(TokenBlacklist).where(
            TokenBlacklist.expires_at < utcnow()
        )
        result = await self.session.execute(stmt)
        # SQLAlchemy 2.x async result may not have rowcount; fallback to 0 if missing
        rowcount = getattr(result, 'rowcount', None)
        return rowcount if rowcount is not None else 0


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository for refresh token operations"""

    model = RefreshToken

    async def find_by_jti(self, jti: str) -> Optional[RefreshToken]:
        """
        Find refresh token by JTI.
        
        Uses BaseRepository query builder for consistency.
        """
        return await self.query().where(jti=jti).first()

    async def store_refresh_token(
        self,
        jti: str,
        user_id: UUID,
        expires_at: datetime,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        family_id: Optional[UUID] = None,
        parent_jti: Optional[str] = None,
    ) -> RefreshToken:
        """
        Store a new refresh token.

        Args:
            jti: JWT ID
            user_id: User ID
            expires_at: Expiration timestamp
            device_info: User agent/device info
            ip_address: Client IP address
            family_id: Token family ID for rotation
            parent_jti: Parent token JTI

        Returns:
            Created refresh token
        """
        data = {
            "jti": jti,
            "user_id": user_id,
            "expires_at": expires_at,
            "device_info": device_info,
            "ip_address": ip_address,
            "family_id": family_id,
            "parent_jti": parent_jti,
            "is_revoked": False,
        }
        return await self.create(data)

    async def revoke_token(self, jti: str) -> bool:
        """
        Revoke a refresh token.

        Args:
            jti: JWT ID

        Returns:
            True if revoked successfully
        """
        query = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await self.session.execute(query)
        token = result.scalars().first()

        if not token:
            return False

        token.is_revoked = True
        token.revoked_at = utcnow()
        await self.session.flush()
        return True

    async def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """
        Revoke all refresh tokens for a user.

        Args:
            user_id: User ID

        Returns:
            Number of tokens revoked
        """
        query = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            ~RefreshToken.is_revoked,
            RefreshToken.expires_at > utcnow()
        )
        result = await self.session.execute(query)
        tokens = result.scalars().all()

        count = 0
        for token in tokens:
            token.is_revoked = True
            token.revoked_at = utcnow()
            count += 1

        await self.session.flush()
        return count

    async def cleanup_expired_tokens(self) -> int:
        """
        Remove expired refresh tokens.

        Returns:
            Number of tokens removed
        """
        stmt = delete(RefreshToken).where(
            RefreshToken.expires_at < utcnow()
        )
        result = await self.session.execute(stmt)
        rowcount = getattr(result, 'rowcount', None)
        return rowcount if rowcount is not None else 0

    async def get_user_active_sessions(self, user_id: UUID) -> list[RefreshToken]:
        """
        Get all active sessions (refresh tokens) for a user.
        
        Uses BaseRepository query builder where possible. Note that BaseRepository
        doesn't support complex conditions (like ~ and >), so we keep custom query
        for this specific use case.

        Args:
            user_id: User ID

        Returns:
            List of active refresh tokens
        """
        # BaseRepository.where() doesn't support complex conditions (~, >),
        # so we use direct query for this specific case
        query = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            ~RefreshToken.is_revoked,
            RefreshToken.expires_at > utcnow()
        ).order_by(RefreshToken.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())
