from datetime import datetime

from pydantic import BaseModel, Field


class ActivityCreate(BaseModel):
    activity_id: int
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    begin_time: datetime
    end_time: datetime
    stock_count: int = Field(gt=0)
    daily_limit: int = Field(default=3, gt=0)
    state: str = "running"


class ActivityResponse(BaseModel):
    activity_id: int
    name: str
    state: str
    stock_count: int
    stock_surplus_count: int

    model_config = {"from_attributes": True}


class AwardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    award_type: str = "coupon"
    content: str | None = None
    stock_count: int = Field(gt=0)
    weight: float = Field(gt=0)


class AwardResponse(BaseModel):
    id: int
    activity_id: int
    name: str
    award_type: str
    stock_count: int
    stock_surplus_count: int
    weight: float

    model_config = {"from_attributes": True}
