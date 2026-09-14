from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "lottery-python"
    database_url: str = "sqlite:///./lottery.db"

    # FR-6a 频率限流（防滥用）。窗口与阈值必须可配置，不得硬编码。
    # 注意：这与 FR-6b 的「每人每日参与次数」是两个不同的东西——前者是秒级防刷，
    # 后者是日级业务配额，取值来自 activity.daily_limit。
    rate_limit_window_seconds: int = 10
    rate_limit_max_count: int = 3

    # Phase 2 接入 Redis 时启用（当前为占位，见缺陷 D8）。
    redis_url: str = "redis://localhost:6379/0"
    enable_redis: bool = False


settings = Settings()
