"""常用时区常量与本地时区获取。

常量覆盖 UTC 及主流业务城市的 IANA 时区（UTC-12 ~ UTC+14 各主要时区带），
命名统一全大写、多词下划线分隔，可直接作为 tzinfo 参数传入 datetime 相关
构造与 tea_tool.datetime.util 各函数。依赖 zoneinfo（Python 3.9+ 内置），
具体时区数据取自已安装的 tzdata。
"""

from datetime import datetime, tzinfo
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")

# 亚洲
SHANGHAI = ZoneInfo("Asia/Shanghai")
SINGAPORE = ZoneInfo("Asia/Singapore")
TOKYO = ZoneInfo("Asia/Tokyo")
SEOUL = ZoneInfo("Asia/Seoul")
HONG_KONG = ZoneInfo("Asia/Hong_Kong")
BANGKOK = ZoneInfo("Asia/Bangkok")
DUBAI = ZoneInfo("Asia/Dubai")
KOLKATA = ZoneInfo("Asia/Kolkata")

# 欧洲
LONDON = ZoneInfo("Europe/London")
PARIS = ZoneInfo("Europe/Paris")
BERLIN = ZoneInfo("Europe/Berlin")
AMSTERDAM = ZoneInfo("Europe/Amsterdam")
MOSCOW = ZoneInfo("Europe/Moscow")

# 美洲
NEW_YORK = ZoneInfo("America/New_York")
LOS_ANGELES = ZoneInfo("America/Los_Angeles")
CHICAGO = ZoneInfo("America/Chicago")
TORONTO = ZoneInfo("America/Toronto")
SAO_PAULO = ZoneInfo("America/Sao_Paulo")

# 大洋洲
SYDNEY = ZoneInfo("Australia/Sydney")
AUCKLAND = ZoneInfo("Pacific/Auckland")

# 非洲
JOHANNESBURG = ZoneInfo("Africa/Johannesburg")


def local_tz() -> tzinfo:
    """返回系统本地时区。

    本地时区取自运行环境（TZ 环境变量或系统设置），与 datetime.now().astimezone()
    的时区归属一致；系统时区可被识别为具体区域时返回 ZoneInfo，否则退化为固定
    偏移时区。

    Returns:
        当前系统本地时区对应的 tzinfo 对象。
    """
    local = datetime.now().astimezone().tzinfo
    assert local is not None
    return local
