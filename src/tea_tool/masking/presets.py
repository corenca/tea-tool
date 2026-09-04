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

- IP_RULE 无法区分 IPv4 与四段点分十进制数字，版本号等（如 "1.2.3.4"）
  会被误判为 IP；
- BANK_CARD_RULE 只按 13~19 位纯数字串识别，不做 Luhn 校验，生产环境建议
  叠加 Luhn 或更严格的上下文约束；
- ID_CARD_RULE 仅覆盖中国大陆 18 位身份证格式（含末位 X/x）。
"""

from .rules import MaskRule
from .strategies import KeepStrategy

# 中国大陆手机号：1[3-9] 开头共 11 位。
PHONE_RULE = MaskRule(
    pattern=r"(?<!\d)1[3-9]\d{9}(?!\d)",
    strategy=KeepStrategy(),
    priority=100,
)

# 18 位身份证：优先级高于银行卡，避免纯数字身份证被银行卡规则拆分命中。
ID_CARD_RULE = MaskRule(
    pattern=r"(?<!\d)\d{17}[\dXx](?!\d)",
    strategy=KeepStrategy(),
    priority=200,
)

# 邮箱。
EMAIL_RULE = MaskRule(
    pattern=(
        r"(?<![\w.+-])"
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
        r"@"
        r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"
        r"(?![\w.-])"
    ),
    strategy=KeepStrategy(),
    priority=80,
)

# IPv4。
IP_RULE = MaskRule(
    pattern=(
        r"(?<![\d.])"
        r"(?:"
        r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\."
        r"){3}"
        r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
        r"(?![\d.])"
    ),
    strategy=KeepStrategy(),
    priority=50,
)

# 银行卡：只负责发现 13~19 位数字串，不做 Luhn 校验（见模块 docstring）。
BANK_CARD_RULE = MaskRule(
    pattern=r"(?<!\d)\d{13,19}(?!\d)",
    strategy=KeepStrategy(),
    priority=150,
)

# 中国大陆常见个人信息规则组合，按优先级降序：
# 身份证(200) > 银行卡(150) > 手机号(100) > 邮箱(80) > IP(50)。
CN_PII_RULES = [
    ID_CARD_RULE,
    BANK_CARD_RULE,
    PHONE_RULE,
    EMAIL_RULE,
    IP_RULE,
]
