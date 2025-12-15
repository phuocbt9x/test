from enum import Enum
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import warnings
import re


class Environment(str, Enum):
    """Application environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class JWTAlgorithm(str, Enum):
    """Supported JWT algorithms"""
    HS256 = "HS256"
    HS384 = "HS384"
    HS512 = "HS512"
    RS256 = "RS256"
    RS384 = "RS384"
    RS512 = "RS512"
    ES256 = "ES256"
    ES384 = "ES384"
    ES512 = "ES512"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==================== APP SETTINGS ====================
    APP_NAME: str = Field(default="FastAPI Base")
    APP_ENV: Environment = Field(default=Environment.DEVELOPMENT)
    APP_TIMEZONE: str = Field(default="Asia/Tokyo") 
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000, ge=1, le=65535)
    APP_ROUTER_PREFIX: str = Field(default="/api/v1")
    APP_VERSION: str = Field(default="1.0.0")

    # ==================== CORS SETTINGS ====================
    CORS_ORIGINS: str = Field(...)
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
    DB_POOL_SIZE: int = Field(default=20, ge=5, le=100)
    DB_MAX_OVERFLOW: int = Field(default=40, ge=10, le=100)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1)
    DB_POOL_RECYCLE: int = Field(default=1800, ge=60)
    DB_POOL_PRE_PING: bool = Field(default=True)

    # Read Database (Optional)
    DB_READ_HOST: Optional[str] = None
    DB_READ_PORT: Optional[int] = Field(default=None, ge=1, le=65535)
    DB_READ_USER: Optional[str] = None
    DB_READ_PASSWORD: Optional[str] = None
    DB_READ_NAME: Optional[str] = None
    DB_READ_POOL_SIZE: int = Field(default=30, ge=10, le=100)
    DB_READ_MAX_OVERFLOW: int = Field(default=60, ge=20, le=100)

    # ==================== REDIS SETTINGS ====================
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379, ge=1, le=65535)
    REDIS_DB: int = Field(default=0, ge=0, le=15)
    REDIS_PASSWORD: str = Field(default="")
    REDIS_MAX_CONNECTIONS: int = Field(default=100, ge=50, le=1000)
    REDIS_DECODE_RESPONSES: bool = Field(default=True)
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, ge=1)
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(default=5, ge=1)

    # ==================== JWT SETTINGS ====================
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: JWTAlgorithm = Field(default=JWTAlgorithm.HS256)
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=5, le=60)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=30)
    JWT_ISSUER: str = Field(default="fastapi-app")
    JWT_AUDIENCE: str = Field(default="fastapi-users")

    # ==================== SECURITY ====================
    ENABLE_SECURITY_HEADERS: bool = Field(default=True)
    BCRYPT_ROUNDS: int = Field(default=12, ge=10, le=15)
    PASSWORD_MIN_LENGTH: int = Field(default=8, ge=8)

    MAX_LOGIN_ATTEMPTS: int = Field(default=5, ge=3, le=10)
    ACCOUNT_LOCKOUT_DURATION: int = Field(default=900, ge=300)
    SESSION_TIMEOUT: int = Field(default=3600, ge=600)
    ENABLE_2FA: bool = Field(default=False)
    
    # ==================== RATE LIMITING ====================
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: str = Field(default="60/minute")
    RATE_LIMIT_STORAGE_URL: Optional[str] = None
    RATE_LIMIT_PER_USER_MINUTE: int = Field(default=100, ge=10)
    RATE_LIMIT_ANONYMOUS_MINUTE: int = Field(default=10, ge=5)

    # ==================== LOGGING ====================
    LOGGING_LEVEL: str = Field(default="INFO")
    LOGGING_JSON_FORMAT: bool = Field(default=True)
    LOGGING_REQUEST_BODY: bool = Field(default=False)
    LOGGING_RESPONSE_BODY: bool = Field(default=False)
    
    # ==================== VALIDATORS ====================
    # Note: APP_ENV and JWT_ALGORITHM are validated automatically by Enum types

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 64:
            raise ValueError("JWT_SECRET_KEY must be at least 64 characters for production security")
        
        weak_secrets = {
            "your-secret-key", "secret", "password", "changeme", "12345678",
            "dev-secret-key-change-in-production",
            "CHANGE_THIS_TO_SECURE_RANDOM_64_CHARACTER_STRING_IN_PRODUCTION"
        }
        if v.lower() in weak_secrets or any(weak in v.lower() for weak in weak_secrets):
            raise ValueError("JWT_SECRET_KEY is using a default/weak value. Generate a secure key!")
        
        if not (any(c.isupper() for c in v) and any(c.islower() for c in v) and any(c.isdigit() for c in v)):
            warnings.warn("JWT_SECRET_KEY should contain uppercase, lowercase, and digits for better entropy")
        
        return v
    
    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("CORS_ORIGINS cannot be empty")
        
        if "*" in v:
            raise ValueError("CORS_ORIGINS cannot contain '*' wildcard for security")
        
        origins = [o.strip() for o in v.split(",")]
        
        url_pattern = re.compile(
            r'^https?://'
            r'(?:[a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+'
            r'(?::\d+)?'
            r'(?:/.*)?$'
        )
        
        for origin in origins:
            if not url_pattern.match(origin):
                raise ValueError(f"Invalid CORS origin format: {origin}. Must be full URL with protocol")
            
            if origin.startswith("http://") and not origin.startswith("http://localhost"):
                warnings.warn(f"CORS origin {origin} uses insecure HTTP protocol")
        
        return v
    
    @field_validator("DB_PASSWORD")
    @classmethod
    def validate_db_password(cls, v: str) -> str:
        if not v or len(v) < 12:
            raise ValueError("DB_PASSWORD must be at least 12 characters")
        
        weak_passwords = {
            "postgres", "password", "admin", "root", "12345678",
            "your_secure_password_here_min_8_chars"
        }
        if v.lower() in weak_passwords:
            raise ValueError("DB_PASSWORD is too weak or using default value")
        
        return v
    
    @field_validator("REDIS_PASSWORD")
    @classmethod
    def validate_redis_password(cls, v: str) -> str:
        if v and len(v) < 16:
            raise ValueError("REDIS_PASSWORD should be at least 16 characters if set")
        return v

    @model_validator(mode='after')
    def validate_production_settings(self) -> 'Settings':
        """Extra validation for production environment"""
        if self.APP_ENV == Environment.PRODUCTION:
            if len(self.JWT_SECRET_KEY) < 64:
                raise ValueError("Production JWT_SECRET_KEY must be at least 64 characters")
            
            if self.DB_ECHO:
                raise ValueError("DB_ECHO must be False in production (performance impact)")
            
            if not self.RATE_LIMIT_ENABLED:
                raise ValueError("RATE_LIMIT_ENABLED must be True in production")
            
            if not self.ENABLE_SECURITY_HEADERS:
                raise ValueError("ENABLE_SECURITY_HEADERS must be True in production")
            
            if self.LOGGING_REQUEST_BODY or self.LOGGING_RESPONSE_BODY:
                warnings.warn("Consider disabling body logging in production for performance")
            
            if "localhost" in self.CORS_ORIGINS.lower():
                warnings.warn("Production CORS should not include localhost origins")
            
            if self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 30:
                warnings.warn("Access token lifetime >30min not recommended for production")
            
            if self.DB_POOL_SIZE < 20:
                warnings.warn("DB_POOL_SIZE <20 may cause performance issues under load")
        
        if self.APP_ENV == Environment.STAGING:
            if self.DB_ECHO:
                warnings.warn("Consider disabling DB_ECHO in staging for performance testing")

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

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == Environment.DEVELOPMENT


# Initialize and validate settings
try:
    settings = Settings()  # type: ignore
except Exception as e:
    raise RuntimeError(f"[FATAL] Settings validation failed: {e}")


if settings.APP_ENV == Environment.DEVELOPMENT:
    if len(settings.JWT_SECRET_KEY) < 64:
        warnings.warn(
            "\nWARNING: JWT_SECRET_KEY is too short!\n"
            "   Generate a secure key for production:\n"
            "   python -c \"import secrets; print(secrets.token_urlsafe(64))\"\n"
        )