"""显式选用的预置规则集：中国大陆常见个人信息的文本识别规则。

预置规则只做"识别 + 全星"这一最安全的默认：每条规则绑定无参
KeepStrategy()（整段掩码），不含保留位等业务格式断言——具体格式由使用方
按需派生，例如::

    phone_rule = PHONE_RULE.with_strategy(
        KeepStrategy(prefix=3, suffix=4)
    )

规则识别器均为 RegexMatcher；银行卡规则（_BankCardMatcher）在正则定位
候选后叠加 Luhn 校验，经识别器确认钩子过滤伪号——识别器随内容定义，保持
matchers 模块的机制纯净。

本模块不自动生效，须显式传入 Masker::

    from tea_tool.masking import Masker
    from tea_tool.masking.presets import CN_PII_RULES

    masker = Masker(rules=CN_PII_RULES)

已知局限：

- IP_RULE 的 IPv4 分支无法区分四段点分十进制数字，版本号等（如 "1.2.3.4"）
  会被误判为 IP；IPv6 分支为简化实现，不覆盖内嵌 IPv4（如 "::ffff:1.2.3.4"）
  等形态；
- BANK_CARD_RULE 的 Luhn 校验只能排除偶然错误的数字串，不验证卡号真实
  存在或属于某发卡行：模 10 校验下约 1/10 的随机数字串仍能通过，伪造者
  亦可有意构造通过校验的号码，生产环境建议叠加更严格的上下文约束；
- ID_CARD_RULE 覆盖 18 位（含末位 X/x）与 15 位老身份证格式；15 位纯数
  字恰能通过 Luhn 校验的号码会同时命中银行卡规则，由身份证规则按更高优
  先级整段认领（默认整段掩码下输出无差异，派生保留位策略时需注意归属）；
- TELEPHONE_RULE 不校验区号真实性，0 开头的 10~12 位数字串（如 011 国际
  前缀形态）可能被误判为固话。
"""

from tea_tool.masking import KeepStrategy, MaskRule, RegexMatcher, TextMatch
from tea_tool.util.luhn import is_luhn_valid
from tea_tool.util.re import (
    BANK_CARD_RE_PATTERN,
    EMAIL_RE_PATTERN,
    ID_CARD_RE_PATTERN,
    IP_RE_PATTERN,
    PHONE_RE_PATTERN,
    TELEPHONE_RE_PATTERN,
)


class _BankCardMatcher(RegexMatcher):
    """银行卡识别器：正则定位候选后以 Luhn 校验确认，过滤伪号。

    供 BANK_CARD_RULE 使用；识别器属于"银行卡"内容，故随规则定义在
    本模块而非 matchers 模块（见模块 docstring）。
    """

    def accepts(self, match: TextMatch) -> bool:
        """仅接受通过 Luhn 校验的候选。

        Args:
            match: 正则定位到的候选。

        Returns:
            True 表示校验通过，False 表示丢弃。
        """
        return is_luhn_valid(match.value)


_default_strategy = KeepStrategy()

# 中国大陆手机号：1[3-9] 开头共 11 位。
PHONE_RULE = MaskRule(
    matcher=RegexMatcher.of(PHONE_RE_PATTERN),
    strategy=_default_strategy,
    priority=100,
)

# 固话：0 区号（3-4 位）+ 7/8 位号码，或 400 号码。
TELEPHONE_RULE = MaskRule(
    matcher=RegexMatcher.of(TELEPHONE_RE_PATTERN),
    strategy=_default_strategy,
    priority=90,
)

# 身份证（18 位含末位 X/x，或 15 位老证）：优先级高于银行卡，避免纯数字
# 身份证与银行卡规则竞争时被拆分命中。
ID_CARD_RULE = MaskRule(
    matcher=RegexMatcher.of(ID_CARD_RE_PATTERN),
    strategy=_default_strategy,
    priority=200,
)

# 邮箱。
EMAIL_RULE = MaskRule(
    matcher=RegexMatcher.of(EMAIL_RE_PATTERN),
    strategy=_default_strategy,
    priority=80,
)

# IPv4 & IPv6。
IP_RULE = MaskRule(
    matcher=RegexMatcher.of(IP_RE_PATTERN),
    strategy=_default_strategy,
    priority=50,
)

# 银行卡：正则定位 13~19 位数字串 + Luhn 校验确认（见模块 docstring）。
BANK_CARD_RULE = MaskRule(
    matcher=_BankCardMatcher.of(BANK_CARD_RE_PATTERN),
    strategy=_default_strategy,
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
