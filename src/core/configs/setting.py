from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import warnings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==================== APP SETTINGS ====================
    APP_NAME: str = Field(default="FastAPI Base")
    APP_ENV: str = Field(default="development")
    APP_TIMEZONE: str = Field(default="Asia/Tokyo") 
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000, ge=1, le=65535)
    APP_ROUTER_PREFIX: str = Field(default="/api/v1")
    APP_VERSION: str = Field(default="1.0.0")

    # ==================== CORS SETTINGS ====================
    CORS_ORIGINS: str = Field(...)  # Required, no default
    CORS_CREDENTIALS: bool = Field(default=True)
    CORS_METHODS: str = Field(default="GET,POST,PUT,DELETE,PATCH,OPTIONS")
    CORS_HEADERS: str = Field(default="Content-Type,Authorization,X-Request-ID")

    # ==================== DATABASE SETTINGS ====================
    DB_HOST: str = Field(...)
    DB_PORT: int = Field(default=5432, ge=1, le=65535)
    DB_USER: str = Field(...)
    DB_PASSWORD: str = Field(...)
    DB_NAME: str = Field(...)
    DB_ECHO: bool = Field(default=False)
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1)
    DB_POOL_RECYCLE: int = Field(default=3600, ge=60)
    DB_POOL_PRE_PING: bool = Field(default=True)

    # Read Database (Optional)
    DB_READ_HOST: Optional[str] = None
    DB_READ_PORT: Optional[int] = Field(default=None, ge=1, le=65535)
    DB_READ_USER: Optional[str] = None
    DB_READ_PASSWORD: Optional[str] = None
    DB_READ_NAME: Optional[str] = None
    DB_READ_POOL_SIZE: int = Field(default=10, ge=1, le=100)
    DB_READ_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)

    # ==================== REDIS SETTINGS ====================
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379, ge=1, le=65535)
    REDIS_DB: int = Field(default=0, ge=0, le=15)
    REDIS_PASSWORD: str = Field(default="")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, ge=10, le=1000)
    REDIS_DECODE_RESPONSES: bool = Field(default=True)
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, ge=1)
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(default=5, ge=1)

    # ==================== JWT SETTINGS ====================
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, ge=1)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1)
    JWT_ISSUER: str = Field(default="fastapi-app")
    JWT_AUDIENCE: str = Field(default="fastapi-users")

    # ==================== SECURITY ====================
    ENABLE_SECURITY_HEADERS: bool = Field(default=True)
    BCRYPT_ROUNDS: int = Field(default=12, ge=10, le=15)
    PASSWORD_MIN_LENGTH: int = Field(default=8, ge=8)
    
    # ==================== RATE LIMITING ====================
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: str = Field(default="60/minute")
    RATE_LIMIT_STORAGE_URL: Optional[str] = None

    # ==================== LOGGING ====================
    LOGGING_LEVEL: str = Field(default="INFO")
    LOGGING_JSON_FORMAT: bool = Field(default=True)
    
    # ==================== VALIDATORS ====================
    
    @field_validator("APP_ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}")
        return v
    
    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        weak_secrets = {"your-secret-key", "secret", "password", "changeme", "12345678"}
        if v.lower() in weak_secrets:
            raise ValueError("JWT_SECRET_KEY is too weak")
        return v
    
    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("CORS_ORIGINS cannot be empty")
        if "*" in v:
            raise ValueError("CORS_ORIGINS cannot contain '*' wildcard for security")
        origins = [o.strip() for o in v.split(",")]
        for origin in origins:
            if not origin.startswith(("http://", "https://")):
                raise ValueError(f"Invalid CORS origin format: {origin}")
        return v
    
    @field_validator("DB_PASSWORD")
    @classmethod
    def validate_db_password(cls, v: str) -> str:
        if not v or len(v) < 8:
            raise ValueError("DB_PASSWORD must be at least 8 characters")
        return v
    
    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        allowed = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"}
        if v not in allowed:
            raise ValueError(f"JWT_ALGORITHM must be one of {allowed}")
        return v
    
    @model_validator(mode='after')
    def validate_production_settings(self) -> 'Settings':
        """Extra validation for production environment"""
        if self.APP_ENV == "production":
            if len(self.JWT_SECRET_KEY) < 64:
                raise ValueError("Production JWT_SECRET_KEY should be at least 64 characters")
            
            if self.DB_ECHO:
                raise ValueError("DB_ECHO must be False in production")
            
            if not self.RATE_LIMIT_ENABLED:
                raise ValueError("RATE_LIMIT_ENABLED must be True in production")
            
            if not self.ENABLE_SECURITY_HEADERS:
                raise ValueError("ENABLE_SECURITY_HEADERS must be True in production")
        
        return self

    # ==================== PROPERTIES ====================
    
    @property
    def has_read_db(self) -> bool:
        return bool(self.DB_READ_HOST)

    @property
    def REDIS_URL(self) -> str:
        pwd = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{pwd}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def JWT_ACCESS_TOKEN_EXPIRE_SECONDS(self) -> int:
        return self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    @property
    def JWT_REFRESH_TOKEN_EXPIRE_SECONDS(self) -> int:
        return self.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


# Initialize and validate settings
try:
    settings = Settings()  # type: ignore
except Exception as e:
    raise RuntimeError(f"[FATAL] Settings validation failed: {e}")


# Development auto-generation
if settings.APP_ENV == "development":
    if settings.JWT_SECRET_KEY == "dev-secret-key-change-in-production":
        warnings.warn("Using development JWT secret. Generate secure one for production!")