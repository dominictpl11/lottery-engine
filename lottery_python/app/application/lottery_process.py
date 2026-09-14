"""抽奖主链路编排（FR-3）。

链路顺序见 REQUIREMENTS.md FR-3：
    查活动 -> 状态/时间校验 -> 频率限流(FR-6a) -> 每日次数(FR-6b)
    -> 扣活动库存 -> 取候选奖品 -> 加权抽奖 -> 扣奖品库存 -> 写订单

两条纪律贯穿本文件：
1. 任何已经占用的资源（活动库存、当日配额），在其后的步骤失败时必须归还。
2. 活动不存在属于"请求无效"，返回 404 且不落订单；其余业务拒绝才落 rejected 订单。
"""

from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import ActivityNotFoundError
from app.core.timeutil import china_day_key, from_db, utc_now
from app.domain.models import ActivityState, DrawOrder, DrawState, GrantState, RejectReason
from app.domain.strategy.draw_algorithm import WeightedDrawAlgorithm
from app.infrastructure.daily_counter import daily_counter
from app.infrastructure.limiters import sliding_window_limiter
from app.infrastructure.repositories import ActivityRepository, AwardRepository, DrawOrderRepository
from app.schemas.lottery import DrawRequest, DrawResponse

_REJECT_MESSAGES = {
    RejectReason.activity_not_running: "活动未运行",
    RejectReason.activity_not_in_window: "活动不在有效期内",
    RejectReason.rate_limited: "参与频率过高，请稍后再试",
    RejectReason.daily_limit_exceeded: "今日参与次数已用完",
    RejectReason.activity_stock_exhausted: "活动库存不足",
    RejectReason.award_stock_exhausted: "奖品已被抽完",
}


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
            # 404，不落库。见 §4.5 与缺陷 D7。
            raise ActivityNotFoundError(req.activity_id)

        now = utc_now()
        if activity.state != ActivityState.running.value:
            return self._reject(req, RejectReason.activity_not_running)
        # 库中是 naive UTC，补上 tzinfo 后才能与 aware 的 now 比较（缺陷 D4）。
        if not (from_db(activity.begin_time) <= now <= from_db(activity.end_time)):
            return self._reject(req, RejectReason.activity_not_in_window)

        # FR-6a 频率限流。排在每日配额之前：否则高频请求在被拒的同时还会烧掉当日配额。
        rate_key = f"draw:rate:{req.activity_id}:{req.user_id}"
        if not sliding_window_limiter.allow(
            rate_key,
            window_seconds=settings.rate_limit_window_seconds,
            max_count=settings.rate_limit_max_count,
        ):
            return self._reject(req, RejectReason.rate_limited)

        # FR-6b 每日参与次数。与限流是两回事：上限取 activity.daily_limit，按自然日重置。
        day = china_day_key(now)
        daily_key = f"draw:daily:{req.activity_id}:{req.user_id}"
        if not daily_counter.try_consume(daily_key, day, activity.daily_limit):
            return self._reject(req, RejectReason.daily_limit_exceeded)

        if not self.activity_repo.decrement_stock(req.activity_id):
            daily_counter.release(daily_key, day)
            return self._reject(req, RejectReason.activity_stock_exhausted)

        awards = self.award_repo.list_available_by_activity(req.activity_id)
        award = self.draw_algorithm.draw(awards)
        if award is None:
            # 无奖可发：活动库存与当日配额都要归还（缺陷 D3）。
            self.activity_repo.restore_stock(req.activity_id)
            daily_counter.release(daily_key, day)
            return self._reject(req, RejectReason.award_stock_exhausted)

        if not self.award_repo.decrement_stock(award.id):
            # 奖品在本次抽取与扣减之间被别人抢走，同样要归还（缺陷 D3）。
            self.activity_repo.restore_stock(req.activity_id)
            daily_counter.release(daily_key, day)
            return self._reject(req, RejectReason.award_stock_exhausted)

        order = self._create_order(
            req, award, DrawState.won.value, GrantState.pending.value, "中奖"
        )
        return self._response(req, order, success=True)

    def _reject(self, req: DrawRequest, reason: RejectReason) -> DrawResponse:
        message = _REJECT_MESSAGES[reason]
        order = self._create_order(
            req, None, DrawState.rejected.value, GrantState.none.value, message
        )
        return self._response(req, order, success=False, reject_reason=reason)

    def _create_order(
        self, req: DrawRequest, award, draw_state: str, grant_state: str, message: str
    ) -> DrawOrder:
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

    def _response(
        self,
        req: DrawRequest,
        order: DrawOrder,
        success: bool,
        reject_reason: RejectReason | None = None,
    ) -> DrawResponse:
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
            reject_reason=reject_reason,
        )
