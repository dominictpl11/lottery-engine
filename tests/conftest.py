"""测试夹具。

两条隔离原则：
1. 测试用独立的 MySQL 库（lottery_test）和独立的 Redis db（index 1），
   任何时候都不碰开发数据。
2. 每个用例前清空 Redis、每个用例用**唯一的 activity_id**，用例之间不互相干扰。

环境变量必须在导入 app 之前设好——app.core.config.settings 是模块级单例，
一旦导入就固定了。conftest.py 由 pytest 在测试模块之前加载，所以放在这里有效。
"""

import os

os.environ["DATABASE_URL"] = (
    "mysql+pymysql://lottery:change-me-before-use@127.0.0.1:3307/lottery_test?charset=utf8mb4"
)
os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/1"
os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "10"
os.environ["RATE_LIMIT_MAX_COUNT"] = "3"

import itertools  # noqa: E402
from datetime import timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.timeutil import CHINA_TZ, utc_now  # noqa: E402
from app.infrastructure.redis.client import get_redis  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

_ids = itertools.count(700001)


@pytest.fixture(scope="session", autouse=True)
def _schema():
    """建表。

    生产路径是 `alembic upgrade head`，但测试库每次都从零开始，直接用
    metadata 建表更快且等价——两者的真源都是 app/domain/models.py。
    schema 与迁移是否一致由 Phase 1 的验收保证（迁移能从空库复现结构）。
    """
    assert "lottery_test" in settings.database_url, "测试必须跑在 lottery_test 上"
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean():
    """每个用例前清空 Redis 与业务表。"""
    r = get_redis()
    assert r.connection_pool.connection_kwargs.get("db") == 1, "测试必须跑在 Redis db 1 上"
    r.flushdb()
    with SessionLocal() as s:
        s.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for t in ("draw_order", "award", "activity"):
            s.execute(text(f"TRUNCATE TABLE {t}"))
        s.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        s.commit()
    yield


@pytest.fixture
def client():
    with TestClient(fastapi_app) as c:
        yield c


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


@pytest.fixture
def redis_client():
    return get_redis()


@pytest.fixture
def new_id():
    """每次调用返回一个全局唯一的业务 ID，避免用例之间撞号。"""
    return lambda: next(_ids)


@pytest.fixture
def make_activity(client, new_id):
    def _make(stock_total=100, daily_limit=999, status="running",
              starts_in_hours=-1, ends_in_hours=24, activity_id=None):
        aid = activity_id if activity_id is not None else new_id()
        now = utc_now().astimezone(CHINA_TZ)
        resp = client.post("/api/activities", json={
            "activity_id": aid,
            "name": f"test-{aid}",
            "stock_total": stock_total,
            "daily_limit": daily_limit,
            "status": status,
            "start_time": (now + timedelta(hours=starts_in_hours)).isoformat(),
            "end_time": (now + timedelta(hours=ends_in_hours)).isoformat(),
        })
        assert resp.status_code == 201, resp.text
        return aid
    return _make


@pytest.fixture
def make_award(client, new_id):
    def _make(activity_id, stock_total=100, weight=10, award_type="coupon", award_id=None):
        wid = award_id if award_id is not None else new_id()
        resp = client.post(f"/api/activities/{activity_id}/awards", json={
            "award_id": wid,
            "name": f"award-{wid}",
            "award_type": award_type,
            "stock_total": stock_total,
            "weight": weight,
        })
        assert resp.status_code == 201, resp.text
        return wid
    return _make


@pytest.fixture
def draw(client):
    import uuid

    def _draw(activity_id, user_id="tester", request_id=None):
        return client.post("/api/lottery/draw", json={
            "request_id": request_id or uuid.uuid4().hex,
            "user_id": user_id,
            "activity_id": activity_id,
        })
    return _draw
