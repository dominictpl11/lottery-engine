from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.database import Base, engine
from app.core.exceptions import ActivityNotFoundError
from app.interfaces.api.activity_controller import router as activity_router
from app.interfaces.api.lottery_controller import router as lottery_router


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)

    app = FastAPI(
        title="Lottery Engine Python",
        description="High concurrency marketing lottery engine built with FastAPI.",
        version="0.1.0",
    )

    app.include_router(activity_router, prefix="/api")
    app.include_router(lottery_router, prefix="/api")

    # 领域异常在这里统一映射为 HTTP，应用层与领域层不依赖 FastAPI（§5.2）。
    @app.exception_handler(ActivityNotFoundError)
    async def handle_activity_not_found(_: Request, exc: ActivityNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return app


app = create_app()
