from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Set


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    LOGGING_LEVEL: str = Field(default="INFO")
    LOGGING_BACKUP_DAYS: int = Field(default=30)
    LOGGING_JSON_FORMAT: bool = Field(default=True)
    LOGGING_REQUEST_BODY: bool = Field(default=True)
    LOGGING_RESPONSE_BODY: bool = Field(default=False)
    LOGGING_REQUEST_BODY_MAX_SIZE: int = Field(default=10000)  # bytes
    LOGGING_SLOW_REQUEST_THRESHOLD: float = Field(default=1.0)  # seconds

    LOGGING_SENSITIVE_HEADERS: Set[str] = {
        "authorization",
        "cookie",
        "x-api-key",
        "x-auth-token",
        "api-key",
    }
    
    LOGGING_SENSITIVE_BODY_FIELDS: Set[str] = {
        "password",
        "token",
        "secret",
        "api_key",
        "access_token",
        "refresh_token",
        "credit_card",
        "ssn",
    }
    

logging_settings = LoggingSettings()