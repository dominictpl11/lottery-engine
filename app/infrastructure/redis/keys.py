"""Redis key 命名。

统一前缀 `lottery:`，便于运维时按前缀观察或清理。
key 里只放业务标识，不放用户可控的自由文本。
"""


def activity_stock(activity_id: int) -> str:
    return f"lottery:stock:activity:{activity_id}"


def award_stock(award_id: int) -> str:
    return f"lottery:stock:award:{award_id}"


def rate_limit(activity_id: int, user_id: str) -> str:
    return f"lottery:rate:{activity_id}:{user_id}"


def daily_quota(activity_id: int, user_id: str, day: str) -> str:
    return f"lottery:daily:{activity_id}:{user_id}:{day}"


def idempotency(request_id: str) -> str:
    return f"lottery:idem:{request_id}"
