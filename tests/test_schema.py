"""tea_tool.schema 数据模型基类与字段别名的单元测试。"""

from datetime import UTC, date, datetime, timedelta, timezone

from tea_tool.datetime.formatter import DATE_TIME_FORMAT
from tea_tool.schema import BaseModel, DateField, DateTimeField, LocalDateTimeField


class DateTimeModel(BaseModel):
    """含 naive/aware 各类 datetime 字段的测试模型。"""

    local: LocalDateTimeField


class RawModel(BaseModel):
    """同时使用两种 datetime 字段的测试模型，用于对齐比较。"""

    plain: DateTimeField
    local: LocalDateTimeField
    d: DateField


class TestLocalDateTimeField:
    """LocalDateTimeField 的 json 序列化行为。"""

    def test_naive_keeps_original_value(self) -> None:
        """naive 输入按原值格式化，与 DateTimeField 输出一致。"""
        # 刻意构造 naive 时间以覆盖 naive 序列化路径
        naive = datetime(2026, 9, 4, 18, 30, 45)  # noqa: DTZ001
        raw = RawModel(plain=naive, local=naive, d=date(2026, 9, 4))
        payload = raw.model_dump_json()
        assert f'"plain":"{naive.strftime(DATE_TIME_FORMAT)}"' in payload
        assert f'"local":"{naive.strftime(DATE_TIME_FORMAT)}"' in payload

    def test_aware_converts_to_local_wall_clock(self) -> None:
        """aware 输入先转系统本地时区再格式化，输出为本地墙钟时间。"""
        aware = datetime(2026, 9, 4, 10, 30, 45, tzinfo=UTC)
        model = DateTimeModel(local=aware)
        expected = aware.astimezone().strftime(DATE_TIME_FORMAT)
        assert model.model_dump_json() == f'{{"local":"{expected}"}}'

    def test_aware_fixed_offset_also_converted(self) -> None:
        """固定偏移 aware 输入同样转换到系统本地时区。"""
        aware = datetime(2026, 9, 4, 18, 30, 45, tzinfo=timezone(timedelta(hours=8)))
        model = DateTimeModel(local=aware)
        expected = aware.astimezone().strftime(DATE_TIME_FORMAT)
        assert model.model_dump_json() == f'{{"local":"{expected}"}}'

    def test_microsecond_truncated_like_datetime_field(self) -> None:
        """微秒精度截断，与 DateTimeField 现状保持一致。"""
        aware = datetime(2026, 9, 4, 10, 30, 45, 123456, tzinfo=UTC)
        model = DateTimeModel(local=aware)
        expected = aware.astimezone().strftime(DATE_TIME_FORMAT)
        assert model.model_dump_json() == f'{{"local":"{expected}"}}'

    def test_json_output_can_roundtrip(self) -> None:
        """json 输出可被 pydantic 解析回等价 datetime。"""
        aware = datetime(2026, 9, 4, 10, 30, 45, tzinfo=UTC)
        origin = DateTimeModel(local=aware)
        restored = DateTimeModel.model_validate_json(origin.model_dump_json())
        # 序列化走本地墙钟，反序列化回到 naive 等价时刻（比较重放后的本地墙钟）
        assert restored.local == aware.astimezone().replace(tzinfo=None)

    def test_dump_stays_datetime_when_not_json(self) -> None:
        """非 json 模式（model_dump）保持 datetime 对象不转换。"""
        aware = datetime(2026, 9, 4, 10, 30, 45, tzinfo=UTC)
        model = DateTimeModel(local=aware)
        assert model.model_dump()["local"] == aware
