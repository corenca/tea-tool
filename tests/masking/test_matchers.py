"""tea_tool.masking.matchers 识别器层的单元测试。"""

import re
from dataclasses import FrozenInstanceError

import pytest

from tea_tool.masking.matchers import Matcher, RegexMatcher, TextMatch

DIGITS = r"\d+"


# ----------------------------------------------------------------------
# TextMatch：候选命中区间
# ----------------------------------------------------------------------


def test_text_match_fields() -> None:
    """候选携带区间与原文。"""
    match = TextMatch(start=2, end=5, value="123")
    assert match.start == 2
    assert match.end == 5
    assert match.value == "123"


def test_text_match_is_immutable() -> None:
    """候选为 frozen 数据，构造后不可修改。"""
    match = TextMatch(start=0, end=1, value="1")
    with pytest.raises(FrozenInstanceError):
        match.value = "2"  # type: ignore[misc]


# ----------------------------------------------------------------------
# Matcher：识别器接口
# ----------------------------------------------------------------------


def test_matcher_is_abstract() -> None:
    """接口不可直接实例化，须实现 find。"""
    with pytest.raises(TypeError):
        Matcher()  # type: ignore[abstract]


def test_matcher_accepts_defaults_to_true() -> None:
    """基类 accepts 默认接受全部候选（确认钩子按需覆写）。"""
    matcher = RegexMatcher(DIGITS)
    assert matcher.accepts(TextMatch(start=0, end=1, value="1")) is True


# ----------------------------------------------------------------------
# RegexMatcher：正则识别器
# ----------------------------------------------------------------------


def test_regex_matcher_find_hits() -> None:
    """正则定位全部候选，携带区间与原文。"""
    matcher = RegexMatcher(r"1[3-9]\d{9}")
    matches = matcher.find("手机 13812345678 与 13912345678")
    assert matches == [
        TextMatch(start=3, end=14, value="13812345678"),
        TextMatch(start=17, end=28, value="13912345678"),
    ]


def test_regex_matcher_find_no_hit() -> None:
    """无候选时返回空列表。"""
    assert RegexMatcher(DIGITS).find("这里没有数字") == []


def test_regex_matcher_accepts_compiled_pattern() -> None:
    """构造接受预编译的 re.Pattern。"""
    matcher = RegexMatcher(re.compile(DIGITS))
    assert [m.value for m in matcher.find("ab12cd34")] == ["12", "34"]


def test_regex_matcher_ignores_zero_width() -> None:
    """可零宽匹配的正则：零宽命中不构成可替换片段，find 时忽略。"""
    matcher = RegexMatcher(r"\d*")
    assert [m.value for m in matcher.find("ab12cd")] == ["12"]


def test_regex_matcher_empty_pattern_raises() -> None:
    """空正则构造时拒绝，避免零宽命中污染脱敏结果。"""
    with pytest.raises(ValueError, match="pattern"):
        RegexMatcher("")


# ----------------------------------------------------------------------
# 自定义识别器：接口子类扩展点
# ----------------------------------------------------------------------


class _KeywordMatcher(Matcher):
    """测试用：以整词扫描定位关键词候选（非正则实现）。"""

    def __init__(self, keyword: str) -> None:
        """构造关键词识别器。

        Args:
            keyword: 待定位的关键词。
        """
        self._keyword = keyword

    def find(self, text: str) -> list[TextMatch]:
        """定位全部整词候选。

        Args:
            text: 待扫描文本。

        Returns:
            出现顺序排列的候选列表。
        """
        matches: list[TextMatch] = []
        for match in re.finditer(r"\S+", text):
            if match.group() == self._keyword:
                matches.append(
                    TextMatch(start=match.start(), end=match.end(), value=match.group())
                )
        return matches


def test_custom_matcher_implements_interface() -> None:
    """非正则识别器同样作为子类工作：定位结果与正则实现一致。"""
    matcher = _KeywordMatcher("卡号")
    assert matcher.find("卡号 12345678 与 卡号 87654321") == [
        TextMatch(start=0, end=2, value="卡号"),
        TextMatch(start=14, end=16, value="卡号"),
    ]
