"""领域模型。见 REQUIREMENTS.md §4。

两条贯穿全文件的约定：

1. 所有 DateTime 列存 **naive UTC**，时区转换在 app/core/timeutil.py 的边界函数中
   显式完成（§4.4）。时间由应用生成而非 DB 的 CURRENT_TIMESTAMP —— 后者取服务器
   时区，会让"库里都是 UTC"这条约定依赖部署环境。compose 里另外把 MySQL 时区钉成
   UTC，是为了手工 SQL 也落在同一口径上。
2. 字段命名对齐 docs/PROJECT_PLAN.md §7（§4.1 的对照表）。
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.timeutil import utc_now_naive


class ActivityStatus(str, Enum):
    draft = "draft"
    running = "running"
    closed = "closed"


class AwardType(str, Enum):
    coupon = "coupon"
    physical = "physical"
    virtual = "virtual"
    # 「谢谢参与」。抽中它记为 missed，不算中奖（FR-3）。
    none = "none"


class DrawState(str, Enum):
    won = "won"
    missed = "missed"
    rejected = "rejected"


class AwardState(str, Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    none = "none"


class RejectReason(str, Enum):
    """业务拒绝原因，取值固定，见 §6.5。

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
    __table_args__ = (
        # 抽奖主链路第一步 WHERE activity_id = ?；同时防止重复创建活动（§4.3）
        UniqueConstraint("activity_id", name="uk_activity_id"),
        CheckConstraint(
            "stock_surplus >= 0 AND stock_surplus <= stock_total", name="ck_activity_stock"
        ),
        CheckConstraint("end_time > start_time", name="ck_activity_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default=ActivityStatus.draft.value)
    stock_total: Mapped[int] = mapped_column(Integer)
    stock_surplus: Mapped[int] = mapped_column(Integer)
    daily_limit: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, onupdate=utc_now_naive
    )

    awards: Mapped[list["Award"]] = relationship(back_populates="activity")


class Award(Base):
    __tablename__ = "award"
    __table_args__ = (
        CheckConstraint(
            "stock_surplus >= 0 AND stock_surplus <= stock_total", name="ck_award_stock"
        ),
        CheckConstraint("weight > 0", name="ck_award_weight"),
        UniqueConstraint("award_id", name="uk_award_id"),
        # 服务候选奖品查询：WHERE activity_id = ? AND stock_surplus > 0（§4.3）
        Index("idx_activity_id", "activity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    award_id: Mapped[int] = mapped_column(BigInteger)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activity.activity_id", name="fk_award_activity")
    )
    name: Mapped[str] = mapped_column(String(100))
    award_type: Mapped[str] = mapped_column(String(16))
    content: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # INT 而非 FLOAT：浮点权重会给统计分布测试（NFR-4）引入不必要的精度误差，
    # 且整数在 Phase 2 的 Redis Lua 里更好处理。权重不必是百分比，总和不必为 100。
    weight: Mapped[int] = mapped_column(Integer)
    stock_total: Mapped[int] = mapped_column(Integer)
    stock_surplus: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, onupdate=utc_now_naive
    )

    activity: Mapped[Activity] = relationship(back_populates="awards")


class DrawOrder(Base):
    __tablename__ = "draw_order"
    __table_args__ = (
        UniqueConstraint("order_id", name="uk_order_id"),
        UniqueConstraint("request_id", name="uk_request_id"),
        # 服务每日次数的 DB 兜底统计与「我的参与记录」查询。
        # 列序按 等值 -> 等值 -> 范围 排列（§4.3）。
        Index("idx_user_activity_created", "user_id", "activity_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64))
    # 幂等键。UNIQUE 是幂等的最后一道防线（§4.3）：即使 Redis 幂等检查异常，
    # 数据库仍能阻止重复订单。Phase 2 接入 Redis 后改为客户端提供。
    request_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(String(64))
    activity_id: Mapped[int] = mapped_column(BigInteger)
    award_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    draw_state: Mapped[str] = mapped_column(String(16))
    award_state: Mapped[str] = mapped_column(String(16))
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, onupdate=utc_now_naive
    )
