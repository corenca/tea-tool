"""datetime 日期时间通用工具。

提供日历运算（月份首末日、逐日序列）与时刻获取（日零点、当日时间范围、
本地/UTC 当前时间、字符串解析）。日历运算中的月份首末日与逐日序列
（get_month_start、get_month_end、list_days）仅接受 date；get_days_in_month
接受 date/datetime（仅用其年月）。时刻类函数（get_day_start、get_day_range、
get_local_time、get_utc_time、parse_datetime）产出 datetime：date 输入按该日
提升，datetime 输入保留 naive/aware 属性。时区语义：本模块只做钟面解释
（attach），不做跨时区换算；"本地时区"指系统时区，可用 timezone.local_tz()
获取。
"""

from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta, tzinfo

from .timezone import local_tz


def _shift_year_month(value: date | datetime, months: int) -> tuple[int, int]:
    """计算 value 所在月偏移 months 个月后的 (年, 月)。

    months 为负时同样正确（divmod 对负值取整向负无穷），例如 2026-01 偏移 -1
    得到 (2025, 12)。

    Args:
        value: 基准日期或时间，取其所在年与月。
        months: 月份偏移量。

    Returns:
        偏移后的 (年, 月) 二元组。
    """
    total = value.year * 12 + (value.month - 1) + months
    year, month_index = divmod(total, 12)
    return year, month_index + 1


def get_month_start(value: date | datetime, months: int = 0) -> date:
    """返回 value 所在月偏移 months 个月后的首日。

    months 为正表示偏移到之后的月份、为负表示之前的月份，0（默认）即 value 所在
    当月。value 无论 date 还是 datetime 均统一返回 date（datetime 仅取其年与月，
    不带时分秒与时区），例如 2026-01-31 10:30 偏移 1 个月返回 2026-02-01。

    Args:
        value: 基准日期或时间，取其所在月。
        months: 月份偏移量，正为后负为前，默认当月。

    Returns:
        目标月首日（date）。
    """
    year, month = _shift_year_month(value, months)
    return date(year, month, 1)


def get_month_end(value: date | datetime, months: int = 0) -> date:
    """返回 value 所在月偏移 months 个月后的末日。

    月份偏移语义与 get_month_start 一致（正后负前，0 为当月）；返回目标月的最后
    一天，跨月取末日不受 value 原日影响，例如 2026-01-31 偏移 1 个月返回
    2026-02-28。value 无论 date 还是 datetime 均统一返回 date（datetime 仅取其
    年与月，不带时分秒与时区）。

    Args:
        value: 基准日期或时间，取其所在月。
        months: 月份偏移量，正为后负为前，默认当月。

    Returns:
        目标月末日（date）。
    """
    year, month = _shift_year_month(value, months)
    last = monthrange(year, month)[1]
    return date(year, month, last)


def get_days_in_month(value: date | datetime) -> int:
    """返回 value 所在月的天数。

    Args:
        value: 基准日期或时间，取其所在月。

    Returns:
        所在月的天数（平年 2 月为 28、闰年为 29）。
    """
    return monthrange(value.year, value.month)[1]


def get_day_start(value: date | datetime) -> datetime:
    """返回 value 所在日的零点时刻。

    时刻域函数：date 输入提升为当日 00:00 的 naive datetime；naive datetime 清零
    时分秒与微秒；aware datetime 清零时刻但保留其 tzinfo（DST 切换日零点通常无
    歧义，不做 fold 处理）。

    Args:
        value: 基准日期或时间，取其所在日。

    Returns:
        所在日零点对应的 datetime（naive 或保留输入的 aware 属性）。
    """
    if isinstance(value, datetime):
        return value.replace(hour=0, minute=0, second=0, microsecond=0)
    return datetime.combine(value, time.min)


def get_day_range(
    value: date | datetime, tz: tzinfo | None = None
) -> tuple[datetime, datetime]:
    """返回 value 所在日的时间范围 [当日零点, 次日零点)，左闭右开。

    时刻域函数，返回值恒为 datetime 对。时区规则：
    - tz 显式给出时，两端钟面时间 attach 该时区（覆盖 value 自带时区，不换算）；
    - tz 缺省且 value 为 aware datetime 时，沿用 value 的时区；
    - 其余情形（date / naive datetime）两端为 naive。
    DST 切换日该范围的实际时长可能非 24 小时，但两端恒为该时区钟面零点。

    Args:
        value: 基准日期或时间，取其所在日。
        tz: 目标时区；缺省时沿用输入时区或保持 naive。

    Returns:
        (当日零点, 次日零点) 元组。
    """
    if isinstance(value, datetime):
        day = value.date()
        resolved = tz if tz is not None else value.tzinfo
    else:
        day = value
        resolved = tz
    return (
        datetime.combine(day, time.min, tzinfo=resolved),
        datetime.combine(day + timedelta(days=1), time.min, tzinfo=resolved),
    )


def list_days(start: date, end: date) -> list[date]:
    """返回 [start, end) 区间内逐日 date 序列，左闭右开不含 end。

    start 等于或晚于 end 时返回空列表。

    Args:
        start: 起始日期（含）。
        end: 结束日期（不含）。

    Returns:
        逐日 date 序列；start >= end 时为空列表。
    """
    result: list[date] = []
    cursor = start
    while cursor < end:
        result.append(cursor)
        cursor += timedelta(days=1)
    return result


def get_local_time() -> datetime:
    """返回系统本地时区的当前时刻（aware）。

    Returns:
        带系统本地时区的当前 datetime。
    """
    return datetime.now().astimezone()


def get_utc_time() -> datetime:
    """返回 UTC 的当前时刻（aware）。

    Returns:
        带 UTC 时区的当前 datetime。
    """
    return datetime.now(UTC)


def parse_datetime(text: str, fmt: str, tz: tzinfo | None = None) -> datetime:
    """按格式化模板将时间字符串解析为 aware datetime。

    结果为钟面解释：模板不含 %z 指令（字符串无时区信息）时，将解析出的钟面
    时间 attach 到 tz（缺省为系统本地时区）；模板含 %z 指令时解析结果自带偏移
    并直接返回，此时忽略 tz 参数。DST 歧义时刻按钟面解释，不做特殊折叠处理。

    Args:
        text: 待解析的时间字符串。
        fmt: strptime 格式化模板，可复用 tea_tool.datetime.formatter 常量。
        tz: attach 目标时区，缺省为系统本地时区；模板含 %z 时无效。

    Returns:
        解析得到的 aware datetime。

    Raises:
        ValueError: 当 text 与 fmt 不匹配时（strptime 原生异常）。
    """
    parsed = datetime.strptime(text, fmt)  # noqa: DTZ007 解析结果 naive 时后续按 tz 参数 attach 时区
    if parsed.tzinfo is not None:
        return parsed
    return parsed.replace(tzinfo=tz if tz is not None else local_tz())
