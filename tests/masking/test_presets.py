"""tea_tool.masking.presets 预置规则集的单元测试。"""

import re

from tea_tool.masking import KeepStrategy, MaskRule
from tea_tool.masking.presets import (
    BANK_CARD_RULE,
    CN_PII_RULES,
    EMAIL_RULE,
    ID_CARD_RULE,
    IP_RULE,
    PHONE_RULE,
    TELEPHONE_RULE,
)


def test_presets_composition() -> None:
    """CN_PII_RULES 包含六条规则，均为识别+全星策略。"""
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
        assert isinstance(rule.pattern, re.Pattern)
        assert isinstance(rule.strategy, KeepStrategy)
        assert rule.strategy.prefix == 0 and rule.strategy.suffix == 0


def test_preset_priorities_ordering() -> None:
    """预置规则优先级与组合顺序一致（身份证 > 银行卡 > 手机 > 固话 > 邮箱 > IP）。"""
    priorities = [rule.priority for rule in CN_PII_RULES]
    assert priorities == sorted(priorities, reverse=True)
