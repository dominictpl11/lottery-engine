from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain.models import Activity, Award, DrawOrder


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_activity_id(self, activity_id: int) -> Activity | None:
        return self.db.scalar(select(Activity).where(Activity.activity_id == activity_id))

    def get_surplus(self, activity_id: int) -> int:
        """当前剩余库存。用于 Redis key 缺失时的初始化（FR-7）。"""
        v = self.db.scalar(
            select(Activity.stock_surplus).where(Activity.activity_id == activity_id)
        )
        return int(v or 0)

    def create(self, activity: Activity) -> Activity:
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def decrement_stock_nocommit(self, activity_id: int) -> bool:
        """原子扣减活动库存，**不提交**。

        用单条带条件的 UPDATE 而不是"读出来判断再赋值"（缺陷 D1）：
        `WHERE stock_surplus > 0` 交给数据库在行锁内判断，rowcount 为 0 就说明
        没扣到。这是 Redis 闸门之外的第二道防线——即使 Redis 被清空导致放行过量，
        MySQL 这层仍然不会把库存扣成负数。

        提交由调用方与订单写入放在同一事务里完成（§4.6）。
        """
        result = self.db.execute(
            update(Activity)
            .where(Activity.activity_id == activity_id, Activity.stock_surplus > 0)
            .values(stock_surplus=Activity.stock_surplus - 1)
        )
        return result.rowcount == 1


class AwardRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_award_id(self, award_id: int) -> Award | None:
        return self.db.scalar(select(Award).where(Award.award_id == award_id))

    def list_by_activity(self, activity_id: int) -> list[Award]:
        """活动下的全部奖品，含已抽空的。

        与 list_available_by_activity 的区别：这个给展示用（要让人看到某个奖品
        已经没了），抽奖链路用的是只返回有库存的那个。
        """
        stmt = (
            select(Award)
            .where(Award.activity_id == activity_id)
            .order_by(Award.weight.desc())
        )
        return list(self.db.scalars(stmt).all())

    def list_available_by_activity(self, activity_id: int) -> list[Award]:
        stmt = (
            select(Award)
            .where(Award.activity_id == activity_id)
            .where(Award.stock_surplus > 0)
        )
        return list(self.db.scalars(stmt).all())

    def get_surplus(self, award_id: int) -> int:
        """当前剩余库存。用于 Redis key 缺失时的初始化（FR-7）。"""
        v = self.db.scalar(select(Award.stock_surplus).where(Award.award_id == award_id))
        return int(v or 0)

    def create(self, award: Award) -> Award:
        self.db.add(award)
        self.db.commit()
        self.db.refresh(award)
        return award

    def decrement_stock_nocommit(self, award_id: int) -> bool:
        """原子扣减奖品库存，**不提交**。理由同 ActivityRepository.decrement_stock_nocommit。"""
        result = self.db.execute(
            update(Award)
            .where(Award.award_id == award_id, Award.stock_surplus > 0)
            .values(stock_surplus=Award.stock_surplus - 1)
        )
        return result.rowcount == 1


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
