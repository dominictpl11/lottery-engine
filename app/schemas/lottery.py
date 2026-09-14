from pydantic import BaseModel, Field

from app.domain.models import RejectReason


class DrawAward(BaseModel):
    award_id: int
    award_name: str


class DrawRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    activity_id: int
    # request_id（客户端提供的幂等键，FR-5）在 Phase 2 随 Redis 幂等一并加入。
    # 当前由服务端生成，先把 draw_order.request_id 的 UNIQUE 约束立起来。


class DrawResponse(BaseModel):
    # success 表示抽奖流程是否正常执行完毕，**不表示是否中奖**（§6.3）：
    #   中奖 -> True/won；未中奖 -> True/missed；业务拒绝 -> False/rejected
    success: bool
    order_id: str | None = None
    user_id: str
    activity_id: int
    draw_state: str
    award_state: str
    award: DrawAward | None = None
    message: str
    # 业务拒绝时给出固定分类，便于测试与压测统计（§6.5）。
    reject_reason: RejectReason | None = None
