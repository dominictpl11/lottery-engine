"""幂等在并发下的行为（FR-5）。

串行重发很容易通过（第二次直接命中缓存），真正的考验是**同时**到达：
多个线程同时发现 key 不存在，如果没有 SET NX，就会都去执行一遍。
"""

import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.domain.models import Activity, DrawOrder

pytestmark = pytest.mark.concurrency


def _same_request(client, activity_id, request_id, n, workers=32):
    def one(_):
        r = client.post("/api/lottery/draw", json={
            "request_id": request_id, "user_id": "dup-user", "activity_id": activity_id,
        })
        return r.status_code, r.json()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(one, range(n)))


def test_concurrent_same_request_id_creates_one_order(client, make_activity,
                                                      make_award, db):
    aid = make_activity(stock_total=100, daily_limit=9999)
    make_award(aid, stock_total=100)
    rid = uuid.uuid4().hex

    results = _same_request(client, aid, rid, 40)
    codes = Counter(c for c, _ in results)

    assert codes.get(500, 0) == 0, f"出现了 5xx：{dict(codes)}"
    assert set(codes) <= {200, 409}, f"只应有 200(回放) 或 409(处理中)：{dict(codes)}"

    n_orders = db.query(DrawOrder).filter(DrawOrder.request_id == rid).count()
    assert n_orders == 1, f"同一 request_id 产生了 {n_orders} 条订单"

    order_ids = {b.get("order_id") for c, b in results if c == 200 and b.get("order_id")}
    assert len(order_ids) == 1, f"成功响应指向了 {len(order_ids)} 个不同订单"


def test_concurrent_duplicate_consumes_stock_once(client, make_activity,
                                                  make_award, db, redis_client):
    """重复请求只能扣一次库存——这是幂等真正要防的副作用。"""
    aid = make_activity(stock_total=100, daily_limit=9999)
    make_award(aid, stock_total=100)
    rid = uuid.uuid4().hex

    _same_request(client, aid, rid, 40)

    db.expire_all()
    act = db.query(Activity).filter(Activity.activity_id == aid).one()
    assert act.stock_surplus == 99, f"库存被扣了 {100 - act.stock_surplus} 次"
    assert int(redis_client.get(f"lottery:stock:activity:{aid}")) == 99


def test_distinct_request_ids_are_independent(client, make_activity, make_award, db):
    """幂等不能误伤：不同 request_id 必须各自独立生效。"""
    aid = make_activity(stock_total=100, daily_limit=9999)
    make_award(aid, stock_total=100)

    def one(i):
        return client.post("/api/lottery/draw", json={
            "request_id": uuid.uuid4().hex, "user_id": f"indep{i}", "activity_id": aid,
        }).json()

    with ThreadPoolExecutor(max_workers=16) as ex:
        bodies = list(ex.map(one, range(20)))

    drawn = [b for b in bodies if b.get("draw_state") in ("won", "missed")]
    assert len(drawn) == 20, "不同 request_id 的请求被错误地合并了"
    assert len({b["order_id"] for b in drawn}) == 20, "订单号重复"


def test_db_unique_constraint_is_the_last_line(db, make_activity):
    """即使 Redis 幂等失效，MySQL 的 uk_request_id 仍然拦得住重复订单。

    这条不走 API，直接往库里插第二条同 request_id 的记录，验证约束真的在。
    """
    from sqlalchemy.exc import IntegrityError

    aid = make_activity()
    rid = uuid.uuid4().hex
    for order_id in ("order-a", "order-b"):
        db.add(DrawOrder(
            order_id=order_id, request_id=rid, user_id="u", activity_id=aid,
            award_id=None, draw_state="rejected", award_state="none", message="x",
        ))
        if order_id == "order-a":
            db.commit()
        else:
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
