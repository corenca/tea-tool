"""tea_tool.masking.presets 预置规则集的单元测试。"""

from tea_tool.masking import KeepStrategy, MaskRule, RegexMatcher
from tea_tool.masking.presets import (
    BANK_CARD_RULE,
    CN_PII_RULES,
    EMAIL_RULE,
    ID_CARD_RULE,
    IP_RULE,
    PHONE_RULE,
    TELEPHONE_RULE,
)

# 各测试共用的卡号素材：Visa 公开测试卡号（通过 Luhn）与其破坏校验位的近真伪号。
VISA_TEST_CARD = "4111111111111111"
FAKE_CARD = "4111111111111112"


def test_presets_composition() -> None:
    """CN_PII_RULES 包含六条规则，均为识别器 + 全星策略。"""
    assert CN_PII_RULES == [
        ID_CARD_RULE,
        BANK_CARD_RULE,
        PHONE_RULE,
        TELEPHONE_RULE,
        EMAIL_RULE,
        IP_RULE,
    ]
    for rule in CN_PII_RULES:
        assert isinstance(rule, MaskRule)
        assert isinstance(rule.matcher, RegexMatcher)
        assert isinstance(rule.strategy, KeepStrategy)
        assert rule.strategy.prefix == 0 and rule.strategy.suffix == 0


def test_preset_priorities_ordering() -> None:
    """预置规则优先级与组合顺序一致（身份证 > 银行卡 > 手机 > 固话 > 邮箱 > IP）。"""
    priorities = [rule.priority for rule in CN_PII_RULES]
    assert priorities == sorted(priorities, reverse=True)


def test_bank_card_rule_filters_by_luhn() -> None:
    """银行卡规则在正则定位后经 Luhn 确认：真卡命中、伪卡丢弃。"""
    assert [m.value for m in BANK_CARD_RULE.find("卡号 " + VISA_TEST_CARD)] == [
        VISA_TEST_CARD
    ]
    assert BANK_CARD_RULE.find("数字 " + FAKE_CARD) == []
