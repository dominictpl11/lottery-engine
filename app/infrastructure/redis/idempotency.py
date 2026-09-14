"""请求幂等（FR-5）。

同一个 request_id 重复到达（双击、网络重试、上游重发），只能产生一次副作用：
一次扣库存、一条订单、一次发奖。

两层防线：
1. Redis（本模块）—— 快路径。`SET NX` 抢占，抢到的才执行，没抢到的直接返回
   首次结果或"处理中"。
2. MySQL `uk_request_id` —— 最后一道。即使 Redis 挂了、被清空、或 TTL 已过，
   数据库仍然拒绝第二条同 request_id 的订单。

状态机：
    不存在        -> SET NX 成功 -> NEW，调用方继续执行
    "processing"  -> IN_FLIGHT，说明有另一个请求正在处理，返回 409
    其他（JSON）  -> DONE，直接回放首次结果
"""

import json
from enum import Enum

from redis import Redis

from app.infrastructure.redis import keys

_PROCESSING = "processing"


class IdempotencyState(str, Enum):
    new = "new"
    in_flight = "in_flight"
    done = "done"


class RedisIdempotency:
    def __init__(self, client: Redis, lock_ttl: int, result_ttl: int):
        self._client = client
        self._lock_ttl = lock_ttl
        self._result_ttl = result_ttl

    def begin(self, request_id: str) -> tuple[IdempotencyState, dict | None]:
        key = keys.idempotency(request_id)
        # SET NX 的 TTL 是"处理中"的最长容忍时间：进程在执行到一半时崩溃，
        # key 到期后这个 request_id 才能被重试，不会永久卡死。
        if self._client.set(key, _PROCESSING, nx=True, ex=self._lock_ttl):
            return IdempotencyState.new, None

        value = self._client.get(key)
        if value is None or value == _PROCESSING:
            # value 为 None：刚好在 SET NX 失败与 GET 之间过期，按处理中对待，
            # 让调用方重试，比贸然放行安全。
            return IdempotencyState.in_flight, None
        try:
            return IdempotencyState.done, json.loads(value)
        except json.JSONDecodeError:
            return IdempotencyState.in_flight, None

    def complete(self, request_id: str, result: dict) -> None:
        """把首次结果写回，供后续重放。"""
        self._client.set(keys.idempotency(request_id), json.dumps(result), ex=self._result_ttl)

    def abort(self, request_id: str) -> None:
        """执行失败时释放占位，让这个 request_id 可以被重试。"""
        self._client.delete(keys.idempotency(request_id))
