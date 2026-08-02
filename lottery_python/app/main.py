from fastapi import FastAPI

from app.core.database import Base, engine
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

    return app


app = create_app()
