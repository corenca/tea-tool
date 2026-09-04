# ruff: noqa: DTZ005
"""tea_tool.datetime.timezone 时区常量与本地时区获取的单元测试。"""

from datetime import datetime, timedelta

from tea_tool.datetime.timezone import (
    LOS_ANGELES,
    NEW_YORK,
    SHANGHAI,
    SYDNEY,
    UTC,
    local_tz,
)


class TestTimezone:
    """timezone 时区常量与本地时区获取。"""

    def test_zoneinfo_keys(self) -> None:
        """常量指向预期 IANA 时区。"""
        assert UTC.key == "UTC"
        assert SHANGHAI.key == "Asia/Shanghai"
        assert NEW_YORK.key == "America/New_York"
        assert LOS_ANGELES.key == "America/Los_Angeles"
        assert SYDNEY.key == "Australia/Sydney"

    def test_constants_are_usable_as_tzinfo(self) -> None:
        """常量可直接构造 aware datetime 并给出正确偏移。"""
        assert datetime(2026, 1, 1, tzinfo=SHANGHAI).utcoffset() == timedelta(hours=8)
        # 纽约 1 月为冬令时（UTC-5）。
        assert datetime(2026, 1, 1, tzinfo=NEW_YORK).utcoffset() == timedelta(hours=-5)

    def test_local_tz_matches_astimezone(self) -> None:
        """local_tz 与 astimezone 无参结果的时区偏移一致。"""
        now = datetime.now()
        assert local_tz().utcoffset(now) == now.astimezone().utcoffset()
