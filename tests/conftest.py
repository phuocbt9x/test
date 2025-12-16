"""
Pytest configuration and shared fixtures for testing.

This module provides:
- Database test fixtures with transaction rollback
- Redis test fixtures with cleanup
- FastAPI test client
- Authentication fixtures
- Mock factories
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from redis.asyncio import Redis

from src.core.configs import settings
from src.core.configs.database import db, Base
from src.core.configs.redis import redis_manager
from src.modules.user.models import User
from src.modules.auth.models import RefreshToken, TokenBlacklist
from src.core.security.jwt import JWTManager
from src.core.security.password import PasswordHasher


# ==================== Event Loop Configuration ====================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== Database Fixtures ====================

@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """
    Create a test database engine.
    Uses SQLite in-memory database for fast testing.
    """
    # Use SQLite for testing (faster and isolated)
    test_database_url = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(
        test_database_url,
        echo=False,
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session with transaction rollback.
    Each test gets a fresh session with automatic rollback.
    """
    session_factory = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async with session_factory() as session:
        # Begin transaction
        await session.begin()

        yield session

        # Rollback transaction (ensures test isolation)
        await session.rollback()


# ==================== Redis Fixtures ====================

@pytest_asyncio.fixture(scope="function")
async def mock_redis() -> AsyncGenerator[AsyncMock, None]:
    """
    Mock Redis client for testing without actual Redis connection.
    """
    mock = AsyncMock(spec=Redis)

    # Setup in-memory storage for mock Redis
    storage = {}

    async def mock_get(key: str):
        return storage.get(key)

    async def mock_set(key: str, value, ex=None, nx=False, xx=False):
        if nx and key in storage:
            return False
        if xx and key not in storage:
            return False
        storage[key] = value
        return True

    async def mock_delete(key: str):
        if key in storage:
            del storage[key]
            return 1
        return 0

    async def mock_exists(key: str):
        return 1 if key in storage else 0

    async def mock_ping():
        return True

    mock.get.side_effect = mock_get
    mock.set.side_effect = mock_set
    mock.delete.side_effect = mock_delete
    mock.exists.side_effect = mock_exists
    mock.ping.side_effect = mock_ping

    yield mock


@pytest_asyncio.fixture(scope="function")
async def redis_client(mock_redis) -> AsyncGenerator[AsyncMock, None]:
    """
    Provide a mocked Redis client for testing.
    Automatically patches redis_manager._client.
    """
    original_client = redis_manager._client
    original_initialized = redis_manager._initialized

    redis_manager._client = mock_redis
    redis_manager._initialized = True

    yield mock_redis

    # Restore original state
    redis_manager._client = original_client
    redis_manager._initialized = original_initialized


# ==================== FastAPI Test Client ====================

@pytest_asyncio.fixture(scope="function")
async def test_app() -> FastAPI:
    """
    Create a FastAPI test application.
    """
    from src.app import app
    return app


@pytest_asyncio.fixture(scope="function")
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP test client.
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ==================== User Fixtures ====================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """
    Create a test user in the database.
    """
    user = User(
        id=uuid4(),
        email="testuser@example.com",
        username="testuser",
        password_hash=PasswordHasher.hash("Test@1234"),
        full_name="Test User",
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """
    Create an admin test user.
    """
    user = User(
        id=uuid4(),
        email="admin@example.com",
        username="admin",
        password_hash=PasswordHasher.hash("Admin@1234"),
        full_name="Admin User",
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(db_session: AsyncSession) -> User:
    """
    Create an inactive test user.
    """
    user = User(
        id=uuid4(),
        email="inactive@example.com",
        username="inactive",
        password_hash=PasswordHasher.hash("Inactive@1234"),
        is_active=False,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ==================== Authentication Fixtures ====================

@pytest.fixture
def test_tokens(test_user: User) -> dict:
    """
    Generate access and refresh tokens for test user.
    """
    token_pair = JWTManager.create_token_pair(
        user_id=str(test_user.id),
        email=test_user.email,
        username=test_user.username,
        roles=["user"],
        permissions=[]
    )
    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": token_pair.token_type,
    }


@pytest.fixture
def admin_tokens(admin_user: User) -> dict:
    """
    Generate tokens for admin user.
    """
    token_pair = JWTManager.create_token_pair(
        user_id=str(admin_user.id),
        email=admin_user.email,
        username=admin_user.username,
        roles=["admin", "user"],
        permissions=["users:read", "users:write", "users:delete"]
    )
    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": token_pair.token_type,
    }


@pytest.fixture
def auth_headers(test_tokens: dict) -> dict:
    """
    Create authorization headers for API requests.
    """
    return {"Authorization": f"Bearer {test_tokens['access_token']}"}


@pytest.fixture
def admin_auth_headers(admin_tokens: dict) -> dict:
    """
    Create admin authorization headers.
    """
    return {"Authorization": f"Bearer {admin_tokens['access_token']}"}


# ==================== Mock Factories ====================

@pytest.fixture
def mock_password_manager():
    """Mock password manager."""
    mock = MagicMock()
    mock.hash_password.return_value = "$2b$12$mockedhashvalue"
    mock.verify_password.return_value = True
    return mock


@pytest.fixture
def mock_jwt_manager():
    """Mock JWT manager."""
    mock = MagicMock()
    mock.create_token_pair.return_value = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "token_type": "bearer",
        "expires_in": 900,
    }
    return mock
