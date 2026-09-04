"""tea_tool.util.re 预编译正则常量的单元测试。

用例以整串匹配（fullmatch）验证各模式的边界断言与结构约束：模式都带
lookbehind/lookahead，fullmatch 下能表达"独立成串"的目标语义。自由文本
中 search 的行为由 masking 层的掩码测试覆盖。
"""

import re

import pytest

from tea_tool.util.re import (
    BANK_CARD_RE_PATTERN,
    EMAIL_RE_PATTERN,
    ID_CARD_RE_PATTERN,
    IP_RE_PATTERN,
    IPV4_RE_PATTERN,
    IPV6_RE_PATTERN,
    PHONE_RE_PATTERN,
    TELEPHONE_RE_PATTERN,
)

# (模式, 文本, 是否应整串匹配)。反例多为等长/相邻长度的结构违规。
_CASES: tuple[tuple[re.Pattern[str], str, bool], ...] = (
    # 手机号：1[3-9] 开头共 11 位。
    (PHONE_RE_PATTERN, "13812345678", True),
    (PHONE_RE_PATTERN, "19912345678", True),
    (PHONE_RE_PATTERN, "12812345678", False),
    (PHONE_RE_PATTERN, "10012345678", False),
    (PHONE_RE_PATTERN, "1381234567", False),
    (PHONE_RE_PATTERN, "138123456789", False),
    # 固话：0 区号 + 7/8 位号码，或 400 号码（不校验区号真实性）。
    (TELEPHONE_RE_PATTERN, "010-12345678", True),
    (TELEPHONE_RE_PATTERN, "01012345678", True),
    (TELEPHONE_RE_PATTERN, "021-1234567", True),
    (TELEPHONE_RE_PATTERN, "400-123-4567", True),
    (TELEPHONE_RE_PATTERN, "4001234567", True),
    (TELEPHONE_RE_PATTERN, "010-123456", False),
    (TELEPHONE_RE_PATTERN, "400-1234-567", False),
    (TELEPHONE_RE_PATTERN, "12345678", False),
    # 身份证：18 位（含末位 X/x）或 15 位老证。
    (ID_CARD_RE_PATTERN, "110105194912310021", True),
    (ID_CARD_RE_PATTERN, "11010519491231002X", True),
    (ID_CARD_RE_PATTERN, "11010519491231002x", True),
    (ID_CARD_RE_PATTERN, "110105490101001", True),
    (ID_CARD_RE_PATTERN, "132201780101001", True),
    (ID_CARD_RE_PATTERN, "11010519491231002", False),
    (ID_CARD_RE_PATTERN, "1101051949123100211", False),
    (ID_CARD_RE_PATTERN, "11010549010100X", False),
    # 邮箱：域名 label 首尾为字母数字、不超过 63 字符。
    (EMAIL_RE_PATTERN, "a@b.cn", True),
    (EMAIL_RE_PATTERN, "user.name+tag@sub.example.com", True),
    (EMAIL_RE_PATTERN, "a@b-c.cn", True),
    (EMAIL_RE_PATTERN, "a@" + "b" * 63 + ".cn", True),
    (EMAIL_RE_PATTERN, "a@b", False),
    (EMAIL_RE_PATTERN, "a@-b.cn", False),
    (EMAIL_RE_PATTERN, "a@b-.cn", False),
    (EMAIL_RE_PATTERN, "a@" + "b" * 64 + ".cn", False),
    # 银行卡号：13~19 位纯数字。
    (BANK_CARD_RE_PATTERN, "1234567890123", True),
    (BANK_CARD_RE_PATTERN, "6222020200112233", True),
    (BANK_CARD_RE_PATTERN, "1234567890123456789", True),
    (BANK_CARD_RE_PATTERN, "123456789012", False),
    (BANK_CARD_RE_PATTERN, "12345678901234567890", False),
    (BANK_CARD_RE_PATTERN, "622202020011223a", False),
    # IPv4：四段点分十进制、每段 0-255。
    (IPV4_RE_PATTERN, "192.168.1.10", True),
    (IPV4_RE_PATTERN, "1.2.3.4", True),
    (IPV4_RE_PATTERN, "255.255.255.255", True),
    (IPV4_RE_PATTERN, "256.1.1.1", False),
    (IPV4_RE_PATTERN, "1.2.3", False),
    (IPV4_RE_PATTERN, "1.2.3.4.5", False),
    # IPv6：大小写不敏感（编译期 IGNORECASE），十六进制组 1-4 位。
    (IPV6_RE_PATTERN, "2001:db8::1", True),
    (IPV6_RE_PATTERN, "2001:DB8::1", True),
    (IPV6_RE_PATTERN, "::1", True),
    (IPV6_RE_PATTERN, "fe80::1", True),
    (IPV6_RE_PATTERN, "1:2:3:4:5:6:7:8", True),
    (IPV6_RE_PATTERN, "12345::1", False),
    (IPV6_RE_PATTERN, "2001:db8::1::1", False),
    (IPV6_RE_PATTERN, "1:2:3:4:5:6:7:8:9", False),
    # IPv4|IPv6 组合。
    (IP_RE_PATTERN, "192.168.1.10", True),
    (IP_RE_PATTERN, "2001:db8::1", True),
    (IP_RE_PATTERN, "2001:DB8::1", True),
    (IP_RE_PATTERN, "::1", True),
    (IP_RE_PATTERN, "1.2.3", False),
    (IP_RE_PATTERN, "12345::1", False),
)

# 全部导出常量。
_ALL_PATTERNS: tuple[re.Pattern[str], ...] = (
    BANK_CARD_RE_PATTERN,
    EMAIL_RE_PATTERN,
    ID_CARD_RE_PATTERN,
    IP_RE_PATTERN,
    IPV4_RE_PATTERN,
    IPV6_RE_PATTERN,
    PHONE_RE_PATTERN,
    TELEPHONE_RE_PATTERN,
)


@pytest.mark.parametrize(("pattern", "text", "expected"), _CASES)
def test_pattern_fullmatch(pattern: re.Pattern[str], text: str, expected: bool) -> None:
    """各模式对整串匹配的正反例行为符合预期。"""
    assert (pattern.fullmatch(text) is not None) == expected, (
        f"{pattern.pattern!r} 对 {text!r} 的整串匹配结果应为 {expected}"
    )


def test_all_patterns_are_compiled() -> None:
    """所有导出常量均为预编译 re.Pattern（py.typed 分发保持类型稳定）。"""
    for pattern in _ALL_PATTERNS:
        assert isinstance(pattern, re.Pattern)


def test_ip_combination_is_case_insensitive() -> None:
    """IP_RE_PATTERN 组合可匹配大写 IPv6（回归：内联 (?i) 拼接编译崩溃）。"""
    assert IP_RE_PATTERN.flags & re.IGNORECASE
    assert IP_RE_PATTERN.fullmatch("FE80::1")
