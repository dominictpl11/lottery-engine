import logging
from contextlib import asynccontextmanager
from pathlib import Path

import redis as redis_lib
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import TimeoutError as SATimeoutError

from app.core.exceptions import (
    ActivityNotFoundError,
    DependencyUnavailableError,
    DrawPersistenceError,
    DuplicateRequestError,
)
from app.infrastructure.redis.client import ping as redis_ping
from app.interfaces.api.activity_controller import router as activity_router
from app.interfaces.api.lottery_controller import router as lottery_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Redis 承担原子库存、限流和幂等，起不来就没必要假装能提供服务。
    # 这里只告警不退出，让 /api/health 仍可探活；抽奖接口会以 503 拒绝。
    try:
        redis_ping()
        logger.info("Redis 连接正常")
    except redis_lib.RedisError as exc:
        logger.error("Redis 不可用，抽奖接口将返回 503：%s", exc)
    yield


def create_app() -> FastAPI:
    # 建表交给 Alembic（`alembic upgrade head`），不再用 create_all：
    # 否则 schema 会有两个真源，迁移也无法复现结构（§8.2）。

    app = FastAPI(
        title="Lottery Engine",
        description="Concurrency-safe marketing lottery service.",
        version="0.3.0",
        lifespan=lifespan,
    )

    app.include_router(activity_router, prefix="/api")
    app.include_router(lottery_router, prefix="/api")

    # 演示页。一个静态 HTML，由 API 自己托管——不引入前端框架和构建工具，
    # 保持单体（PROJECT_PLAN 5.1）。它的作用是让并发特性可以被当场点出来，
    # 而不是给一个好看的转盘。
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/", include_in_schema=False)
        async def demo_page():
            """面向用户的抽奖页。刻意不暴露中奖概率。"""
            return FileResponse(static_dir / "index.html")

        @app.get("/dev", include_in_schema=False)
        async def dev_page():
            """开发者页：真实权重、并发验证、请求响应原文。"""
            return FileResponse(static_dir / "dev.html")

    # 领域异常在这里统一映射为 HTTP，应用层与领域层不依赖 FastAPI（§5.2）。
    @app.exception_handler(ActivityNotFoundError)
    async def handle_activity_not_found(_: Request, exc: ActivityNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(DuplicateRequestError)
    async def handle_duplicate_request(_: Request, exc: DuplicateRequestError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(DrawPersistenceError)
    async def handle_draw_persistence(_: Request, exc: DrawPersistenceError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(DependencyUnavailableError)
    async def handle_dependency_unavailable(_: Request, exc: DependencyUnavailableError):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    # 数据库连接池耗尽是**容量问题**，不是程序错误，语义上属于 503 而非 500：
    # 服务端一切正常，只是当前负载超过了它能同时处理的量。
    # 分开返回有实际意义——压测报告里 503 代表"这台机器到顶了"，
    # 500 才代表"有 bug 要修"。
    @app.exception_handler(SATimeoutError)
    async def handle_pool_timeout(_: Request, exc: SATimeoutError):
        logger.error("数据库连接池耗尽：%s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "服务繁忙，请稍后重试"},
        )

    # Redis 故障统一转成 503：快速失败，绝不降级放行（见 client.py 的说明）。
    @app.exception_handler(redis_lib.RedisError)
    async def handle_redis_error(_: Request, exc: redis_lib.RedisError):
        logger.error("Redis 操作失败：%s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "依赖服务暂不可用，请稍后重试"},
        )

    return app


app = create_app()
