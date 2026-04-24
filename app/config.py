from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://agrismart:agrismart_secret_2024@localhost:5432/cropdb"
    DATABASE_URL_SYNC: str = "postgresql://agrismart:agrismart_secret_2024@localhost:5432/cropdb"
    JWT_SECRET: str = "agrismart-jwt-super-secret-key-change-me-in-production-2024"
    JWT_ALGORITHM: str = "HS256"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    OPENWEATHER_API_KEY: str = "your_openweathermap_api_key_here"
    PORT: int = 8002
    LOG_LEVEL: str = "info"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
