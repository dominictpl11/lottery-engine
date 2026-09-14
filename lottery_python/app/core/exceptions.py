"""领域异常。

应用层与领域层不直接依赖 FastAPI，异常在 main.py 中统一映射为 HTTP 响应
（REQUIREMENTS.md §5.2：业务逻辑不得堆在 Controller）。
"""


class LotteryError(Exception):
    """本项目所有业务异常的基类。"""


class ActivityNotFoundError(LotteryError):
    """活动不存在。

    按 REQUIREMENTS.md §4.5，这类请求返回 404 且**不落抽奖订单**——否则任意
    activity_id 都能往 draw_order 里写一行，形成刷库入口（缺陷 D7）。
    """

    def __init__(self, activity_id: int):
        self.activity_id = activity_id
        super().__init__(f"活动不存在: {activity_id}")


class DrawPersistenceError(LotteryError):
    """抽奖结果写库失败。

    此时活动库存与当日配额已被占用，调用方必须先补偿再抛出（§4.6 的失败点表）。
    映射为 HTTP 500：这是系统错误，不是业务拒绝，应当计入压测失败率（§7.2）。
    """
