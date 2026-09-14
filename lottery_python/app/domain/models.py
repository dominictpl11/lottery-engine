"""领域模型。

所有 DateTime 列存 **naive UTC**，时区转换在 app/core/timeutil.py 的边界函数
中显式完成（见 REQUIREMENTS.md §4.4）。

字段命名沿用当前实现；按 §4.1，重命名为 status / stock_total / stock_surplus /
award_state 等 v2 口径的工作放在 Phase 1 重建 MySQL schema 时一次性完成。
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.timeutil import utc_now_naive


class ActivityState(str, Enum):
    draft = "draft"
    running = "running"
    closed = "closed"


class AwardType(str, Enum):
    text = "text"
    coupon = "coupon"
    physical = "physical"


class DrawState(str, Enum):
    won = "won"
    missed = "missed"
    rejected = "rejected"


class GrantState(str, Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    none = "none"


class RejectReason(str, Enum):
    """业务拒绝原因，取值固定，见 REQUIREMENTS.md §6.5。

    压测与测试按此分类统计；业务拒绝不计入失败率（§7.2）。
    """

    activity_not_running = "activity_not_running"
    activity_not_in_window = "activity_not_in_window"
    daily_limit_exceeded = "daily_limit_exceeded"
    rate_limited = "rate_limited"
    activity_stock_exhausted = "activity_stock_exhausted"
    award_stock_exhausted = "award_stock_exhausted"


class Activity(Base):
    __tablename__ = "activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    begin_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    stock_count: Mapped[int] = mapped_column(Integer)
    stock_surplus_count: Mapped[int] = mapped_column(Integer)
    daily_limit: Mapped[int] = mapped_column(Integer, default=3)
    state: Mapped[str] = mapped_column(String(20), default=ActivityState.draft.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    awards: Mapped[list["Award"]] = relationship(back_populates="activity")


class Award(Base):
    __tablename__ = "award"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activity.activity_id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    award_type: Mapped[str] = mapped_column(String(20))
    content: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stock_count: Mapped[int] = mapped_column(Integer)
    stock_surplus_count: Mapped[int] = mapped_column(Integer)
    weight: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    activity: Mapped[Activity] = relationship(back_populates="awards")


class DrawOrder(Base):
    __tablename__ = "draw_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    activity_id: Mapped[int] = mapped_column(Integer, index=True)
    award_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    award_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    draw_state: Mapped[str] = mapped_column(String(20))
    grant_state: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
