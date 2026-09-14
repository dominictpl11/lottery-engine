from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

# 连接池大小是压测暴露出来的真实瓶颈（见 docs/benchmark.md）。
#
# SQLAlchemy 默认 pool_size=5 / max_overflow=10，即每个进程最多 15 条连接。
# 4 个 uvicorn worker 下总共 60 条，而 FastAPI 的同步端点跑在线程池里（默认 40 线程/进程），
# 并发一上来就会有大量请求排队等连接，等满 pool_timeout=30s 后抛
# `QueuePool limit of size 5 overflow 10 reached` —— 表现为 HTTP 500 和 ~30s 的尾延迟。
#
# 调大之前要先算 MySQL 端的上限：max_connections 默认 151，
# 必须满足 workers * (pool_size + max_overflow) < max_connections，
# 否则瓶颈只是从应用侧挪到了数据库侧。当前 4 * (20 + 10) = 120 < 151。
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    # 连接可能被 MySQL 的 wait_timeout 单方面关闭，取出前先探活，
    # 避免把一条死连接交给请求。
    pool_pre_ping=True,
    # 主动回收长连接，配合上面一条减少 "MySQL server has gone away"。
    pool_recycle=1800,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
