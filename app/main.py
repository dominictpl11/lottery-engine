import logging

import redis as redis_lib
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

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


def create_app() -> FastAPI:
    # 建表交给 Alembic（`alembic upgrade head`），不再用 create_all：
    # 否则 schema 会有两个真源，迁移也无法复现结构（§8.2）。

    app = FastAPI(
        title="Lottery Engine",
        description="Concurrency-safe marketing lottery service.",
        version="0.2.0",
    )

    app.include_router(activity_router, prefix="/api")
    app.include_router(lottery_router, prefix="/api")

    @app.on_event("startup")
    def check_dependencies() -> None:
        # Redis 承担原子库存、限流和幂等，起不来就没必要假装能提供服务。
        # 这里只告警不退出，让 /api/health 仍可探活；抽奖接口会以 503 拒绝。
        try:
            redis_ping()
            logger.info("Redis 连接正常")
        except redis_lib.RedisError as exc:
            logger.error("Redis 不可用，抽奖接口将返回 503：%s", exc)

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
