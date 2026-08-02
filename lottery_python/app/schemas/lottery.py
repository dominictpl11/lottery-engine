from pydantic import BaseModel, Field


class DrawRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    activity_id: int


class DrawResponse(BaseModel):
    success: bool
    order_id: str | None = None
    user_id: str
    activity_id: int
    draw_state: str
    grant_state: str
    award_id: int | None = None
    award_name: str | None = None
    message: str
