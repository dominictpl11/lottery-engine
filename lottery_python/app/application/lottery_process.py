from datetime import datetime
from uuid import uuid4

from app.domain.models import ActivityState, DrawOrder, DrawState, GrantState
from app.domain.strategy.draw_algorithm import WeightedDrawAlgorithm
from app.infrastructure.limiters import sliding_window_limiter
from app.infrastructure.repositories import ActivityRepository, AwardRepository, DrawOrderRepository
from app.schemas.lottery import DrawRequest, DrawResponse


class LotteryProcess:
    def __init__(
        self,
        activity_repo: ActivityRepository,
        award_repo: AwardRepository,
        order_repo: DrawOrderRepository,
    ):
        self.activity_repo = activity_repo
        self.award_repo = award_repo
        self.order_repo = order_repo
        self.draw_algorithm = WeightedDrawAlgorithm()

    def draw(self, req: DrawRequest) -> DrawResponse:
        activity = self.activity_repo.get_by_activity_id(req.activity_id)
        if activity is None:
            return self._reject(req, "活动不存在")

        now = datetime.utcnow()
        if activity.state != ActivityState.running.value:
            return self._reject(req, "活动未运行")
        if not (activity.begin_time <= now <= activity.end_time):
            return self._reject(req, "活动不在有效期内")

        limit_key = f"draw:{req.activity_id}:{req.user_id}"
        if not sliding_window_limiter.allow(limit_key, window_seconds=60, max_count=activity.daily_limit):
            return self._reject(req, "参与频率过高，请稍后再试")

        if not self.activity_repo.decrement_stock(req.activity_id):
            return self._reject(req, "活动库存不足")

        awards = self.award_repo.list_available_by_activity(req.activity_id)
        award = self.draw_algorithm.draw(awards)
        if award is None:
            order = self._create_order(req, None, DrawState.missed.value, GrantState.none.value, "未中奖")
            return self._response(req, order, True)

        if not self.award_repo.decrement_stock(award.id):
            order = self._create_order(req, None, DrawState.missed.value, GrantState.none.value, "奖品库存不足")
            return self._response(req, order, True)

        order = self._create_order(req, award, DrawState.won.value, GrantState.pending.value, "中奖")
        return self._response(req, order, True)

    def _reject(self, req: DrawRequest, message: str) -> DrawResponse:
        order = self._create_order(req, None, DrawState.rejected.value, GrantState.none.value, message)
        return self._response(req, order, False)

    def _create_order(self, req: DrawRequest, award, draw_state: str, grant_state: str, message: str) -> DrawOrder:
        order = DrawOrder(
            order_id=uuid4().hex,
            user_id=req.user_id,
            activity_id=req.activity_id,
            award_id=award.id if award else None,
            award_name=award.name if award else None,
            draw_state=draw_state,
            grant_state=grant_state,
            message=message,
        )
        return self.order_repo.create(order)

    def _response(self, req: DrawRequest, order: DrawOrder, success: bool) -> DrawResponse:
        return DrawResponse(
            success=success,
            order_id=order.order_id,
            user_id=req.user_id,
            activity_id=req.activity_id,
            draw_state=order.draw_state,
            grant_state=order.grant_state,
            award_id=order.award_id,
            award_name=order.award_name,
            message=order.message,
        )
