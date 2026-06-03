from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    MFA_TOKEN_EXPIRE_MINUTES: int = 5
    RECOVERY_TOKEN_EXPIRE_MINUTES: int = 30
    LOGIN_RATE_LIMIT: str = "5/60seconds"

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def encryption_key_exact_length(cls, v: str) -> str:
        if len(v) != 32:
            raise ValueError("ENCRYPTION_KEY must be exactly 32 characters")
        return v
