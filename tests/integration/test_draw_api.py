"""抽奖主链路（FR-3）与各类业务拒绝（§4.5 / §6.3 / §6.5）。"""

import uuid

from app.domain.models import DrawOrder


def _orders(db, activity_id):
    return db.query(DrawOrder).filter(DrawOrder.activity_id == activity_id).all()


def test_winning_draw(client, make_activity, make_award, draw, db):
    aid = make_activity()
    wid = make_award(aid, stock_total=10)
    r = draw(aid)
    assert r.status_code == 200
    b = r.json()
    assert b["success"] is True
    assert b["draw_state"] == "won"
    assert b["award_state"] == "pending"
    assert b["award"] == {"award_id": wid, "award_name": f"award-{wid}"}
    assert b["reject_reason"] is None
    orders = _orders(db, aid)
    assert len(orders) == 1 and orders[0].draw_state == "won"


def test_thank_you_award_is_not_a_win(client, make_activity, make_award, draw, db):
    """FR-3：抽中 award_type=none 记为 missed，success 仍为 true。"""
    aid = make_activity()
    make_award(aid, stock_total=10, award_type="none")
    b = draw(aid).json()
    assert b["success"] is True
    assert b["draw_state"] == "missed"
    assert b["award_state"] == "none"
    assert b["award"] is None
    assert _orders(db, aid)[0].draw_state == "missed"


def test_missing_activity_returns_404_and_writes_nothing(client, db, draw):
    """D7 回归：不存在的活动不得在 draw_order 里留下任何行。"""
    r = draw(99999999)
    assert r.status_code == 404
    assert _orders(db, 99999999) == []


def test_activity_not_running(make_activity, make_award, draw):
    aid = make_activity(status="draft")
    make_award(aid)
    b = draw(aid).json()
    assert b["success"] is False
    assert b["draw_state"] == "rejected"
    assert b["reject_reason"] == "activity_not_running"


def test_activity_not_started_yet(make_activity, make_award, draw):
    aid = make_activity(starts_in_hours=2, ends_in_hours=5)
    make_award(aid)
    assert draw(aid).json()["reject_reason"] == "activity_not_in_window"


def test_activity_already_ended(make_activity, make_award, draw):
    aid = make_activity(starts_in_hours=-48, ends_in_hours=-24)
    make_award(aid)
    assert draw(aid).json()["reject_reason"] == "activity_not_in_window"


def test_activity_stock_exhausted(make_activity, make_award, draw):
    aid = make_activity(stock_total=1)
    make_award(aid, stock_total=100)
    assert draw(aid, user_id="a").json()["draw_state"] == "won"
    b = draw(aid, user_id="b").json()
    assert b["success"] is False
    assert b["reject_reason"] == "activity_stock_exhausted"


def test_award_stock_exhausted(make_activity, make_award, draw):
    """活动还有库存但奖品抽光了：这是业务拒绝，不是中奖也不是未中奖。"""
    aid = make_activity(stock_total=100)
    make_award(aid, stock_total=1)
    assert draw(aid, user_id="a").json()["draw_state"] == "won"
    b = draw(aid, user_id="b").json()
    assert b["success"] is False
    assert b["reject_reason"] == "award_stock_exhausted"


def test_rate_limit(make_activity, make_award, draw):
    """FR-6a：默认 10s / 3 次。"""
    aid = make_activity(stock_total=1000, daily_limit=9999)
    make_award(aid, stock_total=1000)
    states = [draw(aid, user_id="fast").json() for _ in range(5)]
    reasons = [s.get("reject_reason") or s["draw_state"] for s in states]
    assert reasons[:3] == ["won", "won", "won"]
    assert reasons[3:] == ["rate_limited", "rate_limited"]


def test_rate_limit_is_per_user(make_activity, make_award, draw):
    aid = make_activity(stock_total=1000, daily_limit=9999)
    make_award(aid, stock_total=1000)
    for _ in range(3):
        draw(aid, user_id="noisy")
    assert draw(aid, user_id="noisy").json()["reject_reason"] == "rate_limited"
    assert draw(aid, user_id="quiet").json()["draw_state"] == "won"


def test_daily_limit_is_separate_from_rate_limit(make_activity, make_award, draw):
    """D2 回归：每日配额和频率限流是两条不同的规则。

    daily_limit=2 且限流是 10s/3 次，所以第 3 次必须是 daily_limit_exceeded
    而不是 rate_limited —— 如果两者被混成一个，这里会拿到错误的原因。
    """
    aid = make_activity(stock_total=1000, daily_limit=2)
    make_award(aid, stock_total=1000)
    reasons = []
    for _ in range(4):
        b = draw(aid, user_id="quota").json()
        reasons.append(b.get("reject_reason") or b["draw_state"])
    assert reasons == ["won", "won", "daily_limit_exceeded", "rate_limited"]


def test_duplicate_request_id_replays_same_order(make_activity, make_award, draw, db):
    """FR-5：串行重发同一个 request_id，只产生一条订单。"""
    aid = make_activity(stock_total=100)
    make_award(aid, stock_total=100)
    rid = uuid.uuid4().hex
    first = draw(aid, user_id="idem", request_id=rid).json()
    second = draw(aid, user_id="idem", request_id=rid).json()
    assert first["order_id"] == second["order_id"]
    assert len(_orders(db, aid)) == 1


def test_request_id_is_required(client, make_activity):
    aid = make_activity()
    r = client.post("/api/lottery/draw", json={"user_id": "u", "activity_id": aid})
    assert r.status_code == 422


def test_stock_decrements_in_both_stores(make_activity, make_award, draw, db,
                                         redis_client):
    """§4.6：MySQL 与 Redis 两侧都要扣，且保持一致。"""
    from app.domain.models import Activity
    aid = make_activity(stock_total=10)
    wid = make_award(aid, stock_total=10)
    draw(aid)
    db.expire_all()
    act = db.query(Activity).filter(Activity.activity_id == aid).one()
    assert act.stock_surplus == 9
    assert int(redis_client.get(f"lottery:stock:activity:{aid}")) == 9
    assert int(redis_client.get(f"lottery:stock:award:{wid}")) == 9
