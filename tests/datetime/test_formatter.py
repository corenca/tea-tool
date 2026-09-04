# ruff: noqa: DTZ001, DTZ007
"""tea_tool.datetime.formatter 格式化模板常量的单元测试。"""

from datetime import datetime, timedelta, timezone

from tea_tool.datetime.formatter import (
    DATE_TIME_FORMAT_CN,
    DATE_TIME_ISO,
    DATE_TIME_ISO_ZONE,
    DATE_TIME_MICROSECOND,
    DATE_TIME_ZONE,
    MONTH_FORMAT,
    TIME_FORMAT_MINUTE,
    YEAR_TO_MICROSECOND,
)


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
