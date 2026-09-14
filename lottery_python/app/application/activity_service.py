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
            begin_time=to_db(req.begin_time),
            end_time=to_db(req.end_time),
            stock_count=req.stock_count,
            stock_surplus_count=req.stock_count,
            daily_limit=req.daily_limit,
            state=req.state.value,
        )
        return self.activity_repo.create(activity)

    def create_award(self, activity_id: int, req: AwardCreate) -> Award:
        award = Award(
            activity_id=activity_id,
            name=req.name,
            award_type=req.award_type.value,
            content=req.content,
            stock_count=req.stock_count,
            stock_surplus_count=req.stock_count,
            weight=req.weight,
        )
        return self.award_repo.create(award)
