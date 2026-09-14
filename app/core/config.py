from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "lottery-python"
    # 正式库为 MySQL（§8.2）。
    # 这里的默认值是**本地开发占位**，与 docker-compose.yml 的默认账号一致，
    # 不是密钥；任何非本地部署都必须通过环境变量 / .env 覆盖 DATABASE_URL（NFR-5）。
    database_url: str = (
        "mysql+pymysql://lottery:[REDACTED_LOCAL_CREDENTIAL]@127.0.0.1:3307/lottery_db?charset=utf8mb4"
    )

    # FR-6a 频率限流（防滥用）。窗口与阈值必须可配置，不得硬编码。
    # 注意：这与 FR-6b 的「每人每日参与次数」是两个不同的东西——前者是秒级防刷，
    # 后者是日级业务配额，取值来自 activity.daily_limit。
    rate_limit_window_seconds: int = 10
    rate_limit_max_count: int = 3

    # Redis 是并发正确性的依赖（原子库存 / 限流 / 幂等），不是可选加速层，
    # 因此没有 enable_redis 开关：连不上就快速失败，不静默降级到进程内实现。
    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_socket_timeout: float = 3.0

    # 数据库连接池。默认的 5+10 在 200 并发下会耗尽并抛 QueuePool timeout，
    # 这是 Phase 4 压测暴露出来的瓶颈，详见 docs/benchmark.md。
    # 约束：workers * (pool_size + max_overflow) 必须小于 MySQL 的 max_connections。
    db_pool_size: int = 40
    db_max_overflow: int = 20
    db_pool_timeout: float = 10.0

    # FR-5 幂等：lock 是"处理中"占位的存活时间（进程中途崩溃后多久允许重试），
    # result 是首次结果的可回放时长。
    idempotency_lock_ttl_seconds: int = 60
    idempotency_result_ttl_seconds: int = 86400

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
