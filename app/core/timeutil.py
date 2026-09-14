"""时间与时区约定。见 REQUIREMENTS.md §4.4。

约定：
- 数据库列是 naive DATETIME，一律存 **UTC** 时刻（SQLite 与 MySQL 的 DATETIME
  都不带时区，把时区信息交给应用层显式处理，比依赖驱动的隐式行为可靠）。
- 应用内部一律使用 timezone-aware datetime。
- 进出数据库的边界由 to_db / from_db 显式转换。
- API 入参要求带时区偏移（由 schema 的 AwareDatetime 保证），不接受 naive 值，
  避免"用户按北京时间填、服务端按 UTC 解释"这类静默错误（缺陷 D4）。
"""

from datetime import datetime, timedelta, timezone

UTC = timezone.utc

# 中国自 1991 年起全境使用单一时区且不再实行夏令时，固定 +08:00 偏移是精确的。
# 因此这里不引入 zoneinfo/tzdata 依赖（Windows 上 zoneinfo 还需额外安装 tzdata）。
CHINA_TZ = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """当前时刻，timezone-aware UTC。替代已废弃且语义误导的 datetime.utcnow()。"""
    return datetime.now(UTC)


def utc_now_naive() -> datetime:
    """当前时刻的 naive UTC 表示，用作数据库列默认值。"""
    return to_db(utc_now())


def to_db(value: datetime) -> datetime:
    """写库方向：转成 naive UTC。naive 输入视为已是 UTC，原样返回。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def from_db(value: datetime) -> datetime:
    """读库方向：给 naive UTC 补上 tzinfo，使其可与 utc_now() 直接比较。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def china_day_key(value: datetime) -> str:
    """自然日键，按 Asia/Shanghai 日界计算（REQUIREMENTS.md §4.4）。

    用于每日参与次数（FR-6b）。日界必须是业务所在时区，不能直接用 UTC 日界，
    否则北京时间每天早上 8 点配额才会重置。
    """
    return from_db(value).astimezone(CHINA_TZ).strftime("%Y%m%d")


def seconds_until_china_midnight(value: datetime) -> int:
    """距离下一个 Asia/Shanghai 零点还有多少秒。

    用作每日配额 key 的 TTL：key 自己到点过期，不需要任何清理任务。
    至少返回 60 秒，避免正好卡在零点时算出过短甚至为 0 的 TTL。
    """
    local = from_db(value).astimezone(CHINA_TZ)
    tomorrow = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(int((tomorrow - local).total_seconds()), 60)
