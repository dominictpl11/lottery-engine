"""并发不变量（NFR-1）。

这是整个项目最核心的主张：**任何并发强度下都不超卖**。

这里用线程池打同一个进程内的 ASGI 应用。它验证的是 Redis Lua 与 MySQL 条件
UPDATE 的原子性——这两者是跨进程生效的，所以结论对多 worker 同样成立。
真正的多进程验证由 Phase 4 的 Locust 压测完成（docs/benchmark.md）。
"""

import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.domain.models import Activity, Award, DrawOrder

pytestmark = pytest.mark.concurrency


def _hammer(client, activity_id, n, workers=32, same_user=False):
    def one(i):
        r = client.post("/api/lottery/draw", json={
            "request_id": uuid.uuid4().hex,
            "user_id": "shared" if same_user else f"u{i}",
            "activity_id": activity_id,
        })
        return r.status_code, r.json()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(one, range(n)))


def test_no_oversell_under_concurrency(client, make_activity, make_award, db,
                                       redis_client):
    """初始库存 100，并发 1000 次 —— 成功数必须恰好 100，且库存不为负。"""
    STOCK, N = 100, 1000
    aid = make_activity(stock_total=STOCK, daily_limit=9999)
    wid = make_award(aid, stock_total=STOCK)

    results = _hammer(client, aid, N)
    codes = Counter(c for c, _ in results)
    won = sum(1 for c, b in results if c == 200 and b.get("draw_state") == "won")
    reasons = Counter(b.get("reject_reason") for c, b in results
                      if c == 200 and b.get("success") is False)

    assert codes.get(500, 0) == 0, f"出现了 5xx：{dict(codes)}"
    assert won == STOCK, f"中奖 {won} 次，库存 {STOCK}；拒绝原因={dict(reasons)}"

    db.expire_all()
    act = db.query(Activity).filter(Activity.activity_id == aid).one()
    awd = db.query(Award).filter(Award.award_id == wid).one()
    assert act.stock_surplus == 0 and awd.stock_surplus == 0
    assert act.stock_surplus >= 0 and awd.stock_surplus >= 0

    assert int(redis_client.get(f"lottery:stock:activity:{aid}")) == 0
    assert int(redis_client.get(f"lottery:stock:award:{wid}")) == 0

    n_won_orders = db.query(DrawOrder).filter(
        DrawOrder.activity_id == aid, DrawOrder.draw_state == "won").count()
    assert n_won_orders == STOCK, "won 订单数必须等于中奖次数"


def test_award_stock_respected_across_multiple_awards(client, make_activity,
                                                      make_award, db):
    """活动库存充足但各奖品分别有限，总中奖数不得超过奖品总和。"""
    aid = make_activity(stock_total=1000, daily_limit=9999)
    wids = [make_award(aid, stock_total=20, weight=10) for _ in range(3)]

    results = _hammer(client, aid, 400)
    won = sum(1 for c, b in results if c == 200 and b.get("draw_state") == "won")
    assert won <= 60, f"中奖 {won} 次，但奖品总量只有 60"

    db.expire_all()
    for wid in wids:
        awd = db.query(Award).filter(Award.award_id == wid).one()
        assert awd.stock_surplus >= 0, f"奖品 {wid} 库存为负"


def test_daily_limit_holds_under_concurrency(client, make_activity, make_award, db):
    """同一用户并发请求时，每日配额不能被击穿。"""
    aid = make_activity(stock_total=1000, daily_limit=2)
    make_award(aid, stock_total=1000)

    results = _hammer(client, aid, 40, same_user=True)
    ok = sum(1 for c, b in results if c == 200
             and b.get("draw_state") in ("won", "missed"))
    # 限流(10s/3次)和每日配额(2)同时生效，通过的次数取两者更小值
    assert ok <= 2, f"放行了 {ok} 次，但 daily_limit=2"

    n_orders = db.query(DrawOrder).filter(
        DrawOrder.activity_id == aid,
        DrawOrder.draw_state.in_(("won", "missed"))).count()
    assert n_orders == ok
