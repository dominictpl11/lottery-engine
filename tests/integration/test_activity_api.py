"""活动与奖品配置接口（FR-1 / FR-2）。

边界用例里有多条是 Phase 0 缺陷 D6 的回归保护：枚举未绑定时这些非法值都能写进库。
"""


def test_create_activity_returns_201(client, new_id):
    aid = new_id()
    r = client.post("/api/activities", json={
        "activity_id": aid, "name": "春节抽奖", "stock_total": 100, "daily_limit": 3,
        "status": "running",
        "start_time": "2026-09-14T00:00:00+08:00",
        "end_time": "2026-12-31T23:59:59+08:00",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["stock_surplus"] == 100, "创建时剩余库存应初始化为总量"
    assert body["status"] == "running"


def test_duplicate_activity_id_returns_409(client, make_activity):
    aid = make_activity()
    r = client.post("/api/activities", json={
        "activity_id": aid, "name": "dup", "stock_total": 10, "status": "running",
        "start_time": "2026-09-14T00:00:00+08:00",
        "end_time": "2026-12-31T23:59:59+08:00",
    })
    assert r.status_code == 409


def test_invalid_status_returns_422(client, new_id):
    """D6 回归：status 绑定了枚举，非法值必须在入口被拒。"""
    r = client.post("/api/activities", json={
        "activity_id": new_id(), "name": "x", "stock_total": 10,
        "status": "totally-bogus",
        "start_time": "2026-09-14T00:00:00+08:00",
        "end_time": "2026-12-31T23:59:59+08:00",
    })
    assert r.status_code == 422


def test_end_time_before_start_time_returns_422(client, new_id):
    r = client.post("/api/activities", json={
        "activity_id": new_id(), "name": "x", "stock_total": 10, "status": "running",
        "start_time": "2026-12-31T00:00:00+08:00",
        "end_time": "2026-09-14T00:00:00+08:00",
    })
    assert r.status_code == 422


def test_naive_datetime_returns_422(client, new_id):
    """D4 回归：不带时区偏移的时间必须被拒，不能被猜成 UTC。"""
    r = client.post("/api/activities", json={
        "activity_id": new_id(), "name": "x", "stock_total": 10, "status": "running",
        "start_time": "2026-09-14T00:00:00",
        "end_time": "2026-12-31T23:59:59",
    })
    assert r.status_code == 422


def test_non_positive_stock_returns_422(client, new_id):
    r = client.post("/api/activities", json={
        "activity_id": new_id(), "name": "x", "stock_total": 0, "status": "running",
        "start_time": "2026-09-14T00:00:00+08:00",
        "end_time": "2026-12-31T23:59:59+08:00",
    })
    assert r.status_code == 422


def test_get_activity(client, make_activity):
    aid = make_activity(stock_total=42)
    r = client.get(f"/api/activities/{aid}")
    assert r.status_code == 200
    assert r.json()["stock_total"] == 42


def test_get_missing_activity_returns_404(client):
    assert client.get("/api/activities/99999999").status_code == 404


def test_create_award_returns_201(client, make_activity, new_id):
    aid = make_activity()
    r = client.post(f"/api/activities/{aid}/awards", json={
        "award_id": new_id(), "name": "100元券", "award_type": "coupon",
        "stock_total": 50, "weight": 10,
    })
    assert r.status_code == 201
    assert r.json()["stock_surplus"] == 50


def test_award_on_missing_activity_returns_404(client, new_id):
    r = client.post("/api/activities/99999999/awards", json={
        "award_id": new_id(), "name": "x", "award_type": "coupon",
        "stock_total": 1, "weight": 1,
    })
    assert r.status_code == 404


def test_duplicate_award_id_returns_409(client, make_activity, make_award):
    aid = make_activity()
    wid = make_award(aid)
    r = client.post(f"/api/activities/{aid}/awards", json={
        "award_id": wid, "name": "dup", "award_type": "coupon",
        "stock_total": 1, "weight": 1,
    })
    assert r.status_code == 409


def test_invalid_award_type_returns_422(client, make_activity, new_id):
    """D6 回归。"""
    aid = make_activity()
    r = client.post(f"/api/activities/{aid}/awards", json={
        "award_id": new_id(), "name": "x", "award_type": "bogus-type",
        "stock_total": 1, "weight": 1,
    })
    assert r.status_code == 422


def test_non_positive_weight_returns_422(client, make_activity, new_id):
    aid = make_activity()
    r = client.post(f"/api/activities/{aid}/awards", json={
        "award_id": new_id(), "name": "x", "award_type": "coupon",
        "stock_total": 1, "weight": 0,
    })
    assert r.status_code == 422


def test_list_awards(client, make_activity, make_award):
    aid = make_activity()
    wids = {make_award(aid, weight=10), make_award(aid, weight=30)}
    r = client.get(f"/api/activities/{aid}/awards")
    assert r.status_code == 200
    body = r.json()
    assert {w["award_id"] for w in body} == wids
    assert [w["weight"] for w in body] == [30, 10], "应按权重从大到小"


def test_list_awards_includes_sold_out(client, make_activity, make_award, draw, db):
    """展示用的列表要含已抽空的奖品，抽奖链路用的那个才只返回有库存的。"""
    aid = make_activity()
    make_award(aid, stock_total=1)
    draw(aid)
    body = client.get(f"/api/activities/{aid}/awards").json()
    assert len(body) == 1 and body[0]["stock_surplus"] == 0


def test_list_awards_missing_activity_returns_404(client):
    assert client.get("/api/activities/99999999/awards").status_code == 404


def test_user_page_is_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "lottery" in r.text.lower()


def test_user_page_does_not_leak_win_rate(client):
    """面向用户的页面不得暴露中奖概率。

    九宫格里每个奖品占的格子数是平均的，奖品卡也不标概率——
    如果哪天有人往用户页加回概率角标，这条会挡住。
    """
    html = client.get("/").text
    js = client.get("/static/app.js").text
    # 去掉注释再看——注释里解释"为什么不展示中奖率"是应该的，
    # 真正会泄露的是渲染出来的内容，以及用于渲染它的代码。
    code = chr(10).join(
        ln for ln in js.split(chr(10)) if not ln.strip().startswith(("//", "*", "/*"))
    )

    assert 'class="rate"' not in html and 'class="rate"' not in code
    assert "weight" not in code, "用户页不应拿 weight 做任何渲染"
    assert "%" not in html


def test_dev_page_is_served(client):
    r = client.get("/dev")
    assert r.status_code == 200
    assert "开发者" in r.text


def test_dev_page_shows_win_rate(client):
    """开发者页反过来必须摊开真实权重。"""
    assert "中奖率" in client.get("/dev").text
