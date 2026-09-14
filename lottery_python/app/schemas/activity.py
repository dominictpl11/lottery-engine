from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.domain.models import ActivityStatus, AwardType
from app.schemas.types import UtcDatetime


class ActivityCreate(BaseModel):
    activity_id: int
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    # AwareDatetime：必须带时区偏移。naive 值会被拒为 422，而不是被静默当成 UTC
    # 解释（缺陷 D4）。见 §4.4。
    start_time: AwareDatetime
    end_time: AwareDatetime
    stock_total: int = Field(gt=0)
    daily_limit: int = Field(default=3, gt=0)
    status: ActivityStatus = ActivityStatus.running

    @model_validator(mode="after")
    def check_time_window(self) -> "ActivityCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time 必须晚于 start_time")
        return self


class ActivityResponse(BaseModel):
    activity_id: int
    name: str
    description: str | None = None
    start_time: UtcDatetime
    end_time: UtcDatetime
    status: ActivityStatus
    stock_total: int
    stock_surplus: int
    daily_limit: int

    model_config = {"from_attributes": True}


class AwardCreate(BaseModel):
    award_id: int
    name: str = Field(min_length=1, max_length=100)
    award_type: AwardType = AwardType.coupon
    content: str | None = None
    stock_total: int = Field(gt=0)
    # 整数权重，见 models.Award.weight 的说明。
    weight: int = Field(gt=0)


class AwardResponse(BaseModel):
    award_id: int
    activity_id: int
    name: str
    award_type: AwardType
    content: str | None = None
    weight: int
    stock_total: int
    stock_surplus: int

    model_config = {"from_attributes": True}
