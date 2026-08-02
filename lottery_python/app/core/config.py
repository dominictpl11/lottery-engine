from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "lottery-python"
    database_url: str = "sqlite:///./lottery.db"
    redis_url: str = "redis://localhost:6379/0"
    enable_redis: bool = False


settings = Settings()
