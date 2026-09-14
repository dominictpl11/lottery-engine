from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Activity, Award, DrawOrder


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_activity_id(self, activity_id: int) -> Activity | None:
        return self.db.scalar(select(Activity).where(Activity.activity_id == activity_id))

    def create(self, activity: Activity) -> Activity:
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def decrement_stock(self, activity_id: int) -> bool:
        # 注意：这是 read-then-write，并发下会超卖（缺陷 D1）。
        # Phase 2 用 Redis Lua 原子扣减替换，见 FR-7。
        activity = self.get_by_activity_id(activity_id)
        if activity is None or activity.stock_surplus <= 0:
            return False
        activity.stock_surplus -= 1
        self.db.commit()
        return True

    def restore_stock(self, activity_id: int) -> None:
        """归还一个活动库存。

        用于「活动库存已扣，但后续步骤失败」的补偿路径（缺陷 D3）。缺了这一步，
        无奖可发或奖品扣减失败时，已扣的活动库存会凭空蒸发。
        """
        activity = self.get_by_activity_id(activity_id)
        if activity is None or activity.stock_surplus >= activity.stock_total:
            return
        activity.stock_surplus += 1
        self.db.commit()


class AwardRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_award_id(self, award_id: int) -> Award | None:
        return self.db.scalar(select(Award).where(Award.award_id == award_id))

    def list_available_by_activity(self, activity_id: int) -> list[Award]:
        stmt = (
            select(Award)
            .where(Award.activity_id == activity_id)
            .where(Award.stock_surplus > 0)
        )
        return list(self.db.scalars(stmt).all())

    def create(self, award: Award) -> Award:
        self.db.add(award)
        self.db.commit()
        self.db.refresh(award)
        return award

    def decrement_stock_nocommit(self, award: Award) -> bool:
        """扣减奖品库存，但**不提交**。

        提交由调用方与订单写入放在同一个事务里完成（§4.6），避免出现
        「订单说中奖、但奖品库存没扣」的不一致。
        并发正确性仍依赖 Phase 2 的 Redis Lua（缺陷 D1）。
        """
        if award.stock_surplus <= 0:
            return False
        award.stock_surplus -= 1
        return True


class DrawOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_nocommit(self, order: DrawOrder) -> DrawOrder:
        """把订单加入当前事务，**不提交**。提交由调用方统一完成（§4.6）。"""
        self.db.add(order)
        return order

    def create(self, order: DrawOrder) -> DrawOrder:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
