from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application.lottery_process import LotteryProcess
from app.core.database import get_db
from app.infrastructure.repositories import ActivityRepository, AwardRepository, DrawOrderRepository
from app.schemas.lottery import DrawRequest, DrawResponse

router = APIRouter(tags=["lottery"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/lottery/draw", response_model=DrawResponse)
def draw(req: DrawRequest, db: Session = Depends(get_db)):
    process = LotteryProcess(
        ActivityRepository(db),
        AwardRepository(db),
        DrawOrderRepository(db),
    )
    return process.draw(req)
