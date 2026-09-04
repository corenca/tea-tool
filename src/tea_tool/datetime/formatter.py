"""日期时间 strftime/strptime 格式化模板常量。

常量按粒度组织：DATE（日）、TIME（时间）、DATE_TIME（日期时间）、MONTH（月）与
YEAR 系压缩串（%Y%m%d…，常用于文件名/键）。同一粒度提供连字符（默认）、斜杠
（_SLASH）、中文（_CN）分隔变体；后缀 _ZONE 携带 %z 时区偏移、_ISO 为 ISO 8601
扩展 T 分隔。注意：%f 恒为 6 位微秒且 strftime 不支持截宽，故含 %f 的模板按
微秒（MICROSECOND）命名；%z 输出形如 +0800 无冒号（近似 RFC 3339，非严格）。
"""

# 日期
DATE_FORMAT = "%Y-%m-%d"
DATE_FORMAT_SLASH = "%Y/%m/%d"
DATE_FORMAT_CN = "%Y年%m月%d日"

# 时间
TIME_FORMAT = "%H:%M:%S"
TIME_FORMAT_MINUTE = "%H:%M"
TIME_FORMAT_SLASH = "%H/%M/%S"
TIME_FORMAT_CN = "%H时%M分%S秒"

# 日期时间
DATE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_TIME_FORMAT_SLASH = "%Y/%m/%d %H:%M:%S"
DATE_TIME_FORMAT_CN = "%Y年%m月%d日 %H时%M分%S秒"
DATE_TIME_MICROSECOND = "%Y-%m-%d %H:%M:%S.%f"
DATE_TIME_ZONE = "%Y-%m-%d %H:%M:%S%z"
DATE_TIME_ISO = "%Y-%m-%dT%H:%M:%S"
DATE_TIME_ISO_ZONE = "%Y-%m-%dT%H:%M:%S%z"

# 月
MONTH_FORMAT = "%Y-%m"

# 年份系压缩串（无分隔符，常用于文件名/键）
YEAR = "%Y"
YEAR_TO_MONTH = "%Y%m"
YEAR_TO_DAY = "%Y%m%d"
YEAR_TO_HOUR = "%Y%m%d%H"
YEAR_TO_MINUTE = "%Y%m%d%H%M"
YEAR_TO_SECOND = "%Y%m%d%H%M%S"
YEAR_TO_MICROSECOND = "%Y%m%d%H%M%S.%f"
