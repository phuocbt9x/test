import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from threading import Lock

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from src.core.configs import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class SingletonMeta(type):
    _instances: dict[type, object] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


class DatabaseManager(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._write_engine: Optional[AsyncEngine] = None
        self._read_engine: Optional[AsyncEngine] = None
        self._write_session_factory: Optional[async_sessionmaker] = None
        self._read_session_factory: Optional[async_sessionmaker] = None
        self._initialized: bool = False
    
    async def init(self) -> None:
        if self._initialized:
            logger.warning("Database already initialized - skipping")
            return

        self._write_engine = self._create_engine(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            is_write=True,
        )
        
        self._write_session_factory = async_sessionmaker(
            bind=self._write_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        logger.info(
            f"✅ Write DB initialized: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME} "
            f"(pool_size={settings.DB_POOL_SIZE}, max_overflow={settings.DB_MAX_OVERFLOW})"
        )
        
        if settings.has_read_db:
            read_host = settings.DB_READ_HOST or settings.DB_HOST
            read_port = settings.DB_READ_PORT or settings.DB_PORT
            read_user = settings.DB_READ_USER or settings.DB_USER
            read_password = settings.DB_READ_PASSWORD or settings.DB_PASSWORD
            read_name = settings.DB_READ_NAME or settings.DB_NAME
            self._read_engine = self._create_engine(
                host=read_host,
                port=read_port,
                user=read_user,
                password=read_password,
                database=read_name,
                pool_size=settings.DB_READ_POOL_SIZE,
                max_overflow=settings.DB_READ_MAX_OVERFLOW,
                is_write=False,
            )
            self._read_session_factory = async_sessionmaker(
                bind=self._read_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            logger.info(
                f"Read DB initialized: {read_host}:{read_port}/{read_name} "
                f"(pool_size={settings.DB_READ_POOL_SIZE}, max_overflow={settings.DB_READ_MAX_OVERFLOW})"
            )
        else:
            self._read_engine = self._write_engine
            self._read_session_factory = self._write_session_factory
            logger.info("Read DB using write DB configuration (no replica)")
        
        self._initialized = True
    
        await self._verify_connections()
    
    def _create_engine(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        pool_size: int,
        max_overflow: int,
        is_write: bool = True,
    ) -> AsyncEngine:
        database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        is_production = getattr(settings, "APP_ENV", "development") == "production"
        poolclass = QueuePool if is_production else NullPool
        engine_args: dict[str, object] = {
            "echo": settings.DB_ECHO,
            "pool_pre_ping": True,
            "poolclass": poolclass,
            "connect_args": {
                "server_settings": {
                    "application_name": f"{settings.APP_NAME}_{'write' if is_write else 'read'}",
                    "jit": "off",
                },
                "command_timeout": 60,
                "timeout": 10,
            },
        }
        if is_production:
            engine_args["pool_size"] = pool_size
            engine_args["max_overflow"] = max_overflow
        return create_async_engine(database_url, **engine_args)
    
    async def _verify_connections(self) -> None:
        try:
            async with self.session(read_only=False) as session:
                await session.execute(text("SELECT 1"))
                logger.info("Write DB connection verified")

            async with self.session(read_only=True) as session:
                await session.execute(text("SELECT 1"))
                logger.info("Read DB connection verified")
        except Exception as e:
            logger.error(f"Database connection verification failed: {e}")
            raise
    
    async def close(self) -> None:
        if not self._initialized:
            logger.warning("Database not initialized - nothing to close")
            return
        
        if self._write_engine:
            await self._write_engine.dispose()
            logger.info("Write DB connection pool closed")
        
        if self._read_engine and self._read_engine != self._write_engine:
            await self._read_engine.dispose()
            logger.info("Read DB connection pool closed")
        
        self._initialized = False
    
    @asynccontextmanager
    async def session(
        self, read_only: bool = False
    ) -> AsyncGenerator[AsyncSession, None]:
        if not self._initialized:
            raise RuntimeError(
                "Database not initialized. Call await db.init() first in app lifespan."
            )
        
        factory = self._read_session_factory if read_only else self._write_session_factory
        
        if factory is None:
            raise RuntimeError("Session factory not available")

        async with factory() as session:
            try:
                yield session
                if not read_only:
                    await session.commit()
                    
            except Exception as e:
                if not read_only:
                    await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                pass
    
    @property
    def write_engine(self) -> AsyncEngine:
        if self._write_engine is None:
            raise RuntimeError("Database not initialized")
        return self._write_engine
    
    @property
    def read_engine(self) -> AsyncEngine:
        if self._read_engine is None:
            raise RuntimeError("Database not initialized")
        return self._read_engine
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    async def create_pgvector_extension(self) -> None:
        async with self.session(read_only=False) as session:
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension ensured")
    
    async def health_check(self) -> dict:
        status: dict[str, object] = {
            "write_db": "unknown",
            "read_db": "unknown",
            "pool_status": {},
        }

        try:
            async with self.session(read_only=False) as session:
                await session.execute(text("SELECT 1"))
                status["write_db"] = "healthy"
        except Exception as e:
            status["write_db"] = f"unhealthy: {str(e)}"

        try:
            async with self.session(read_only=True) as session:
                await session.execute(text("SELECT 1"))
                status["read_db"] = "healthy"
        except Exception as e:
            status["read_db"] = f"unhealthy: {str(e)}"

        pool_status = status["pool_status"]
        if isinstance(pool_status, dict):
            if self._write_engine:
                pool = self._write_engine.pool
                pool_status["write"] = {
                    "size": pool.size() if hasattr(pool, 'size') else 'N/A',
                    "checked_out": pool.checkedout() if hasattr(pool, 'checkedout') else 'N/A',
                }
            if self._read_engine and self._read_engine != self._write_engine:
                pool = self._read_engine.pool
                pool_status["read"] = {
                    "size": pool.size() if hasattr(pool, 'size') else 'N/A',
                    "checked_out": pool.checkedout() if hasattr(pool, 'checkedout') else 'N/A',
                }
        return status


db = DatabaseManager()


async def get_write_db() -> AsyncGenerator[AsyncSession, None]:
    async with db.session(read_only=False) as session:
        yield session


async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
    async with db.session(read_only=True) as session:
        yield session


get_db = get_write_db