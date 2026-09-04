"""显式选用的预置规则集：中国大陆常见个人信息的文本识别规则。

预置规则只做"识别 + 全星"这一最安全的默认：每条规则绑定无参
KeepStrategy()（整段掩码），不含保留位等业务格式断言——具体格式由使用方
按需派生，例如::

    phone_rule = PHONE_RULE.with_strategy(
        KeepStrategy(prefix=3, suffix=4)
    )

本模块不自动生效，须显式传入 Masker::

    from tea_tool.masking import Masker
    from tea_tool.masking.presets import CN_PII_RULES

    masker = Masker(rules=CN_PII_RULES)

已知局限：

- IP_RULE 的 IPv4 分支无法区分四段点分十进制数字，版本号等（如 "1.2.3.4"）
  会被误判为 IP；IPv6 分支为简化实现，不覆盖内嵌 IPv4（如 "::ffff:1.2.3.4"）
  等形态；
- BANK_CARD_RULE 只按 13~19 位纯数字串识别，不做 Luhn 校验，生产环境建议
  叠加 Luhn 或更严格的上下文约束；
- ID_CARD_RULE 覆盖 18 位（含末位 X/x）与 15 位老身份证格式；15 位纯数字
  分支无法与 15 位银行卡号等纯数字串区分，会按最高优先级整段认领（默认
  整段掩码下输出无差异，派生保留位策略时需注意归属）；
- TELEPHONE_RULE 不校验区号真实性，0 开头的 10~12 位数字串（如 011 国际
  前缀形态）可能被误判为固话。
"""

from tea_tool.masking import KeepStrategy, MaskRule
from tea_tool.util.re import (
    BANK_CARD_RE_PATTERN,
    EMAIL_RE_PATTERN,
    ID_CARD_RE_PATTERN,
    IP_RE_PATTERN,
    PHONE_RE_PATTERN,
    TELEPHONE_RE_PATTERN,
)

# 中国大陆手机号：1[3-9] 开头共 11 位。
PHONE_RULE = MaskRule(
    pattern=PHONE_RE_PATTERN,
    strategy=KeepStrategy(),
    priority=100,
)

# 固话：0 区号（3-4 位）+ 7/8 位号码，或 400 号码。
TELEPHONE_RULE = MaskRule(
    pattern=TELEPHONE_RE_PATTERN,
    strategy=KeepStrategy(),
    priority=90,
)

# 身份证（18 位含末位 X/x，或 15 位老证）：优先级高于银行卡，避免纯数字
# 身份证被银行卡规则拆分命中。
ID_CARD_RULE = MaskRule(
    pattern=ID_CARD_RE_PATTERN,
    strategy=KeepStrategy(),
    priority=200,
)

# 邮箱。
EMAIL_RULE = MaskRule(
    pattern=EMAIL_RE_PATTERN,
    strategy=KeepStrategy(),
    priority=80,
)

# IPv4 & IPv6。
IP_RULE = MaskRule(
    pattern=IP_RE_PATTERN,
    strategy=KeepStrategy(),
    priority=50,
)

# 银行卡：只负责发现 13~19 位数字串，不做 Luhn 校验（见模块 docstring）。
BANK_CARD_RULE = MaskRule(
    pattern=BANK_CARD_RE_PATTERN,
    strategy=KeepStrategy(),
    priority=150,
)

# 中国大陆常见个人信息规则组合，按优先级降序：
# 身份证(200) > 银行卡(150) > 手机号(100) > 固话(90) > 邮箱(80) > IP(50)。
CN_PII_RULES = [
    ID_CARD_RULE,
    BANK_CARD_RULE,
    PHONE_RULE,
    TELEPHONE_RULE,
    EMAIL_RULE,
    IP_RULE,
]
