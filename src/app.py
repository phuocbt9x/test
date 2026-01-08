from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request

from src.core import (
    auto_load_routers,
    get_logger,
    limiter,
    logging_settings,
    print_routes_table,
    settings,
    Environment,
    setup_exception_handlers,
    setup_logging,
    setup_middlewares,
    redis_manager,
    db,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(
        logging_settings.LOGGING_JSON_FORMAT,
        logging_settings.LOGGING_LEVEL,
    )
    try:
        await db.init()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        raise RuntimeError("Database initialization failed") from e

    try:
        await redis_manager.init()
        logger.info("Redis initialized")
    except Exception as e:
        logger.error("Redis initialization failed: %s", e)
        logger.warning("Application will continue without Redis")

    try:
        db_health = await db.health_check()
        logger.info("Database health: %s", db_health.get("write_db"))

        if redis_manager.is_initialized:
            redis_health = await redis_manager.health_check()
            logger.info("Redis health: %s", redis_health.get("status"))
    except Exception as e:
        logger.warning("Health check warning: %s", e)

    if settings.APP_ENV == Environment.DEVELOPMENT:
        print_routes_table(app)

    logger.info("Application startup complete")

    yield

    logger.info("Application shutting down...")

    if redis_manager.is_initialized:
        try:
            await redis_manager.close()
            logger.info("Redis closed")
        except Exception as e:
            logger.error("Redis close error: %s", e)

    if db.is_initialized:
        try:
            await db.close()
            logger.info("Database closed")
        except Exception as e:
            logger.error("Database close error: %s", e)

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        docs_url="/docs" if settings.APP_ENV == Environment.DEVELOPMENT else None,
        redoc_url="/redoc" if settings.APP_ENV == Environment.DEVELOPMENT else None,
        openapi_url=(
            f"{settings.APP_ROUTER_PREFIX}/openapi.json"
            if settings.APP_ENV == Environment.DEVELOPMENT
            else None
        ),
        lifespan=lifespan,
    )

    setup_middlewares(app)
    setup_exception_handlers(app)
    auto_load_routers(
        app=app,
        modules_dir="src/modules",
        prefix=settings.APP_ROUTER_PREFIX,
        parallel=True,
    )
    logger.info("Routers loaded")

    @app.get("/", tags=["Root"])
    @limiter.exempt
    async def root(request: Request) -> dict[str, Any]:
        return {
            "message": "Welcome to FastAPI Clean Architecture",
            "app": settings.APP_NAME,
            "version": "0.1.0",
            "docs": "/docs" if settings.APP_ENV == Environment.DEVELOPMENT else None,
            "health": "/health",
        }

    @app.get("/health", tags=["Health"])
    @limiter.exempt
    async def health_check() -> dict[str, Any]:
        health_status: dict[str, Any] = {
            "status": "healthy",
            "app": {
                "name": settings.APP_NAME,
                "env": settings.APP_ENV,
                "timezone": settings.APP_TIMEZONE,
            },
        }

        try:
            db_health = await db.health_check()
            health_status["database"] = db_health

            if "unhealthy" in str(db_health):
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["database"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "unhealthy"

        try:
            if redis_manager.is_initialized:
                redis_health = await redis_manager.health_check()
                health_status["redis"] = redis_health

                if redis_health.get("status") != "healthy":
                    logger.warning("Redis is %s", redis_health.get("status"))
            else:
                health_status["redis"] = {"status": "not_initialized"}
        except Exception as e:
            health_status["redis"] = {"status": "unhealthy", "error": str(e)}
            logger.warning("Redis health check failed: %s", e)

        return health_status

    @app.get("/health/database", tags=["Health"])
    @limiter.exempt
    async def database_health() -> dict[str, Any]:
        return await db.health_check()

    @app.get("/health/redis", tags=["Health"])
    @limiter.exempt
    async def redis_health() -> dict[str, Any]:
        if not redis_manager.is_initialized:
            return {"status": "not_initialized"}
        return await redis_manager.health_check()

    if settings.APP_ENV == Environment.DEVELOPMENT:

        @app.get("/debug/cache/keys", tags=["Debug"])
        async def list_cache_keys(pattern: str = "*") -> dict[str, Any]:
            keys = await redis_manager.keys(pattern)
            return {
                "pattern": pattern,
                "count": len(keys),
                "keys": keys[:100],
            }

        @app.delete("/debug/cache/flush", tags=["Debug"])
        async def flush_cache() -> dict[str, Any]:
            success = await redis_manager.flushdb()
            return {
                "success": success,
                "message": "Cache flushed" if success else "Failed",
            }

    return app


app = create_app()
