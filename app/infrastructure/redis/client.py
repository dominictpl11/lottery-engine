"""Redis 连接。

Redis 在本项目里不是可选的缓存加速层，而是**并发正确性的依赖**：
原子库存、分布式限流、幂等都靠它。因此不提供"没有 Redis 就降级到进程内实现"
的开关——进程内实现在多 worker 下根本不成立，静默降级只会把超卖问题藏起来。

Redis 不可用时的策略是**快速失败**（见 app/core/exceptions.py 的
DependencyUnavailableError），抽奖接口返回 503，而不是放行。
"""

from functools import lru_cache

import redis

from app.core.config import settings


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=settings.redis_socket_timeout,
        socket_connect_timeout=settings.redis_socket_timeout,
        health_check_interval=30,
    )


def ping() -> bool:
    """启动自检用。连不上直接抛 redis.RedisError。"""
    return bool(get_redis().ping())
