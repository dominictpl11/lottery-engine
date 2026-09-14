from app.core.timeutil import to_db
from app.domain.models import Activity, Award
from app.infrastructure.repositories import ActivityRepository, AwardRepository
from app.schemas.activity import ActivityCreate, AwardCreate


class ActivityService:
    def __init__(self, activity_repo: ActivityRepository, award_repo: AwardRepository):
        self.activity_repo = activity_repo
        self.award_repo = award_repo

    def create_activity(self, req: ActivityCreate) -> Activity:
        activity = Activity(
            activity_id=req.activity_id,
            name=req.name,
            description=req.description,
            # 入参带时区，落库统一转成 naive UTC（§4.4）。
            start_time=to_db(req.start_time),
            end_time=to_db(req.end_time),
            stock_total=req.stock_total,
            stock_surplus=req.stock_total,
            daily_limit=req.daily_limit,
            status=req.status.value,
        )
        return self.activity_repo.create(activity)

    def create_award(self, activity_id: int, req: AwardCreate) -> Award:
        award = Award(
            award_id=req.award_id,
            activity_id=activity_id,
            name=req.name,
            award_type=req.award_type.value,
            content=req.content,
            stock_total=req.stock_total,
            stock_surplus=req.stock_total,
            weight=req.weight,
        )
        return self.award_repo.create(award)
