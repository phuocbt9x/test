from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = Field(default="FastAPI Base")
    APP_ENV: str = Field(default="development")
    APP_TIMEZONE: str = Field(default="Asia/Tokyo") 
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)
    APP_ROUTER_PREFIX: str = Field(default="/api/v1")

    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:8000")
    CORS_CREDENTIALS: bool = Field(default=True)
    CORS_METHODS: str = Field(default="GET,POST,PUT,DELETE,OPTIONS")
    CORS_HEADERS: str = Field(default="*")

    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="postgres")
    DB_NAME: str = Field(default="fastapi")
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries")
    DB_POOL_SIZE: int = Field(default=5, description="Write DB pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Write DB max overflow")

    # Read Database (Optional)
    DB_READ_HOST: Optional[str] = Field(default=None, description="Read DB host")
    DB_READ_PORT: Optional[int] = Field(default=None, description="Read DB port")
    DB_READ_USER: Optional[str] = Field(default=None, description="Read DB user")
    DB_READ_PASSWORD: Optional[str] = Field(default=None, description="Read DB password")
    DB_READ_NAME: Optional[str] = Field(default=None, description="Read DB name")
    DB_READ_POOL_SIZE: int = Field(default=10, description="Read DB pool size")
    DB_READ_MAX_OVERFLOW: int = Field(default=20, description="Read DB max overflow")

    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: str = Field(default="")
    REDIS_MAX_CONNECTIONS: int = Field(default=100)
    REDIS_DECODE_RESPONSES: bool = Field(default=True)

    JWT_SECRET: str = Field(min_length=32)  # type: ignore
    JWT_EXPIRES: int = Field(default=3600)
    JWT_REFRESH_EXPIRES: int = Field(default=86400)

    LOG_LEVEL: str = Field(default="INFO")
    LOG_BACKUP_DAYS: int = Field(default=30)

    RATE_LIMIT_ENABLED: bool = Field(default=False)
    RATE_LIMIT_PER_MINUTE: str = Field(default="100/minute")

    @property
    def has_read_db(self) -> bool:
        return bool(self.DB_READ_HOST)

    @property
    def REDIS_URL(self) -> str:
        pwd = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{pwd}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()  # type: ignore


if not settings.JWT_SECRET or len(settings.JWT_SECRET) < 32:
    raise RuntimeError("[FATAL] JWT_SECRET must be at least 32 characters and not empty!")
if not settings.DB_PASSWORD or settings.DB_PASSWORD.strip() == "":
    raise RuntimeError("[FATAL] DB_PASSWORD must not be empty!")
if not settings.CORS_ORIGINS or settings.CORS_ORIGINS.strip() == "" or settings.CORS_ORIGINS.strip() == "*":
    raise RuntimeError("[FATAL] CORS_ORIGINS must not be '*' or empty!")
