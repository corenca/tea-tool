"""通用脱敏工具：机制与内容分离。

本包提供脱敏机制——策略（strategies）、识别器（matchers）、文本发现规则
（rules）与编排器（Masker），不内置任何"哪些信息敏感、脱成什么样"的业务
默认。规则与格式由使用方显式定义，可选用 presets 模块的预置规则集。

典型用法（业务侧全局定义一次后复用）::

    from tea_tool.masking import Masker, KeepStrategy
    from tea_tool.masking.presets import CN_PII_RULES

    phone_mask = KeepStrategy(prefix=3, suffix=4)
    masker = Masker(rules=CN_PII_RULES)

    masker.mask("13812345678", phone_mask)          # 138****5678
    masker.mask_text("联系 13812345678")            # 联系 ***********
    masker.mask_dict(data, fields={"phone": phone_mask})
"""

from .core import Masker
from .matchers import Matcher, RegexMatcher, TextMatch
from .rules import MaskMatch, MaskRule
from .strategies import (
    HashStrategy,
    KeepStrategy,
    MaskStrategy,
    RemoveStrategy,
    ReplaceStrategy,
)

__all__ = [
    "HashStrategy",
    "KeepStrategy",
    "MaskMatch",
    "MaskRule",
    "MaskStrategy",
    "Masker",
    "Matcher",
    "RegexMatcher",
    "RemoveStrategy",
    "ReplaceStrategy",
    "TextMatch",
]
