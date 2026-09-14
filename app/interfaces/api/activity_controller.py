from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.activity_service import ActivityService
from app.core.database import get_db
from app.infrastructure.repositories import ActivityRepository, AwardRepository
from app.schemas.activity import ActivityCreate, ActivityResponse, AwardCreate, AwardResponse

router = APIRouter(prefix="/activities", tags=["activities"])


def get_activity_service(db: Session) -> ActivityService:
    return ActivityService(ActivityRepository(db), AwardRepository(db))


@router.post("", response_model=ActivityResponse, status_code=201)
def create_activity(req: ActivityCreate, db: Session = Depends(get_db)):
    if ActivityRepository(db).get_by_activity_id(req.activity_id) is not None:
        raise HTTPException(status_code=409, detail="活动ID已存在")
    return get_activity_service(db).create_activity(req)


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = ActivityRepository(db).get_by_activity_id(activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="活动不存在")
    return activity


@router.get("/{activity_id}/awards", response_model=list[AwardResponse])
def list_awards(activity_id: int, db: Session = Depends(get_db)):
    """列出活动下的全部奖品（含已抽空的），按权重从大到小。"""
    if ActivityRepository(db).get_by_activity_id(activity_id) is None:
        raise HTTPException(status_code=404, detail="活动不存在")
    return AwardRepository(db).list_by_activity(activity_id)


@router.post("/{activity_id}/awards", response_model=AwardResponse, status_code=201)
def create_award(activity_id: int, req: AwardCreate, db: Session = Depends(get_db)):
    if ActivityRepository(db).get_by_activity_id(activity_id) is None:
        raise HTTPException(status_code=404, detail="活动不存在")
    if AwardRepository(db).get_by_award_id(req.award_id) is not None:
        raise HTTPException(status_code=409, detail="奖品ID已存在")
    return get_activity_service(db).create_award(activity_id, req)
