"""pydantic 数据模型基类与时间字段序列化别名。

BaseModel 统一项目内模型的 pydantic 配置：支持从 ORM/普通对象读取属性、
赋值时重新校验、按字段名反序列化、忽略未声明字段，并允许标注非 pydantic
类型。DateTimeField/DateField/LocalDateTimeField 供模型字段标注：json
序列化时将 date/datetime 输出为固定格式字符串（DateField 用 DATE_FORMAT，
DateTimeField/LocalDateTimeField 用 DATE_TIME_FORMAT，秒级、不含时区偏移），
其余模式（如 model_dump）保持原生类型。LocalDateTimeField 对 aware 输入会
先转换到系统本地时区再输出，naive 输入按原值输出，精度与 DateTimeField 一致。
"""

from datetime import date, datetime
from typing import Annotated

import pydantic
from pydantic import PlainSerializer
from pydantic.config import ConfigDict

from .datetime.formatter import DATE_FORMAT, DATE_TIME_FORMAT

DateTimeField = Annotated[
    datetime,
    PlainSerializer(
        lambda v: v.strftime(DATE_TIME_FORMAT),
        return_type=str,
        when_used="json",
    ),
]


def _serialize_local(dt: datetime) -> str:
    """将 datetime 序列化为系统本地时间字符串（供 json 模式使用）。

    naive 输入按原值格式化；aware 输入先转换到系统本地时区再格式化，
    输出统一为 DATE_TIME_FORMAT（不含时区偏移与微秒）。

    Args:
        dt: 待序列化的 datetime，naive 或 aware 均可。

    Returns:
        系统本地时间字符串，形如 2026-09-04 18:30:45。
    """
    if dt.utcoffset() is None:
        # naive 直接按原值格式化
        return dt.strftime(DATE_TIME_FORMAT)
    # aware 先转系统本地时区再格式化
    return dt.astimezone().strftime(DATE_TIME_FORMAT)


LocalDateTimeField = Annotated[
    datetime,
    PlainSerializer(_serialize_local, return_type=str, when_used="json"),
]

DateField = Annotated[
    date,
    PlainSerializer(
        lambda v: v.strftime(DATE_FORMAT),
        return_type=str,
        when_used="json",
    ),
]


class BaseModel(pydantic.BaseModel):
    """项目数据模型统一基类，预设常用 pydantic 配置。

    model_config 各选项含义：

    - from_attributes: 可从 ORM 等普通对象读取属性完成初始化。
    - validate_assignment: 实例属性赋值时重新校验类型。
    - populate_by_name: 反序列化时接受按字段名传入。
    - extra="ignore": 忽略输入中未声明的多余字段。
    - arbitrary_types_allowed: 允许字段标注非 pydantic 类型。
    """

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        populate_by_name=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )
