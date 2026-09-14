from pydantic import BaseModel, Field

from app.domain.models import RejectReason


class DrawRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    activity_id: int
    # request_id（幂等键，FR-5）在 Phase 2 随 Redis 幂等一并加入。


class DrawResponse(BaseModel):
    # success 表示抽奖流程是否正常执行完毕，**不表示是否中奖**（§6.3）：
    #   中奖 -> True/won；未中奖 -> True/missed；业务拒绝 -> False/rejected
    success: bool
    order_id: str | None = None
    user_id: str
    activity_id: int
    draw_state: str
    grant_state: str
    award_id: int | None = None
    award_name: str | None = None
    message: str
    # 业务拒绝时给出固定分类，便于测试与压测统计（§6.5）。
    reject_reason: RejectReason | None = None
