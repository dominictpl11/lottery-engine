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
        # Phase 2 用 Redis Lua 原子扣减替换，见 REQUIREMENTS.md FR-7。
        activity = self.get_by_activity_id(activity_id)
        if activity is None or activity.stock_surplus_count <= 0:
            return False
        activity.stock_surplus_count -= 1
        self.db.commit()
        return True

    def restore_stock(self, activity_id: int) -> None:
        """归还一个活动库存。

        用于「活动库存已扣，但后续步骤失败」的补偿路径（缺陷 D3）。缺了这一步，
        无奖可发或奖品扣减失败时，已扣的活动库存会凭空蒸发。
        """
        activity = self.get_by_activity_id(activity_id)
        if activity is None or activity.stock_surplus_count >= activity.stock_count:
            return
        activity.stock_surplus_count += 1
        self.db.commit()


class AwardRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_available_by_activity(self, activity_id: int) -> list[Award]:
        stmt = (
            select(Award)
            .where(Award.activity_id == activity_id)
            .where(Award.stock_surplus_count > 0)
        )
        return list(self.db.scalars(stmt).all())

    def create(self, award: Award) -> Award:
        self.db.add(award)
        self.db.commit()
        self.db.refresh(award)
        return award

    def decrement_stock(self, award_id: int) -> bool:
        # 同样是 read-then-write（缺陷 D1），Phase 2 替换。
        award = self.db.get(Award, award_id)
        if award is None or award.stock_surplus_count <= 0:
            return False
        award.stock_surplus_count -= 1
        self.db.commit()
        return True


class DrawOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, order: DrawOrder) -> DrawOrder:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
