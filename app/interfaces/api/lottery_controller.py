from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application.lottery_process import LotteryProcess
from app.core.config import settings
from app.core.database import get_db
from app.infrastructure.redis.client import get_redis
from app.infrastructure.redis.daily_quota import RedisDailyQuota
from app.infrastructure.redis.idempotency import RedisIdempotency
from app.infrastructure.redis.inventory import RedisInventory
from app.infrastructure.redis.rate_limiter import RedisRateLimiter
from app.infrastructure.repositories import (
    ActivityRepository,
    AwardRepository,
    DrawOrderRepository,
)
from app.schemas.lottery import DrawRequest, DrawResponse

router = APIRouter(tags=["lottery"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/lottery/draw", response_model=DrawResponse)
def draw(req: DrawRequest, db: Session = Depends(get_db)):
    client = get_redis()
    process = LotteryProcess(
        db,
        ActivityRepository(db),
        AwardRepository(db),
        DrawOrderRepository(db),
        RedisInventory(client),
        RedisRateLimiter(client),
        RedisDailyQuota(client),
        RedisIdempotency(
            client,
            lock_ttl=settings.idempotency_lock_ttl_seconds,
            result_ttl=settings.idempotency_result_ttl_seconds,
        ),
    )
    return process.draw(req)
