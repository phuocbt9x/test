from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse

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
    storage_manager,
    mail_manager,
)

logger = get_logger(__name__)

HEALTH_STATUS_HEALTHY = "healthy"
HEALTH_STATUS_DEGRADED = "degraded"
HEALTH_STATUS_UNHEALTHY = "unhealthy"
HEALTH_STATUS_NOT_INITIALIZED = "not_initialized"
MAX_CACHE_KEYS_DISPLAY = 100


def is_development() -> bool:
    return settings.APP_ENV == Environment.DEVELOPMENT


async def initialize_database() -> None:
    try:
        await db.init()
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        raise RuntimeError("Database initialization failed") from e


async def initialize_redis() -> None:
    try:
        await redis_manager.init()
    except Exception as e:
        logger.error("Redis initialization failed: %s", e)
        raise RuntimeError("Redis initialization failed") from e


async def initialize_storage() -> None:
    try:
        storage_manager.initialize()
    except Exception as e:
        logger.error("Storage initialization failed: %s", e)
        raise RuntimeError("Storage initialization failed") from e


async def initialize_mail() -> None:
    try:
        mail_manager.initialize()
    except Exception as e:
        logger.error("Mail initialization failed: %s", e)
        raise RuntimeError("Mail initialization failed") from e


async def perform_startup_health_checks() -> None:
    try:
        await db.health_check()
        if redis_manager.is_initialized:
            await redis_manager.health_check()
    except Exception as e:
        logger.warning("Health check warning: %s", e)


async def shutdown_redis() -> None:
    if redis_manager.is_initialized:
        try:
            await redis_manager.close()
        except Exception as e:
            logger.error("Redis close error: %s", e)


async def shutdown_database() -> None:
    if db.is_initialized:
        try:
            await db.close()
        except Exception as e:
            logger.error("Database close error: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(
        logging_settings.LOGGING_JSON_FORMAT,
        logging_settings.LOGGING_LEVEL,
    )

    await initialize_database()
    await initialize_redis()
    await initialize_storage()
    await initialize_mail()
    await perform_startup_health_checks()

    if is_development():
        print_routes_table(app)

    yield

    await shutdown_redis()
    await shutdown_database()


def setup_static_files_handler(app: FastAPI) -> None:
    base_dir = Path(settings.STORAGE_LOCAL_BASE_DIR)
    base_dir.mkdir(parents=True, exist_ok=True)

    @app.exception_handler(status.HTTP_404_NOT_FOUND)
    async def static_files_handler(request: Request, exc: HTTPException):
        file_path = base_dir / request.url.path.lstrip("/")
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Not Found"},
        )


def _get_docs_url() -> str | None:
    return "/docs" if is_development() else None


def _get_redoc_url() -> str | None:
    return "/redoc" if is_development() else None


def _get_openapi_url() -> str | None:
    if is_development():
        return f"{settings.APP_ROUTER_PREFIX}/openapi.json"
    return None


async def _check_database_health() -> dict[str, Any]:
    try:
        db_health = await db.health_check()
        if HEALTH_STATUS_UNHEALTHY in str(db_health):
            return {"health": db_health, "status": HEALTH_STATUS_DEGRADED}
        return {"health": db_health, "status": HEALTH_STATUS_HEALTHY}
    except Exception as e:
        return {
            "health": {"status": HEALTH_STATUS_UNHEALTHY, "error": str(e)},
            "status": HEALTH_STATUS_UNHEALTHY,
        }


async def _check_redis_health() -> dict[str, Any]:
    if not redis_manager.is_initialized:
        return {"health": {"status": HEALTH_STATUS_NOT_INITIALIZED}, "status": None}

    try:
        redis_health = await redis_manager.health_check()
        status = redis_health.get("status")
        if status != HEALTH_STATUS_HEALTHY:
            logger.warning("Redis is %s", status)
        return {"health": redis_health, "status": status}
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)
        return {
            "health": {"status": HEALTH_STATUS_UNHEALTHY, "error": str(e)},
            "status": HEALTH_STATUS_UNHEALTHY,
        }


def _determine_overall_health_status(
    db_status: str, redis_status: str | None, current_status: str
) -> str:
    if db_status == HEALTH_STATUS_UNHEALTHY:
        return HEALTH_STATUS_UNHEALTHY

    if db_status == HEALTH_STATUS_DEGRADED:
        return HEALTH_STATUS_DEGRADED

    if (
        redis_status == HEALTH_STATUS_UNHEALTHY
        and current_status == HEALTH_STATUS_HEALTHY
    ):
        return HEALTH_STATUS_DEGRADED

    return current_status


async def _build_health_status() -> dict[str, Any]:
    health_status: dict[str, Any] = {
        "status": HEALTH_STATUS_HEALTHY,
        "app": {
            "name": settings.APP_NAME,
            "env": settings.APP_ENV,
            "timezone": settings.APP_TIMEZONE,
        },
    }

    db_result = await _check_database_health()
    health_status["database"] = db_result["health"]

    redis_result = await _check_redis_health()
    health_status["redis"] = redis_result["health"]

    health_status["status"] = _determine_overall_health_status(
        db_status=db_result["status"],
        redis_status=redis_result["status"],
        current_status=health_status["status"],
    )

    return health_status


def _register_health_endpoints(app: FastAPI) -> None:
    @app.get("/health", tags=["Health"])
    @limiter.exempt
    async def health_check() -> dict[str, Any]:
        return await _build_health_status()

    @app.get("/health/database", tags=["Health"])
    @limiter.exempt
    async def database_health() -> dict[str, Any]:
        return await db.health_check()

    @app.get("/health/redis", tags=["Health"])
    @limiter.exempt
    async def redis_health() -> dict[str, Any]:
        if not redis_manager.is_initialized:
            return {"status": HEALTH_STATUS_NOT_INITIALIZED}
        return await redis_manager.health_check()


def _register_root_endpoint(app: FastAPI) -> None:
    @app.get("/", tags=["Root"], name="root")
    @limiter.exempt
    async def root(request: Request) -> dict[str, Any]:
        return {
            "message": "Welcome to FastAPI Clean Architecture",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": _get_docs_url(),
            "redoc": _get_redoc_url(),
            "health": "/health",
        }


def _register_debug_endpoints(app: FastAPI) -> None:
    @app.get("/debug/cache/keys", tags=["Debug"])
    async def list_cache_keys(pattern: str = "*") -> dict[str, Any]:
        keys = await redis_manager.keys(pattern)
        return {
            "pattern": pattern,
            "count": len(keys),
            "keys": keys[:MAX_CACHE_KEYS_DISPLAY],
        }

    @app.delete("/debug/cache/flush", tags=["Debug"])
    async def flush_cache() -> dict[str, Any]:
        success = await redis_manager.flushdb()
        return {
            "success": success,
            "message": "Cache flushed" if success else "Failed",
        }


def _register_endpoints(app: FastAPI) -> None:
    _register_root_endpoint(app)
    _register_health_endpoints(app)

    if is_development():
        _register_debug_endpoints(app)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        docs_url=_get_docs_url(),
        redoc_url=_get_redoc_url(),
        openapi_url=_get_openapi_url(),
        lifespan=lifespan,
    )

    setup_middlewares(app)
    setup_exception_handlers(app)
    setup_static_files_handler(app)

    _register_endpoints(app)

    auto_load_routers(
        app=app,
        modules_dir="src/modules",
        prefix=settings.APP_ROUTER_PREFIX,
        parallel=True,
    )

    return app


app = create_app()
