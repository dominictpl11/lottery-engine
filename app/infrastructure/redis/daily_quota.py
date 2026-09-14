"""每日参与次数（FR-6b）。

与限流是两件事：限流是秒级防刷，本模块是日级业务配额，上限取
activity.daily_limit，按 Asia/Shanghai 自然日重置。

用「key 里带日期 + TTL 到次日零点」而不是定时清理：key 天然随日期切换，
过期由 Redis 负责，没有需要维护的清理任务。
"""

from redis import Redis

from app.infrastructure.redis import keys

# 先判断再自增，必须原子，否则并发下会超过上限。
_CONSUME = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])
local cur = tonumber(redis.call('GET', key) or '0')
if cur >= limit then return 0 end
local v = redis.call('INCR', key)
if v == 1 then redis.call('EXPIRE', key, ttl) end
return 1
"""

# 归还配额，用于「配额已占用但后续步骤失败」的补偿路径。不会减到负数。
_RELEASE = """
local key = KEYS[1]
local cur = tonumber(redis.call('GET', key) or '0')
if cur <= 0 then return 0 end
redis.call('DECR', key)
return 1
"""


class RedisDailyQuota:
    def __init__(self, client: Redis):
        self._consume = client.register_script(_CONSUME)
        self._release = client.register_script(_RELEASE)

    def try_consume(self, activity_id: int, user_id: str, day: str, limit: int, ttl: int) -> bool:
        ok = self._consume(keys=[keys.daily_quota(activity_id, user_id, day)], args=[limit, ttl])
        return int(ok) == 1

    def release(self, activity_id: int, user_id: str, day: str) -> None:
        self._release(keys=[keys.daily_quota(activity_id, user_id, day)])
