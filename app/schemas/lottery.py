from pydantic import BaseModel, Field

from app.domain.models import RejectReason


class DrawAward(BaseModel):
    award_id: int
    award_name: str


class DrawRequest(BaseModel):
    # 幂等键，由客户端（或压测脚本）为每次逻辑请求生成，通常是 UUID。
    # 重发同一个 request_id 只会产生一次副作用（FR-5）。
    request_id: str = Field(min_length=8, max_length=64)
    user_id: str = Field(min_length=1, max_length=64)
    activity_id: int


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
