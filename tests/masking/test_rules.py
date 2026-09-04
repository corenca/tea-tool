"""tea_tool.masking.rules 规则模型与文本命中的单元测试。"""

import re

import pytest
from pydantic import ValidationError

from tea_tool.masking import KeepStrategy, Masker, MaskMatch, MaskRule
from tea_tool.masking.matchers import RegexMatcher, TextMatch
from tea_tool.masking.presets import ID_CARD_RULE, PHONE_RULE

# matcher 字段可接受的三种输入形式：正则字符串、预编译 Pattern、识别器实例。
MatcherInput = str | re.Pattern[str] | RegexMatcher

# 各测试共用的典型策略：手机号保留 3+4。
PHONE_MASK = KeepStrategy(prefix=3, suffix=4)

MASK_CHAR = "*"


def _stars(text: str) -> str:
    """生成与 text 等长的掩码串。"""
    return MASK_CHAR * len(text)


# ----------------------------------------------------------------------
# 规则层：MaskRule.find
# ----------------------------------------------------------------------


def test_mask_rule_find_hits() -> None:
    """规则在文本中找出全部命中，携带区间、原文与所属规则的处理信息。"""
    matches = PHONE_RULE.find("手机 13812345678 与 13912345678")
    assert [m.value for m in matches] == ["13812345678", "13912345678"]
    assert matches[0].start == 3
    assert matches[0].end == 3 + 11
    assert matches[0].strategy is PHONE_RULE.strategy
    assert matches[0].priority == PHONE_RULE.priority


def test_mask_rule_find_no_hit() -> None:
    """无命中时返回空列表。"""
    assert PHONE_RULE.find("这里没有手机号") == []


def test_mask_rule_find_accepts_all_matcher_inputs() -> None:
    """matcher 字段接受正则字符串、预编译 Pattern 与识别器实例。"""
    matcher_inputs: list[MatcherInput] = [
        r"\d+",
        re.compile(r"\d+"),
        RegexMatcher(r"\d+"),
    ]
    for matcher in matcher_inputs:
        rule = MaskRule(matcher=matcher, strategy=KeepStrategy())
        assert [m.value for m in rule.find("ab12cd34")] == ["12", "34"]


class _LongEnoughMatcher(RegexMatcher):
    """测试用：仅接受长度不少于 11 的候选（模拟 Luhn 式真实性确认）。"""

    def accepts(self, match: TextMatch) -> bool:
        """确认候选长度达标。

        Args:
            match: 待确认的候选。

        Returns:
            True 表示接受该候选，False 表示丢弃。
        """
        return len(match.value) >= 11


def test_mask_rule_find_keeps_accepted_candidates_only() -> None:
    """未通过 matcher.accepts 确认的候选不构成命中，丢弃处理。"""
    rule = MaskRule(
        matcher=_LongEnoughMatcher(r"\d+"),
        strategy=KeepStrategy(),
        priority=7,
    )
    matches = rule.find("13812345678 与 12 和 13912345678")
    assert [m.value for m in matches] == ["13812345678", "13912345678"]
    assert matches[0].start == 0
    assert matches[0].strategy is rule.strategy
    assert matches[0].priority == 7


def test_mask_rule_find_ignores_zero_width() -> None:
    """可零宽匹配的正则：零宽命中不构成可替换片段，find 时忽略。"""
    rule = MaskRule(matcher=r"\d*", strategy=KeepStrategy())
    assert [m.value for m in rule.find("ab12cd")] == ["12"]


def test_mask_match_length() -> None:
    """命中长度等于区间长度。"""
    match = MaskMatch(
        strategy=KeepStrategy(),
        priority=1,
        start=3,
        end=14,
        value="13812345678",
    )
    assert match.length == 11


def test_mask_rule_is_immutable() -> None:
    """规则模型为 frozen 配置，字段不可修改。"""
    with pytest.raises(ValidationError):
        PHONE_RULE.priority = 999


def test_mask_rule_empty_pattern_raises() -> None:
    """空正则构造时拒绝，避免零宽命中污染脱敏结果。"""
    with pytest.raises(ValidationError, match="pattern"):
        MaskRule(matcher="", strategy=KeepStrategy())


def test_mask_rule_rejects_non_matcher_input() -> None:
    """matcher 只接受识别器或正则，其余输入显式报错。"""
    with pytest.raises(ValidationError, match="matcher"):
        MaskRule(matcher=42, strategy=KeepStrategy())  # type: ignore[arg-type]


def test_mask_rule_unknown_field_raises() -> None:
    """拼错字段名时显式报错，配置不静默丢失。"""
    with pytest.raises(ValidationError):
        MaskRule(matcher=r"\d+", strategy=KeepStrategy(), priotiy=1)


# ----------------------------------------------------------------------
# 规则层：MaskRule.with_strategy
# ----------------------------------------------------------------------


def test_mask_rule_with_strategy_returns_new_rule() -> None:
    """with_strategy 派生新规则：仅换策略，matcher 与优先级不变。"""
    derived = PHONE_RULE.with_strategy(PHONE_MASK)
    assert isinstance(derived, MaskRule)
    assert derived is not PHONE_RULE
    assert derived.matcher is PHONE_RULE.matcher
    assert derived.priority == PHONE_RULE.priority
    assert derived.strategy is PHONE_MASK


def test_mask_rule_with_strategy_keeps_original_unchanged() -> None:
    """派生不改写原规则：原规则仍是全星策略且可正常使用。"""
    PHONE_RULE.with_strategy(PHONE_MASK)
    assert PHONE_RULE.strategy is not PHONE_MASK
    masker = Masker(rules=[PHONE_RULE])
    assert masker.mask_text("联系 13812345678") == ("联系 " + _stars("13812345678"))


def test_mask_rule_with_strategy_overrides_priority() -> None:
    """显式传入 priority 时派生规则使用新优先级，原规则优先级不变。"""
    derived = ID_CARD_RULE.with_strategy(PHONE_MASK, priority=210)
    assert derived.strategy is PHONE_MASK
    assert derived.priority == 210
    assert derived.matcher is ID_CARD_RULE.matcher
    assert ID_CARD_RULE.priority == 200
