import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.utils.timezone import utcnow
from src.modules.auth.repository import AccessTokenRepository, RefreshTokenRepository
from src.modules.auth.models import AccessToken, RefreshToken


@pytest.mark.units
class TestAccessTokenRepository:
    async def test_find_by_jti(self, test_session: AsyncSession):
        repo = AccessTokenRepository(test_session, test_session)

        jti = "test-jti-12345"
        user_id = uuid4()
        token = AccessToken(
            user_id=user_id,
            jti=jti,
            expires_at=utcnow(),
            is_revoked=False,
        )
        test_session.add(token)
        await test_session.commit()

        found_token = await repo.find_by_jti(jti)

        assert found_token is not None
        assert found_token.jti == jti
        assert found_token.user_id == user_id

    async def test_find_by_jti_not_found(self, test_session: AsyncSession):
        repo = AccessTokenRepository(test_session, test_session)

        found_token = await repo.find_by_jti("non-existent-jti")

        assert found_token is None

    async def test_find_active_by_jti(self, test_session: AsyncSession):
        repo = AccessTokenRepository(test_session, test_session)

        jti_active = "active-jti-12345"
        user_id = uuid4()
        active_token = AccessToken(
            user_id=user_id,
            jti=jti_active,
            expires_at=utcnow(),
            is_revoked=False,
        )
        test_session.add(active_token)

        jti_revoked = "revoked-jti-12345"
        revoked_token = AccessToken(
            user_id=user_id,
            jti=jti_revoked,
            expires_at=utcnow(),
            is_revoked=True,
            revoked_at=utcnow(),
        )
        test_session.add(revoked_token)
        await test_session.commit()

        found_active = await repo.find_active_by_jti(jti_active)
        assert found_active is not None
        assert found_active.jti == jti_active
        assert found_active.is_revoked is False

        found_revoked = await repo.find_active_by_jti(jti_revoked)
        assert found_revoked is None

    async def test_revoke_token_success(self, test_session: AsyncSession):
        repo = AccessTokenRepository(test_session, test_session)

        jti = "revoke-test-jti"
        user_id = uuid4()
        token = AccessToken(
            user_id=user_id,
            jti=jti,
            expires_at=utcnow(),
            is_revoked=False,
        )
        test_session.add(token)
        await test_session.commit()

        result = await repo.revoke_token(jti)
        await test_session.commit()

        assert result is True

        revoked_token = await repo.find_by_jti(jti)
        assert revoked_token.is_revoked is True
        assert revoked_token.revoked_at is not None

    async def test_revoke_token_not_found(self, test_session: AsyncSession):
        repo = AccessTokenRepository(test_session, test_session)

        result = await repo.revoke_token("non-existent-jti")

        assert result is False

    async def test_revoke_all_user_tokens(self, test_session: AsyncSession):
        repo = AccessTokenRepository(test_session, test_session)

        user_id = uuid4()
        other_user_id = uuid4()

        for i in range(3):
            token = AccessToken(
                user_id=user_id,
                jti=f"user-token-{i}",
                expires_at=utcnow(),
                is_revoked=False,
            )
            test_session.add(token)

        other_token = AccessToken(
            user_id=other_user_id,
            jti="other-user-token",
            expires_at=utcnow(),
            is_revoked=False,
        )
        test_session.add(other_token)
        await test_session.commit()

        count = await repo.revoke_all_user_tokens(user_id)
        await test_session.commit()

        assert count == 3

        for i in range(3):
            token = await repo.find_by_jti(f"user-token-{i}")
            assert token.is_revoked is True
            assert token.revoked_at is not None

        other_token_check = await repo.find_by_jti("other-user-token")
        assert other_token_check.is_revoked is False

    async def test_cleanup_expired_tokens(self, test_session: AsyncSession):
        from datetime import timedelta

        repo = AccessTokenRepository(test_session, test_session)

        user_id = uuid4()

        for i in range(2):
            expired_token = AccessToken(
                user_id=user_id,
                jti=f"expired-token-cleanup-{i}",
                expires_at=utcnow() - timedelta(days=1),
                is_revoked=False,
            )
            test_session.add(expired_token)

        valid_token = AccessToken(
            user_id=user_id,
            jti="valid-token-cleanup",
            expires_at=utcnow() + timedelta(days=1),
            is_revoked=False,
        )
        test_session.add(valid_token)
        await test_session.commit()

        count = await repo.cleanup_expired_tokens()
        await test_session.commit()

        assert count >= 2

        for i in range(2):
            token = await repo.find_by_jti(f"expired-token-cleanup-{i}")
            assert token is None

        valid_check = await repo.find_by_jti("valid-token-cleanup")
        assert valid_check is not None


@pytest.mark.units
class TestRefreshTokenRepository:
    async def test_find_by_token(self, test_session: AsyncSession):
        repo = RefreshTokenRepository(test_session, test_session)

        token_str = "test-refresh-token-12345"
        jti = "test-jti-12345"
        user_id = uuid4()
        token = RefreshToken(
            user_id=user_id,
            token=token_str,
            jti=jti,
            expires_at=utcnow(),
            is_revoked=False,
        )
        test_session.add(token)
        await test_session.commit()

        found_token = await repo.find_by_token(token_str)

        assert found_token is not None
        assert found_token.token == token_str
        assert found_token.jti == jti

    async def test_find_by_jti(self, test_session: AsyncSession):
        repo = RefreshTokenRepository(test_session, test_session)

        token_str = "test-refresh-token-jti"
        jti = "test-refresh-jti"
        user_id = uuid4()
        token = RefreshToken(
            user_id=user_id,
            token=token_str,
            jti=jti,
            expires_at=utcnow(),
            is_revoked=False,
        )
        test_session.add(token)
        await test_session.commit()

        found_token = await repo.find_by_jti(jti)

        assert found_token is not None
        assert found_token.jti == jti
        assert found_token.token == token_str

    async def test_find_active_by_token(self, test_session: AsyncSession):
        repo = RefreshTokenRepository(test_session, test_session)

        user_id = uuid4()

        active_token_str = "active-refresh-token"
        active_token = RefreshToken(
            user_id=user_id,
            token=active_token_str,
            jti="active-jti",
            expires_at=utcnow(),
            is_revoked=False,
        )
        test_session.add(active_token)

        revoked_token_str = "revoked-refresh-token"
        revoked_token = RefreshToken(
            user_id=user_id,
            token=revoked_token_str,
            jti="revoked-jti",
            expires_at=utcnow(),
            is_revoked=True,
            revoked_at=utcnow(),
        )
        test_session.add(revoked_token)
        await test_session.commit()

        found_active = await repo.find_active_by_token(active_token_str)
        assert found_active is not None
        assert found_active.is_revoked is False

        found_revoked = await repo.find_active_by_token(revoked_token_str)
        assert found_revoked is None

    async def test_revoke_token_success(self, test_session: AsyncSession):
        repo = RefreshTokenRepository(test_session, test_session)

        token_str = "revoke-refresh-token"
        user_id = uuid4()
        token = RefreshToken(
            user_id=user_id,
            token=token_str,
            jti="revoke-jti",
            expires_at=utcnow(),
            is_revoked=False,
        )
        test_session.add(token)
        await test_session.commit()

        result = await repo.revoke_token(token_str)
        await test_session.commit()

        assert result is True

        revoked_token = await repo.find_by_token(token_str)
        assert revoked_token.is_revoked is True
        assert revoked_token.revoked_at is not None

    async def test_revoke_token_not_found(self, test_session: AsyncSession):
        repo = RefreshTokenRepository(test_session, test_session)

        result = await repo.revoke_token("non-existent-token")

        assert result is False

    async def test_revoke_all_user_tokens(self, test_session: AsyncSession):
        repo = RefreshTokenRepository(test_session, test_session)

        user_id = uuid4()
        other_user_id = uuid4()

        for i in range(3):
            token = RefreshToken(
                user_id=user_id,
                token=f"user-refresh-token-{i}",
                jti=f"user-refresh-jti-{i}",
                expires_at=utcnow(),
                is_revoked=False,
            )
            test_session.add(token)

        other_token = RefreshToken(
            user_id=other_user_id,
            token="other-user-refresh-token",
            jti="other-user-refresh-jti",
            expires_at=utcnow(),
            is_revoked=False,
        )
        test_session.add(other_token)
        await test_session.commit()

        count = await repo.revoke_all_user_tokens(user_id)
        await test_session.commit()

        assert count == 3

        for i in range(3):
            token = await repo.find_by_token(f"user-refresh-token-{i}")
            assert token.is_revoked is True
            assert token.revoked_at is not None

        other_token_check = await repo.find_by_token("other-user-refresh-token")
        assert other_token_check.is_revoked is False

    async def test_cleanup_expired_tokens(self, test_session: AsyncSession):
        from datetime import timedelta

        repo = RefreshTokenRepository(test_session, test_session)

        user_id = uuid4()

        for i in range(2):
            expired_token = RefreshToken(
                user_id=user_id,
                token=f"expired-refresh-token-cleanup-{i}",
                jti=f"expired-refresh-jti-cleanup-{i}",
                expires_at=utcnow() - timedelta(days=1),
                is_revoked=False,
            )
            test_session.add(expired_token)

        valid_token = RefreshToken(
            user_id=user_id,
            token="valid-refresh-token-cleanup",
            jti="valid-refresh-jti-cleanup",
            expires_at=utcnow() + timedelta(days=1),
            is_revoked=False,
        )
        test_session.add(valid_token)
        await test_session.commit()

        count = await repo.cleanup_expired_tokens()
        await test_session.commit()

        assert count >= 2

        for i in range(2):
            token = await repo.find_by_token(f"expired-refresh-token-cleanup-{i}")
            assert token is None

        valid_check = await repo.find_by_token("valid-refresh-token-cleanup")
        assert valid_check is not None
