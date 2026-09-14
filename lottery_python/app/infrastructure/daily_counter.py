"""每日参与次数计数器（FR-6b）。

这是与频率限流（FR-6a）不同的需求：限流是秒级防刷，本计数器是日级业务配额，
上限取 activity.daily_limit，按 Asia/Shanghai 自然日重置。

Phase 2 会整体替换为 Redis 实现（key 含日期、TTL 设到次日零点），届时本模块
只需保留同样的接口。
"""

import threading


class InMemoryDailyCounter:
    def __init__(self):
        self._counts: dict[tuple[str, str], int] = {}
        self._lock = threading.Lock()

    def try_consume(self, key: str, day: str, limit: int) -> bool:
        """占用一次当日配额。超出上限返回 False。"""
        with self._lock:
            self._purge_other_days(day)
            used = self._counts.get((key, day), 0)
            if used >= limit:
                return False
            self._counts[(key, day)] = used + 1
            return True

    def release(self, key: str, day: str) -> None:
        """归还一次配额。

        用于「配额已占用，但后续步骤失败」的补偿路径（例如活动库存不足）。
        没有这一步，被拒绝的请求也会白白吃掉用户当日的参与次数。
        """
        with self._lock:
            used = self._counts.get((key, day), 0)
            if used > 0:
                self._counts[(key, day)] = used - 1

    def _purge_other_days(self, day: str) -> None:
        """丢弃非当日的键，避免长期运行时内存无界增长。"""
        stale = [k for k in self._counts if k[1] != day]
        for k in stale:
            del self._counts[k]


daily_counter = InMemoryDailyCounter()
