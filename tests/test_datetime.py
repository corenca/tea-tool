# ruff: noqa: DTZ001, DTZ005, DTZ007
# 本文件大量刻意构造 naive 时间，用于覆盖日历域（date/datetime 双态）与无时区字符串解析行为。
"""tea_tool.datetime 时间工具包的单元测试。"""

from datetime import date, datetime, timedelta, timezone

import pytest

from tea_tool.datetime.formatter import (
    DATE_TIME_FORMAT,
    DATE_TIME_FORMAT_CN,
    DATE_TIME_ISO,
    DATE_TIME_ISO_ZONE,
    DATE_TIME_MICROSECOND,
    DATE_TIME_ZONE,
    MONTH_FORMAT,
    TIME_FORMAT_MINUTE,
    YEAR_TO_MICROSECOND,
)
from tea_tool.datetime.timezone import (
    LOS_ANGELES,
    NEW_YORK,
    SHANGHAI,
    SYDNEY,
    UTC,
    local_tz,
)
from tea_tool.datetime.util import (
    get_day_range,
    get_day_start,
    get_days_in_month,
    get_local_time,
    get_month_end,
    get_month_start,
    get_utc_time,
    list_days,
    parse_datetime,
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


class TestFormatter:
    """formatter 格式化模板常量。"""

    def test_microsecond_templates_roundtrip(self) -> None:
        """微秒模板与 datetime 互转保持精度。"""
        value = datetime(2026, 1, 2, 3, 4, 5, 678901)
        assert (
            datetime.strptime(
                value.strftime(DATE_TIME_MICROSECOND), DATE_TIME_MICROSECOND
            )
            == value
        )
        assert (
            datetime.strptime(value.strftime(YEAR_TO_MICROSECOND), YEAR_TO_MICROSECOND)
            == value
        )

    def test_zone_template_carries_utc_offset(self) -> None:
        """ZONE 模板可 strftime/strptime 携带 +0800 偏移。"""
        value = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=8)))
        text = value.strftime(DATE_TIME_ZONE)
        parsed = datetime.strptime(text, DATE_TIME_ZONE)
        assert parsed.utcoffset() == timedelta(hours=8)
        assert parsed == value

    def test_iso_templates(self) -> None:
        """ISO 扩展 T 分隔模板按预期解析。"""
        assert datetime.strptime("2026-01-02T03:04:05", DATE_TIME_ISO) == datetime(
            2026, 1, 2, 3, 4, 5
        )
        parsed = datetime.strptime("2026-01-02T03:04:05+0800", DATE_TIME_ISO_ZONE)
        assert parsed.utcoffset() == timedelta(hours=8)

    def test_month_and_minute_templates(self) -> None:
        """MONTH/TIME_FORMAT_MINUTE 模板值正确。"""
        assert MONTH_FORMAT == "%Y-%m"
        assert TIME_FORMAT_MINUTE == "%H:%M"
        assert datetime(2026, 1, 1).strftime(MONTH_FORMAT) == "2026-01"
        assert datetime(2026, 1, 1, 9, 30).strftime(TIME_FORMAT_MINUTE) == "09:30"

    def test_chinese_template_roundtrip(self) -> None:
        """中文模板可正常 strftime/strptime 往返。"""
        value = datetime(2026, 1, 2, 3, 4, 5)
        assert value.strftime(DATE_TIME_FORMAT_CN) == "2026年01月02日 03时04分05秒"
        assert (
            datetime.strptime("2026年01月02日 03时04分05秒", DATE_TIME_FORMAT_CN)
            == value
        )


class TestMonthBoundary:
    """get_month_start / get_month_end 月份首末日。"""

    def test_month_start_no_offset(self) -> None:
        """无偏移时返回所在月首日。"""
        assert get_month_start(date(2026, 1, 15)) == date(2026, 1, 1)
        assert get_month_start(datetime(2026, 6, 30, 10, 30)) == date(2026, 6, 1)

    @pytest.mark.parametrize(
        ("value", "months", "expected"),
        [
            # 正偏移进入后续月份。
            (date(2026, 1, 15), 1, date(2026, 2, 1)),
            # 负偏移回到之前月份。
            (date(2026, 1, 15), -1, date(2025, 12, 1)),
            # 跨年偏移。
            (date(2026, 1, 15), 12, date(2027, 1, 1)),
            (date(2026, 1, 15), -12, date(2025, 1, 1)),
        ],
    )
    def test_month_start_offset(self, value: date, months: int, expected: date) -> None:
        """月份偏移后返回目标月首日。"""
        assert get_month_start(value, months) == expected

    def test_month_start_datetime_input_returns_date(self) -> None:
        """datetime 输入（含 aware）仅作年月基准，统一返回 date。"""
        value = datetime(2026, 1, 15, 10, 30, 5, 123456, tzinfo=SHANGHAI)
        assert get_month_start(value) == date(2026, 1, 1)
        assert get_month_start(value, 1) == date(2026, 2, 1)

    def test_month_end_no_offset(self) -> None:
        """无偏移时返回所在月末日。"""
        assert get_month_end(date(2026, 1, 31)) == date(2026, 1, 31)
        assert get_month_end(datetime(2026, 1, 15, 23, 59, 59)) == date(2026, 1, 31)

    @pytest.mark.parametrize(
        ("value", "months", "expected"),
        [
            # 平年 2 月 28 天。
            (date(2026, 1, 15), 1, date(2026, 2, 28)),
            # 闰年 2 月 29 天。
            (date(2024, 1, 15), 1, date(2024, 2, 29)),
            # 负偏移到上月末。
            (date(2026, 3, 31), -1, date(2026, 2, 28)),
        ],
    )
    def test_month_end_offset(self, value: date, months: int, expected: date) -> None:
        """月份偏移后返回目标月末日。"""
        assert get_month_end(value, months) == expected

    def test_month_end_datetime_input_returns_date(self) -> None:
        """datetime 输入（含 aware）仅作年月基准，统一返回 date。"""
        value = datetime(2026, 1, 15, 23, 59, 59, tzinfo=SHANGHAI)
        assert get_month_end(value) == date(2026, 1, 31)
        assert get_month_end(value, 1) == date(2026, 2, 28)


class TestDaysInMonth:
    """get_days_in_month 当月天数。"""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (date(2026, 2, 10), 28),
            (date(2024, 2, 10), 29),
            (date(2026, 4, 1), 30),
            (date(2026, 12, 1), 31),
            (datetime(2026, 2, 10, 8, 0), 28),
        ],
    )
    def test_days_in_month(self, value: date | datetime, expected: int) -> None:
        """date/datetime 输入均返回所在月天数。"""
        assert get_days_in_month(value) == expected


class TestDayStartAndRange:
    """get_day_start / get_day_range 当日零点与范围。"""

    def test_day_start_from_date(self) -> None:
        """date 输入返回当日 naive 零点。"""
        assert get_day_start(date(2026, 1, 15)) == datetime(2026, 1, 15)

    def test_day_start_from_naive_datetime(self) -> None:
        """naive datetime 清零时分秒与微秒。"""
        assert get_day_start(datetime(2026, 1, 15, 10, 30, 5, 123456)) == datetime(
            2026, 1, 15
        )

    def test_day_start_from_aware_datetime_keeps_tz(self) -> None:
        """aware datetime 保留时区并清零时刻。"""
        result = get_day_start(datetime(2026, 1, 15, 10, 30, tzinfo=SHANGHAI))
        assert result == datetime(2026, 1, 15, tzinfo=SHANGHAI)
        assert result.tzinfo is not None

    def test_day_range_naive(self) -> None:
        """date 输入返回 naive [零点, 次日零点)。"""
        assert get_day_range(date(2026, 1, 15)) == (
            datetime(2026, 1, 15),
            datetime(2026, 1, 16),
        )

    def test_day_range_naive_datetime_input(self) -> None:
        """naive datetime 输入与 date 等价（取所在日）。"""
        assert get_day_range(datetime(2026, 1, 15, 23, 59, 59)) == (
            datetime(2026, 1, 15),
            datetime(2026, 1, 16),
        )

    def test_day_range_aware_keeps_tz(self) -> None:
        """aware datetime 无 tz 参数时沿用其时区。"""
        start, end = get_day_range(datetime(2026, 1, 15, 10, 0, tzinfo=SHANGHAI))
        assert start == datetime(2026, 1, 15, tzinfo=SHANGHAI)
        assert end == datetime(2026, 1, 16, tzinfo=SHANGHAI)

    def test_day_range_explicit_tz(self) -> None:
        """tz 参数显式给出时两端 attach 该时区并覆盖输入时区。"""
        start, end = get_day_range(date(2026, 1, 15), tz=UTC)
        assert start.utcoffset() == timedelta(0)
        assert end.utcoffset() == timedelta(0)
        # 输入自带时区被显式 tz 覆盖。
        start, end = get_day_range(
            datetime(2026, 1, 15, 10, 0, tzinfo=SHANGHAI), tz=UTC
        )
        assert start.utcoffset() == timedelta(0)
        assert end.utcoffset() == timedelta(0)

    def test_day_range_dst_clock_boundary(self) -> None:
        """DST 切换日两端仍为该时区钟面零点（偏移随之变化）。"""
        # 2026-03-08 为纽约进入夏令时当日（02:00 跳变）。
        start, end = get_day_range(date(2026, 3, 8), tz=NEW_YORK)
        assert start.utcoffset() == timedelta(hours=-5)
        assert end.utcoffset() == timedelta(hours=-4)


class TestListDays:
    """list_days 逐日日期序列。"""

    def test_list_days_basic(self) -> None:
        """左闭右开逐日列出。"""
        assert list_days(date(2026, 1, 1), date(2026, 1, 3)) == [
            date(2026, 1, 1),
            date(2026, 1, 2),
        ]

    def test_list_days_cross_year(self) -> None:
        """跨年连续列出。"""
        assert list_days(date(2025, 12, 30), date(2026, 1, 2)) == [
            date(2025, 12, 30),
            date(2025, 12, 31),
            date(2026, 1, 1),
        ]

    def test_list_days_empty_when_start_ge_end(self) -> None:
        """start 等于或晚于 end 时为空列表。"""
        assert list_days(date(2026, 1, 1), date(2026, 1, 1)) == []
        assert list_days(date(2026, 1, 3), date(2026, 1, 1)) == []


class TestNowAndParse:
    """get_local_time / get_utc_time / parse_datetime 时刻获取。"""

    def test_get_local_time_aware(self) -> None:
        """get_local_time 返回 aware 本地时刻，偏移与本地时区一致。"""
        result = get_local_time()
        assert result.tzinfo is not None
        assert result.utcoffset() == local_tz().utcoffset(result)

    def test_get_utc_time_aware(self) -> None:
        """get_utc_time 返回 aware 时刻且偏移为零。"""
        result = get_utc_time()
        assert result.tzinfo is not None
        assert result.utcoffset() == timedelta(0)

    def test_now_wall_clock_gap_matches_offset(self) -> None:
        """本地与 UTC 的墙钟差等于本地偏移（容忍秒级执行间隔）。"""
        utc_now = get_utc_time()
        local_now = get_local_time()
        naive_local = local_now.replace(tzinfo=None)
        naive_utc = utc_now.replace(tzinfo=None)
        assert abs((naive_local - naive_utc) - local_now.utcoffset()) < timedelta(
            seconds=5
        )

    def test_parse_datetime_default_local(self) -> None:
        """无 tz 参数时解析结果 attach 系统本地时区。"""
        result = parse_datetime("2026-01-15 10:30:00", DATE_TIME_FORMAT)
        assert result.tzinfo is not None
        assert result.utcoffset() == local_tz().utcoffset(result)

    def test_parse_datetime_explicit_tz(self) -> None:
        """显式 tz 时解析结果 attach 指定时区。"""
        result = parse_datetime("2026-01-15 10:30:00", DATE_TIME_FORMAT, tz=UTC)
        assert result.utcoffset() == timedelta(0)

    def test_parse_datetime_fmt_with_zone_ignores_tz(self) -> None:
        """模板含 %z 时以字符串自带偏移为准，忽略 tz 参数。"""
        result = parse_datetime("2026-01-02T03:04:05+0800", DATE_TIME_ISO_ZONE, tz=UTC)
        assert result.utcoffset() == timedelta(hours=8)

    def test_parse_datetime_microsecond(self) -> None:
        """微秒模板解析并保留微秒。"""
        result = parse_datetime("2026-01-15 10:30:00.123456", DATE_TIME_MICROSECOND)
        assert result.microsecond == 123456
        assert result.tzinfo is not None

    def test_parse_datetime_invalid_raises(self) -> None:
        """格式不匹配时抛 ValueError。"""
        with pytest.raises(ValueError):
            parse_datetime("not a date", DATE_TIME_FORMAT)
