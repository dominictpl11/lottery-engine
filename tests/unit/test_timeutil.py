"""时区约定（§4.4）。这些约定是缺陷 D4 的修复，必须有回归保护。"""

from datetime import datetime, timedelta, timezone

from app.core.timeutil import (
    CHINA_TZ,
    UTC,
    china_day_key,
    from_db,
    seconds_until_china_midnight,
    to_db,
    utc_now,
    utc_now_naive,
)


def test_utc_now_is_aware():
    assert utc_now().tzinfo is not None


def test_utc_now_naive_has_no_tzinfo():
    """库里存的必须是 naive，否则 SQLAlchemy 写 DATETIME 列会出问题。"""
    assert utc_now_naive().tzinfo is None


def test_to_db_converts_beijing_to_utc():
    bj = datetime(2026, 9, 14, 18, 0, 0, tzinfo=CHINA_TZ)
    assert to_db(bj) == datetime(2026, 9, 14, 10, 0, 0)


def test_from_db_attaches_utc():
    naive = datetime(2026, 9, 14, 10, 0, 0)
    assert from_db(naive) == datetime(2026, 9, 14, 10, 0, 0, tzinfo=UTC)


def test_round_trip_preserves_instant():
    original = datetime(2026, 9, 14, 18, 30, tzinfo=CHINA_TZ)
    assert from_db(to_db(original)) == original


def test_from_db_allows_comparison_with_utc_now():
    """D4 的核心：库里取出的 naive 值补上 tzinfo 后才能与 aware 的 now 比较。"""
    past = to_db(utc_now() - timedelta(hours=1))
    assert from_db(past) < utc_now()


def test_china_day_key_uses_beijing_boundary():
    """UTC 的 16:00 已经是北京的次日，日界必须按业务时区算。"""
    utc_evening = datetime(2026, 9, 14, 16, 30, tzinfo=UTC)
    assert china_day_key(utc_evening) == "20260915"
    utc_morning = datetime(2026, 9, 14, 15, 30, tzinfo=UTC)
    assert china_day_key(utc_morning) == "20260914"


def test_seconds_until_china_midnight_is_within_a_day():
    ttl = seconds_until_china_midnight(utc_now())
    assert 60 <= ttl <= 86400


def test_seconds_until_midnight_has_floor():
    """正好卡在零点时不能算出 0 或负数 TTL，否则 key 立刻过期。"""
    just_before = datetime(2026, 9, 14, 15, 59, 59, tzinfo=UTC)  # 北京 23:59:59
    assert seconds_until_china_midnight(just_before) >= 60
