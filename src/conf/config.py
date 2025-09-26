# class Config:
#     DB_URL = "postgresql+asyncpg://admin:12345@localhost:5432/contacts_db"


# config = Config


from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_SECONDS: int = 3600
    JWT_REFRESH_EXPIRATION_SECONDS: int = 86400
    RESET_TOKEN_EXPIRATION_SECONDS: int = 900
    model_config = ConfigDict(
        extra="ignore", env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SSL: bool = False
    REDIS_CACHE_TTL_SECONDS: int = 300


settings = Settings()
