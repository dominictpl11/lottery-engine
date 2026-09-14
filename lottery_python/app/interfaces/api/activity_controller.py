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
    service = get_activity_service(db)
    existing = ActivityRepository(db).get_by_activity_id(req.activity_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="活动ID已存在")
    return service.create_activity(req)


@router.post("/{activity_id}/awards", response_model=AwardResponse, status_code=201)
def create_award(activity_id: int, req: AwardCreate, db: Session = Depends(get_db)):
    activity_repo = ActivityRepository(db)
    if activity_repo.get_by_activity_id(activity_id) is None:
        raise HTTPException(status_code=404, detail="活动不存在")
    service = get_activity_service(db)
    return service.create_award(activity_id, req)
