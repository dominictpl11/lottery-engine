"""Redis Lua 原子库存（FR-7）。

为什么必须用 Lua：

    GET stock          <- 两个请求都读到 1
    if stock > 0:
        DECR stock     <- 两个都扣，库存变成 -1

GET 与 DECR 之间存在窗口。DECR 本身是原子的，但"判断 + 扣减"这个组合不是。
把判断和扣减放进同一个 Lua 脚本，Redis 单线程执行脚本，整体才原子。

Redis 与 MySQL 的分工（见 REQUIREMENTS.md §4.6）：
- Redis 是**闸门**，决定这次抽奖能不能继续，负责在高并发下不放超；
- MySQL 是**账本**，在事务里记录最终结果，UPDATE 带 `stock_surplus > 0` 条件兜底。
两者可能因 Redis 被清空而漂移，靠下面的"按需初始化"从 MySQL 重新对齐。
"""

from redis import Redis

from app.infrastructure.redis import keys

# 返回值：-1 = key 不存在（调用方需先初始化）；0 = 库存不足；1 = 扣减成功
_DECR = """
local v = redis.call('GET', KEYS[1])
if v == false then return -1 end
if tonumber(v) <= 0 then return 0 end
redis.call('DECR', KEYS[1])
return 1
"""

# 归还一个库存，但不超过上限；key 不存在时不做任何事（说明已被清理）。
_RESTORE = """
local v = redis.call('GET', KEYS[1])
if v == false then return 0 end
if tonumber(v) >= tonumber(ARGV[1]) then return 0 end
redis.call('INCR', KEYS[1])
return 1
"""

NEEDS_INIT = -1
NO_STOCK = 0
OK = 1


class RedisInventory:
    def __init__(self, client: Redis):
        self._decr = client.register_script(_DECR)
        self._restore = client.register_script(_RESTORE)
        self._client = client

    def _try_decrement(self, key: str, load_remaining, ceiling: int) -> bool:
        """扣减一个库存。key 不存在时用 load_remaining() 从 MySQL 初始化后重试一次。"""
        result = int(self._decr(keys=[key]))
        if result == NEEDS_INIT:
            # 初始化用 SET NX：并发下只有第一个请求写入，其余不会覆盖别人已扣过的值。
            # 用剩余量而不是总量，这样 Redis 被清空后能从 MySQL 的当前进度续上。
            self._client.set(key, max(load_remaining(), 0), nx=True)
            result = int(self._decr(keys=[key]))
        return result == OK

    def decrement_activity(self, activity_id: int, load_remaining, stock_total: int) -> bool:
        return self._try_decrement(keys.activity_stock(activity_id), load_remaining, stock_total)

    def decrement_award(self, award_id: int, load_remaining, stock_total: int) -> bool:
        return self._try_decrement(keys.award_stock(award_id), load_remaining, stock_total)

    def restore_activity(self, activity_id: int, stock_total: int) -> None:
        self._restore(keys=[keys.activity_stock(activity_id)], args=[stock_total])

    def restore_award(self, award_id: int, stock_total: int) -> None:
        self._restore(keys=[keys.award_stock(award_id)], args=[stock_total])

    def clear_activity(self, activity_id: int) -> None:
        """活动关闭后清理 key，避免 Redis 里堆积已结束活动的计数。"""
        self._client.delete(keys.activity_stock(activity_id))

    def peek(self, key: str) -> int | None:
        v = self._client.get(key)
        return None if v is None else int(v)
