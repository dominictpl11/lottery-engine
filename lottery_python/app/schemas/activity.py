from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.domain.models import ActivityState, AwardType


class ActivityCreate(BaseModel):
    activity_id: int
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    # AwareDatetime：必须带时区偏移。naive 值会被拒为 422，而不是被静默当成 UTC
    # 解释（缺陷 D4）。见 REQUIREMENTS.md §4.4。
    begin_time: AwareDatetime
    end_time: AwareDatetime
    stock_count: int = Field(gt=0)
    daily_limit: int = Field(default=3, gt=0)
    # 绑定枚举，非法状态值在入口被拒（缺陷 D6）。
    state: ActivityState = ActivityState.running

    @model_validator(mode="after")
    def check_time_window(self) -> "ActivityCreate":
        if self.end_time <= self.begin_time:
            raise ValueError("end_time 必须晚于 begin_time")
        return self


class ActivityResponse(BaseModel):
    activity_id: int
    name: str
    state: ActivityState
    stock_count: int
    stock_surplus_count: int

    model_config = {"from_attributes": True}


class AwardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # 绑定枚举（缺陷 D6）。取值集合按 §4.1 在 Phase 1 改为
    # coupon/physical/virtual/none。
    award_type: AwardType = AwardType.coupon
    content: str | None = None
    stock_count: int = Field(gt=0)
    weight: float = Field(gt=0)


class AwardResponse(BaseModel):
    id: int
    activity_id: int
    name: str
    award_type: AwardType
    stock_count: int
    stock_surplus_count: int
    weight: float

    model_config = {"from_attributes": True}
