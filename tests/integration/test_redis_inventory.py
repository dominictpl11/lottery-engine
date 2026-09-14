"""Redis 基础设施组件的直接测试。

这些组件是并发正确性的地基，值得脱离 HTTP 层单独验证边界行为。
"""

import uuid
from concurrent.futures import ThreadPoolExecutor

from app.infrastructure.redis.daily_quota import RedisDailyQuota
from app.infrastructure.redis.idempotency import IdempotencyState, RedisIdempotency
from app.infrastructure.redis.inventory import RedisInventory
from app.infrastructure.redis.rate_limiter import RedisRateLimiter


class TestInventory:
    def test_decrement_initialises_from_loader(self, redis_client):
        inv = RedisInventory(redis_client)
        assert inv.decrement_activity(1, lambda: 5, 5) is True
        assert int(redis_client.get("lottery:stock:activity:1")) == 4

    def test_decrement_stops_at_zero(self, redis_client):
        inv = RedisInventory(redis_client)
        for _ in range(3):
            assert inv.decrement_activity(2, lambda: 3, 3) is True
        assert inv.decrement_activity(2, lambda: 3, 3) is False
        assert int(redis_client.get("lottery:stock:activity:2")) == 0

    def test_never_goes_negative_under_concurrency(self, redis_client):
        inv = RedisInventory(redis_client)
        with ThreadPoolExecutor(max_workers=32) as ex:
            oks = list(ex.map(lambda _: inv.decrement_activity(3, lambda: 50, 50),
                              range(500)))
        assert sum(oks) == 50
        assert int(redis_client.get("lottery:stock:activity:3")) == 0

    def test_restore_is_capped_at_total(self, redis_client):
        inv = RedisInventory(redis_client)
        inv.decrement_activity(4, lambda: 2, 2)
        inv.restore_activity(4, 2)
        inv.restore_activity(4, 2)  # 多余的一次不应把库存顶超
        assert int(redis_client.get("lottery:stock:activity:4")) == 2

    def test_restore_on_missing_key_is_noop(self, redis_client):
        """key 已被清理（活动结束）时归还不应凭空造出库存。"""
        RedisInventory(redis_client).restore_activity(999, 10)
        assert redis_client.get("lottery:stock:activity:999") is None

    def test_loader_zero_means_sold_out(self, redis_client):
        inv = RedisInventory(redis_client)
        assert inv.decrement_activity(5, lambda: 0, 10) is False


class TestRateLimiter:
    def test_allows_up_to_max_then_blocks(self, redis_client):
        rl = RedisRateLimiter(redis_client)
        assert [rl.allow(1, "u", 10, 3) for _ in range(5)] == [True, True, True,
                                                               False, False]

    def test_users_are_independent(self, redis_client):
        rl = RedisRateLimiter(redis_client)
        for _ in range(3):
            rl.allow(1, "a", 10, 3)
        assert rl.allow(1, "a", 10, 3) is False
        assert rl.allow(1, "b", 10, 3) is True

    def test_activities_are_independent(self, redis_client):
        rl = RedisRateLimiter(redis_client)
        for _ in range(3):
            rl.allow(1, "u", 10, 3)
        assert rl.allow(1, "u", 10, 3) is False
        assert rl.allow(2, "u", 10, 3) is True

    def test_uses_zset_with_unique_members(self, redis_client):
        """每次放行都要留下独立成员。

        旧 Java 版拿时间戳同时作 score 和 member，同一刻的多次请求会被 ZADD
        去重成一个，限流因此偏松。这条就是防这个回归。
        """
        rl = RedisRateLimiter(redis_client)
        for _ in range(3):
            rl.allow(7, "u", 10, 3)
        key = "lottery:rate:7:u"
        assert redis_client.type(key) == "zset"
        assert redis_client.zcard(key) == 3

    def test_window_expiry_is_set(self, redis_client):
        rl = RedisRateLimiter(redis_client)
        rl.allow(8, "u", 10, 3)
        assert 0 < redis_client.pttl("lottery:rate:8:u") <= 10_000


class TestDailyQuota:
    def test_consume_up_to_limit(self, redis_client):
        q = RedisDailyQuota(redis_client)
        assert [q.try_consume(1, "u", "20260914", 2, 3600) for _ in range(3)] == \
               [True, True, False]

    def test_different_day_resets(self, redis_client):
        q = RedisDailyQuota(redis_client)
        for _ in range(2):
            q.try_consume(1, "u", "20260914", 2, 3600)
        assert q.try_consume(1, "u", "20260914", 2, 3600) is False
        assert q.try_consume(1, "u", "20260915", 2, 3600) is True

    def test_release_gives_quota_back(self, redis_client):
        q = RedisDailyQuota(redis_client)
        q.try_consume(1, "u", "20260914", 1, 3600)
        assert q.try_consume(1, "u", "20260914", 1, 3600) is False
        q.release(1, "u", "20260914")
        assert q.try_consume(1, "u", "20260914", 1, 3600) is True

    def test_release_never_goes_negative(self, redis_client):
        q = RedisDailyQuota(redis_client)
        for _ in range(3):
            q.release(1, "u", "20260914")
        assert (redis_client.get("lottery:daily:1:u:20260914") or "0") in ("0", None)

    def test_ttl_is_applied(self, redis_client):
        q = RedisDailyQuota(redis_client)
        q.try_consume(1, "u", "20260914", 5, 3600)
        assert 0 < redis_client.ttl("lottery:daily:1:u:20260914") <= 3600


class TestIdempotency:
    def test_first_call_is_new(self, redis_client):
        idem = RedisIdempotency(redis_client, 60, 3600)
        state, cached = idem.begin(uuid.uuid4().hex)
        assert state is IdempotencyState.new and cached is None

    def test_second_call_while_processing_is_in_flight(self, redis_client):
        idem = RedisIdempotency(redis_client, 60, 3600)
        rid = uuid.uuid4().hex
        idem.begin(rid)
        state, _ = idem.begin(rid)
        assert state is IdempotencyState.in_flight

    def test_completed_result_is_replayed(self, redis_client):
        idem = RedisIdempotency(redis_client, 60, 3600)
        rid = uuid.uuid4().hex
        idem.begin(rid)
        idem.complete(rid, {"order_id": "abc", "draw_state": "won"})
        state, cached = idem.begin(rid)
        assert state is IdempotencyState.done
        assert cached == {"order_id": "abc", "draw_state": "won"}

    def test_abort_allows_retry(self, redis_client):
        idem = RedisIdempotency(redis_client, 60, 3600)
        rid = uuid.uuid4().hex
        idem.begin(rid)
        idem.abort(rid)
        state, _ = idem.begin(rid)
        assert state is IdempotencyState.new

    def test_only_one_winner_under_concurrency(self, redis_client):
        """并发抢占时只能有一个拿到 new —— 这是 SET NX 的意义。"""
        idem = RedisIdempotency(redis_client, 60, 3600)
        rid = uuid.uuid4().hex
        with ThreadPoolExecutor(max_workers=32) as ex:
            states = list(ex.map(lambda _: idem.begin(rid)[0], range(50)))
        assert sum(1 for s in states if s is IdempotencyState.new) == 1
