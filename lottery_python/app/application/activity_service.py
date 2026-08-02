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
            begin_time=req.begin_time,
            end_time=req.end_time,
            stock_count=req.stock_count,
            stock_surplus_count=req.stock_count,
            daily_limit=req.daily_limit,
            state=req.state,
        )
        return self.activity_repo.create(activity)

    def create_award(self, activity_id: int, req: AwardCreate) -> Award:
        award = Award(
            activity_id=activity_id,
            name=req.name,
            award_type=req.award_type,
            content=req.content,
            stock_count=req.stock_count,
            stock_surplus_count=req.stock_count,
            weight=req.weight,
        )
        return self.award_repo.create(award)
