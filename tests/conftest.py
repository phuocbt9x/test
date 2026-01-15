import os
import sys
from pathlib import Path

_DEFAULT_TEST_ENV = {
    "APP_ENV": "development",
    "APP_NAME": "TIMIMA_TEST",
    "APP_HOST": "0.0.0.0",
    "APP_PORT": "8000",
    "APP_ROUTER_PREFIX": "/api/v1",
    "APP_TIMEZONE": "Asia/Tokyo",
    "CORS_ORIGINS": "http://localhost:3000,http://localhost:8000",
    "CORS_CREDENTIALS": "true",
    "CORS_METHODS": "GET,POST,PUT,DELETE,PATCH,OPTIONS",
    "CORS_HEADERS": "Content-Type,Authorization,X-Request-ID",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_USER": "test_user",
    "DB_PASSWORD": "test_password_min_12_chars",
    "DB_NAME": "test_db",
    "DB_ECHO": "false",
    "DB_POOL_SIZE": "5",
    "DB_MAX_OVERFLOW": "10",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_DB": "0",
    "REDIS_PASSWORD": "",
    "JWT_SECRET_KEY": "test_secret_key_for_testing_only_min_64_chars_required_for_validation_abc123",
    "JWT_ALGORITHM": "HS256",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "60",
    "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "7",
    "LOGGING_LEVEL": "ERROR",
}

if "--dev" in sys.argv:
    env_example_path = Path(".env.example")
    if env_example_path.exists():
        from dotenv import dotenv_values

        example_vars = dotenv_values(env_example_path)
        _DEFAULT_TEST_ENV.update({k: v for k, v in example_vars.items() if v})

for key, value in _DEFAULT_TEST_ENV.items():
    if key not in os.environ:
        os.environ[key] = str(value)

# ruff: noqa: E402
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src import create_app
from src.core.configs.database import Base, db
from src.core.configs.redis import redis_manager


def pytest_addoption(parser):
    parser.addoption(
        "--dev",
        action="store_true",
        default=False,
        help="Load .env.example for test environment",
    )


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)


@pytest.fixture(scope="session")
def test_db_url() -> str:
    return "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="session")
async def test_engine(test_db_url: str) -> AsyncGenerator[AsyncEngine, None]:
    import os
    from datetime import datetime
    from datetime import timezone as dt_timezone

    from sqlalchemy import event as sa_event

    # Remove test database if exists
    if test_db_url.startswith("sqlite"):
        db_path = test_db_url.replace("sqlite+aiosqlite:///", "")
        if os.path.exists(db_path):
            os.remove(db_path)

    engine = create_async_engine(
        test_db_url,
        echo=False,
        connect_args={"check_same_thread": False},
        pool_pre_ping=False,
    )

    def make_tz_aware(target, context):
        for attr_name in dir(target):
            if not attr_name.startswith("_"):
                try:
                    attr_value = getattr(target, attr_name)
                    if isinstance(attr_value, datetime) and attr_value.tzinfo is None:
                        setattr(
                            target,
                            attr_name,
                            attr_value.replace(tzinfo=dt_timezone.utc),
                        )
                except Exception:
                    pass

    for mapper in Base.registry.mappers:
        sa_event.listen(mapper.class_, "load", make_tz_aware, propagate=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine

    await engine.dispose()

    if test_db_url.startswith("sqlite"):
        db_path = test_db_url.replace("sqlite+aiosqlite:///", "")
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest_asyncio.fixture(scope="session")
async def setup_test_db(test_engine: AsyncEngine) -> None:
    pass


@pytest.fixture
async def test_session(
    test_engine: AsyncEngine, setup_test_db: None
) -> AsyncGenerator[AsyncSession, None]:
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_app(
    test_engine: AsyncEngine,
) -> AsyncGenerator[FastAPI, None]:
    db._initialized = True
    db._write_engine = test_engine
    db._read_engine = test_engine
    db._write_session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    db._read_session_factory = db._write_session_factory

    redis_manager._initialized = False

    app = create_app()

    yield app

    db._initialized = False
    db._write_engine = None
    db._read_engine = None
    db._write_session_factory = None
    db._read_session_factory = None


@pytest.fixture
async def test_client(
    test_app: FastAPI, test_engine: AsyncEngine
) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        follow_redirects=True,
    ) as client:
        yield client

    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
