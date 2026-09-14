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


class DependencyUnavailableError(LotteryError):
    """外部依赖（Redis）不可用。

    映射为 HTTP 503。这是刻意的**快速失败**：Redis 承担原子库存、限流和幂等，
    它不可用时若继续放行，超卖和重复发奖都会发生。宁可拒绝服务，也不产生
    无法回滚的业务错误。见 README 的 Known Limitations。
    """


class DuplicateRequestError(LotteryError):
    """同一 request_id 正在处理中。

    映射为 HTTP 409。客户端应当把首次请求的结果视为准，而不是继续重试。
    """

    def __init__(self, request_id: str):
        self.request_id = request_id
        super().__init__(f"请求正在处理中，请勿重复提交: {request_id}")
