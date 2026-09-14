"""失败补偿路径（FR-7 / §4.6）。

这是最容易写错、也最难在生产里发现的一类问题：资源已经占用，但后续步骤失败，
如果不归还，库存就会凭空蒸发（缺陷 D3 就是这个）。

这里用注入失败的方式构造这些路径——它们在正常流量下几乎不会发生。
"""

import uuid

import pytest
from sqlalchemy.exc import OperationalError

from app.application.lottery_process import LotteryProcess
from app.core.config import settings
from app.core.exceptions import DrawPersistenceError
from app.infrastructure.redis.client import get_redis
from app.infrastructure.redis.daily_quota import RedisDailyQuota
from app.infrastructure.redis.idempotency import RedisIdempotency
from app.infrastructure.redis.inventory import RedisInventory
from app.infrastructure.redis.rate_limiter import RedisRateLimiter
from app.infrastructure.repositories import (
    ActivityRepository,
    AwardRepository,
    DrawOrderRepository,
)
from app.schemas.lottery import DrawRequest


def _process(db):
    client = get_redis()
    return LotteryProcess(
        db,
        ActivityRepository(db),
        AwardRepository(db),
        DrawOrderRepository(db),
        RedisInventory(client),
        RedisRateLimiter(client),
        RedisDailyQuota(client),
        RedisIdempotency(
            client,
            lock_ttl=settings.idempotency_lock_ttl_seconds,
            result_ttl=settings.idempotency_result_ttl_seconds,
        ),
    )


def test_mysql_commit_failure_restores_redis_stock(
    make_activity, make_award, db, redis_client, monkeypatch
):
    """Redis 已扣库存但 MySQL 写入失败 —— 必须回滚并把两处 Redis 库存都补回。

    这正是 §4.6 失败点表的第一行，也是本项目双写一致性的核心风险点。
    """
    aid = make_activity(stock_total=10)
    wid = make_award(aid, stock_total=10)
    process = _process(db)

    # 先跑一次正常抽奖，把 Redis 的库存 key 初始化出来
    process.draw(DrawRequest(request_id=uuid.uuid4().hex, user_id="warm", activity_id=aid))
    act_key, awd_key = f"lottery:stock:activity:{aid}", f"lottery:stock:award:{wid}"
    act_before = int(redis_client.get(act_key))
    awd_before = int(redis_client.get(awd_key))

    # 注入提交失败
    def boom():
        raise OperationalError("simulated", None, Exception("connection lost"))
    monkeypatch.setattr(process.db, "commit", boom)

    with pytest.raises(DrawPersistenceError):
        process.draw(DrawRequest(request_id=uuid.uuid4().hex, user_id="victim",
                                 activity_id=aid))

    assert int(redis_client.get(act_key)) == act_before, "活动库存没有被归还"
    assert int(redis_client.get(awd_key)) == awd_before, "奖品库存没有被归还"


def test_failed_draw_releases_idempotency_slot(
    make_activity, make_award, db, redis_client, monkeypatch
):
    """执行失败后，同一个 request_id 必须还能重试。

    否则一次偶发的数据库抖动会把这个 request_id 永久锁死。
    """
    aid = make_activity(stock_total=10)
    make_award(aid, stock_total=10)
    process = _process(db)
    rid = uuid.uuid4().hex

    def boom():
        raise OperationalError("simulated", None, Exception("connection lost"))
    monkeypatch.setattr(process.db, "commit", boom)
    with pytest.raises(DrawPersistenceError):
        process.draw(DrawRequest(request_id=rid, user_id="retry", activity_id=aid))

    assert redis_client.get(f"lottery:idem:{rid}") is None, "幂等占位没有被释放"

    monkeypatch.undo()
    process2 = _process(db)
    result = process2.draw(DrawRequest(request_id=rid, user_id="retry", activity_id=aid))
    assert result.draw_state == "won", "同一 request_id 在失败后应当可以重试"


def test_rejected_draw_returns_activity_stock(make_activity, make_award, draw,
                                              redis_client):
    """D3 回归：无奖可发时，已扣的活动库存必须归还。"""
    aid = make_activity(stock_total=100)
    make_award(aid, stock_total=1)
    draw(aid, user_id="first")
    act_key = f"lottery:stock:activity:{aid}"
    before = int(redis_client.get(act_key))
    b = draw(aid, user_id="second").json()
    assert b["reject_reason"] == "award_stock_exhausted"
    assert int(redis_client.get(act_key)) == before, "活动库存被白白吃掉了"


def test_rejected_draw_returns_daily_quota(make_activity, make_award, draw,
                                           redis_client):
    """被拒绝的请求不应消耗用户当日配额。"""
    from app.core.timeutil import china_day_key, utc_now
    aid = make_activity(stock_total=100, daily_limit=5)
    make_award(aid, stock_total=1)
    draw(aid, user_id="first")
    draw(aid, user_id="second")  # 奖品已空，会被拒
    day = china_day_key(utc_now())
    quota = redis_client.get(f"lottery:daily:{aid}:second:{day}")
    assert (quota or "0") == "0", "被拒绝的请求不该扣掉当日配额"


def test_redis_key_rebuilt_from_mysql_surplus(make_activity, make_award, draw,
                                              redis_client, db):
    """FR-7：Redis key 丢失后按 MySQL 的剩余量续上，而不是重置回总量。

    如果这里按 stock_total 初始化，Redis 被清空就等于凭空发放一批库存。
    """
    from app.domain.models import Activity
    aid = make_activity(stock_total=10)
    make_award(aid, stock_total=10)
    for i in range(3):
        draw(aid, user_id=f"u{i}")
    db.expire_all()
    surplus = db.query(Activity).filter(Activity.activity_id == aid).one().stock_surplus
    assert surplus == 7

    redis_client.delete(f"lottery:stock:activity:{aid}")
    assert draw(aid, user_id="after-flush").json()["draw_state"] == "won"
    assert int(redis_client.get(f"lottery:stock:activity:{aid}")) == 6, (
        "应从 MySQL 剩余量 7 续上并扣 1，而不是从总量 10 重来"
    )
