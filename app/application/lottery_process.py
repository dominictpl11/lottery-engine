"""抽奖主链路编排（FR-3）。

链路顺序见 REQUIREMENTS.md FR-3：
    幂等检查 -> 查活动 -> 状态/时间校验 -> 频率限流(FR-6a) -> 每日次数(FR-6b)
    -> Redis 原子扣活动库存 -> 取候选奖品 -> 加权抽奖 -> Redis 原子扣奖品库存
    -> MySQL 事务(扣两处库存 + 写订单) -> 保存幂等结果 -> 返回

Redis 与 MySQL 的分工：Redis 是**闸门**，在高并发下决定放不放行；MySQL 是**账本**，
在事务里记录最终结果，UPDATE 带 `stock_surplus > 0` 作为第二道防线。

三条纪律：
1. 任何已占用的资源（活动库存、奖品库存、当日配额），后续步骤失败时必须按占用的
   逆序归还。
2. 活动不存在返回 404 且不落订单；其余业务拒绝才落 rejected 订单。
3. 两处库存扣减与订单写入必须在同一个数据库事务内（§4.6）。
"""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    ActivityNotFoundError,
    DrawPersistenceError,
    DuplicateRequestError,
)
from app.core.timeutil import (
    china_day_key,
    from_db,
    seconds_until_china_midnight,
    utc_now,
)
from app.domain.models import (
    ActivityStatus,
    AwardState,
    AwardType,
    DrawOrder,
    DrawState,
    RejectReason,
)
from app.domain.strategy.draw_algorithm import WeightedDrawAlgorithm
from app.infrastructure.redis.daily_quota import RedisDailyQuota
from app.infrastructure.redis.idempotency import IdempotencyState, RedisIdempotency
from app.infrastructure.redis.inventory import RedisInventory
from app.infrastructure.redis.rate_limiter import RedisRateLimiter
from app.infrastructure.repositories import (
    ActivityRepository,
    AwardRepository,
    DrawOrderRepository,
)
from app.schemas.lottery import DrawAward, DrawRequest, DrawResponse

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
        db: Session,
        activity_repo: ActivityRepository,
        award_repo: AwardRepository,
        order_repo: DrawOrderRepository,
        inventory: RedisInventory,
        rate_limiter: RedisRateLimiter,
        daily_quota: RedisDailyQuota,
        idempotency: RedisIdempotency,
    ):
        self.db = db
        self.activity_repo = activity_repo
        self.award_repo = award_repo
        self.order_repo = order_repo
        self.inventory = inventory
        self.rate_limiter = rate_limiter
        self.daily_quota = daily_quota
        self.idempotency = idempotency
        self.draw_algorithm = WeightedDrawAlgorithm()

    def draw(self, req: DrawRequest) -> DrawResponse:
        # FR-5：同一 request_id 只执行一次。抢不到占位的直接回放或拒绝。
        state, cached = self.idempotency.begin(req.request_id)
        if state is IdempotencyState.done:
            return DrawResponse(**cached)
        if state is IdempotencyState.in_flight:
            raise DuplicateRequestError(req.request_id)

        try:
            response = self._draw_once(req)
        except Exception:
            # 执行失败就释放占位，让这个 request_id 可以被重试。
            self.idempotency.abort(req.request_id)
            raise

        self.idempotency.complete(req.request_id, response.model_dump(mode="json"))
        return response

    def _draw_once(self, req: DrawRequest) -> DrawResponse:
        activity = self.activity_repo.get_by_activity_id(req.activity_id)
        if activity is None:
            # 404，不落库。见 §4.5 与缺陷 D7。
            raise ActivityNotFoundError(req.activity_id)

        now = utc_now()
        if activity.status != ActivityStatus.running.value:
            return self._reject(req, RejectReason.activity_not_running)
        # 库中是 naive UTC，补上 tzinfo 后才能与 aware 的 now 比较（缺陷 D4）。
        if not (from_db(activity.start_time) <= now <= from_db(activity.end_time)):
            return self._reject(req, RejectReason.activity_not_in_window)

        # FR-6a 频率限流。排在每日配额之前：否则高频请求在被拒的同时还会烧掉当日配额。
        if not self.rate_limiter.allow(
            req.activity_id,
            req.user_id,
            settings.rate_limit_window_seconds,
            settings.rate_limit_max_count,
        ):
            return self._reject(req, RejectReason.rate_limited)

        # FR-6b 每日参与次数。上限取 activity.daily_limit，按 Asia/Shanghai 自然日重置。
        day = china_day_key(now)
        if not self.daily_quota.try_consume(
            req.activity_id,
            req.user_id,
            day,
            activity.daily_limit,
            seconds_until_china_midnight(now),
        ):
            return self._reject(req, RejectReason.daily_limit_exceeded)

        # FR-7 Redis 闸门：活动库存。key 不存在时从 MySQL 的剩余量初始化。
        if not self.inventory.decrement_activity(
            req.activity_id,
            lambda: self.activity_repo.get_surplus(req.activity_id),
            activity.stock_total,
        ):
            self.daily_quota.release(req.activity_id, req.user_id, day)
            return self._reject(req, RejectReason.activity_stock_exhausted)

        awards = self.award_repo.list_available_by_activity(req.activity_id)
        award = self.draw_algorithm.draw(awards)
        if award is None:
            self._release_activity(req, activity, day)
            return self._reject(req, RejectReason.award_stock_exhausted)

        # FR-7 Redis 闸门：奖品库存。
        if not self.inventory.decrement_award(
            award.award_id,
            lambda: self.award_repo.get_surplus(award.award_id),
            award.stock_total,
        ):
            self._release_activity(req, activity, day)
            return self._reject(req, RejectReason.award_stock_exhausted)

        return self._persist(req, activity, award, day)

    def _persist(self, req: DrawRequest, activity, award, day: str) -> DrawResponse:
        # 「谢谢参与」是一个真实奖品（有库存、有权重），但不算中奖（FR-3）。
        won = award.award_type != AwardType.none.value
        order = DrawOrder(
            order_id=uuid4().hex,
            request_id=req.request_id,
            user_id=req.user_id,
            activity_id=req.activity_id,
            award_id=award.award_id,
            draw_state=DrawState.won.value if won else DrawState.missed.value,
            award_state=AwardState.pending.value if won else AwardState.none.value,
            message="中奖" if won else "未中奖",
        )

        # §4.6 的单事务范围：两处库存扣减 + 订单写入一起提交。
        try:
            if not self.activity_repo.decrement_stock_nocommit(req.activity_id):
                raise DrawPersistenceError("活动库存在数据库层扣减失败")
            if not self.award_repo.decrement_stock_nocommit(award.award_id):
                raise DrawPersistenceError("奖品库存在数据库层扣减失败")
            self.order_repo.add_nocommit(order)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            self.inventory.restore_award(award.award_id, award.stock_total)
            self._release_activity(req, activity, day)
            if isinstance(exc, DrawPersistenceError):
                raise
            raise DrawPersistenceError("抽奖结果写入失败，已回滚并归还库存") from exc

        self.db.refresh(order)
        return DrawResponse(
            success=True,
            order_id=order.order_id,
            user_id=req.user_id,
            activity_id=req.activity_id,
            draw_state=order.draw_state,
            award_state=order.award_state,
            award=DrawAward(award_id=award.award_id, award_name=award.name) if won else None,
            message=order.message,
        )

    def _release_activity(self, req: DrawRequest, activity, day: str) -> None:
        """归还活动库存与当日配额（按占用的逆序）。"""
        self.inventory.restore_activity(req.activity_id, activity.stock_total)
        self.daily_quota.release(req.activity_id, req.user_id, day)

    def _reject(self, req: DrawRequest, reason: RejectReason) -> DrawResponse:
        message = _REJECT_MESSAGES[reason]
        order = DrawOrder(
            order_id=uuid4().hex,
            request_id=req.request_id,
            user_id=req.user_id,
            activity_id=req.activity_id,
            award_id=None,
            draw_state=DrawState.rejected.value,
            award_state=AwardState.none.value,
            message=message,
        )
        self.order_repo.create(order)
        return DrawResponse(
            success=False,
            order_id=order.order_id,
            user_id=req.user_id,
            activity_id=req.activity_id,
            draw_state=order.draw_state,
            award_state=order.award_state,
            award=None,
            message=message,
            reject_reason=reason,
        )
