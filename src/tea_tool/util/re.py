"""集中管理的预编译正则模式。

本模块统一存放常见正则：各模式均带前后边界断言（lookbehind/lookahead），
在自由文本中只命中独立成串的目标，避免子串误伤；
目标是否为真实有效格式（身份证校验位、银行卡 Luhn、区号真实性等）不在本
层校验，由使用方按需补充。

模块内常量的值均为预编译的 re.Pattern，命名以 *_RE_PATTERN 结尾，与
字符串型模式文本区分。
"""

import re

# 手机号：1[3-9] 开头，共 11 位
PHONE_RE_PATTERN: re.Pattern[str] = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


# 固话：支持
# 010-12345678
# 010-1234567
# 02112345678
# 400-123-4567
TELEPHONE_RE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<!\d)"
    r"(?:"
    r"0\d{2,3}[- ]?\d{7,8}"
    r"|"
    r"400[- ]?\d{3}[- ]?\d{4}"
    r")"
    r"(?!\d)"
)


# 中国大陆身份证：
# 18 位：前 17 位数字 + 数字/X
# 15 位老身份证
ID_CARD_RE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<!\d)"
    r"(?:"
    r"\d{17}[\dXx]"
    r"|"
    r"\d{15}"
    r")"
    r"(?!\d)"
)


# 邮箱
EMAIL_RE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![\w.+-])"
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@"
    r"[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
    r"(?![\w.-])"
)


# 银行卡号：常见 13~19 位数字
BANK_CARD_RE_PATTERN: re.Pattern[str] = re.compile(r"(?<!\d)\d{13,19}(?!\d)")


# IPv4
IPV4_RE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![\d.])"
    r"(?:"
    r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)"
    r"\."
    r"){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)"
    r"(?![\d.])"
)


# IPv6：简单版本（不含内嵌 IPv4 如 ::ffff:1.2.3.4 等形态）。大小写不敏感
# 通过编译期 re.IGNORECASE 实现，避免内联 (?i) 在模式拼接时非法。
IPV6_RE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![0-9a-f:])"
    r"(?:"
    r"(?:[0-9a-f]{1,4}:){7}[0-9a-f]{1,4}"
    r"|"
    r"(?:[0-9a-f]{1,4}:){1,7}:"
    r"|"
    r"(?:[0-9a-f]{1,4}:){1,6}:[0-9a-f]{1,4}"
    r"|"
    r"(?:[0-9a-f]{1,4}:){1,5}(?::[0-9a-f]{1,4}){1,2}"
    r"|"
    r"(?:[0-9a-f]{1,4}:){1,4}(?::[0-9a-f]{1,4}){1,3}"
    r"|"
    r"(?:[0-9a-f]{1,4}:){1,3}(?::[0-9a-f]{1,4}){1,4}"
    r"|"
    r"(?:[0-9a-f]{1,4}:){1,2}(?::[0-9a-f]{1,4}){1,5}"
    r"|"
    r"[0-9a-f]{1,4}:(?:(?::[0-9a-f]{1,4}){1,6})"
    r"|"
    r":(?:(?::[0-9a-f]{1,4}){1,7}|:)"
    r")"
    r"(?![0-9a-f:])",
    re.IGNORECASE,
)


# IPv4 + IPv6：拼接两分支的 .pattern 文本后整体编译，大小写不敏感沿用
# 编译期 flag，使 IPv6 分支保留十六进制大小写匹配能力。
IP_RE_PATTERN: re.Pattern[str] = re.compile(
    rf"(?:{IPV4_RE_PATTERN.pattern}|{IPV6_RE_PATTERN.pattern})",
    re.IGNORECASE,
)
