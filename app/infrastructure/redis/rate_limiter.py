"""Redis ZSet 滑动窗口限流（FR-6a）。

用 ZSet 而不是简单计数器：固定窗口计数器在窗口边界会放过两倍流量
（比如 10s/3 次，在第 9.9s 和第 10.1s 各放 3 次）。ZSet 以时间戳为 score，
每次先把窗口外的成员清掉再计数，得到的是真正的滑动窗口。

四个操作合并进一个 Lua 脚本，否则 ZCARD 与 ZADD 之间会有竞态。
"""

import uuid

from redis import Redis

from app.infrastructure.redis import keys

_SLIDING_WINDOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_count = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
if redis.call('ZCARD', key) >= max_count then return 0 end
redis.call('ZADD', key, now, member)
redis.call('PEXPIRE', key, window)
return 1
"""


class RedisRateLimiter:
    def __init__(self, client: Redis):
        self._script = client.register_script(_SLIDING_WINDOW)
        self._client = client

    def allow(self, activity_id: int, user_id: str, window_seconds: int, max_count: int) -> bool:
        # 毫秒精度：秒级精度下同一秒内的多次请求会挤在同一个 score 上。
        now_ms = int(self._client.time()[0] * 1000 + self._client.time()[1] / 1000)
        # member 必须唯一。Java 版当年用时间戳同时作 score 和 member，
        # 同一毫秒内的两次请求会被 ZADD 去重成一个，限流因此偏松。
        member = uuid.uuid4().hex
        allowed = self._script(
            keys=[keys.rate_limit(activity_id, user_id)],
            args=[now_ms, window_seconds * 1000, max_count, member],
        )
        return int(allowed) == 1
