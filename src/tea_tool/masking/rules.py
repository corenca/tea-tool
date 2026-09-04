"""文本发现层：规则在自由文本中定位敏感片段。

MaskRule 将"识别（matcher）"与"处理（策略）"绑定为一条完整规则：识别器
（Matcher，见 matchers 模块）定位候选区间并确认其真实命中，同时决定脱敏
方式。MaskMatch 是规则的一次命中结果，平铺携带处理所需信息（策略与优先
级），供编排层做重叠消解后替换。依赖方向（MaskRule → MaskMatch、
MaskRule → Matcher）均为单向，因此本模块无需延迟注解求值。

模型直接继承 pydantic.BaseModel（不经过 tea_tool.schema.BaseModel）：规则
值对象需要的是"不可变 + 拒绝未声明字段"而非 ORM 数据模型的宽松配置——
规则字段拼错应显式报错，避免脱敏静默失效。
"""

from re import Pattern
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator

from .matchers import Matcher, RegexMatcher
from .strategies import MaskStrategy


class _MaskModel(BaseModel):
    """masking 包内模型的公共配置：不可变、拒绝未声明字段、允许非 pydantic 字段。"""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )


class MaskMatch(_MaskModel):
    """规则在文本中的一次命中结果。

    Attributes:
        strategy: 命中所属规则的脱敏策略。
        priority: 命中所属规则的优先级，供重叠消解排序。
        start: 命中区间起点（含）。
        end: 命中区间终点（不含）。
        value: 命中的原始文本。
    """

    strategy: MaskStrategy
    priority: int
    start: int
    end: int
    value: str

    @property
    def length(self) -> int:
        """命中区间长度（end - start）。"""
        return self.end - self.start


class MaskRule(_MaskModel):
    """文本脱敏规则：识别器定位 + 策略处理。

    Attributes:
        matcher: 定位并确认敏感片段的识别器，可为 Matcher 实例，或正则
            表达式（字符串/预编译 Pattern——构造期自动包装为
            RegexMatcher，见 _coerce_matcher）。
        strategy: 命中片段采用的脱敏策略。
        priority: 与其他规则区间重叠时的优先级，数值大者优先，默认 0。
    """

    matcher: Matcher
    strategy: MaskStrategy
    priority: int = 0

    @field_validator("matcher", mode="before")
    @classmethod
    def _coerce_matcher(cls, matcher: object) -> Matcher:
        """把正则表达式包装为正则识别器，识别器子类原样通过。

        便捷入口：matcher 直接传正则字符串或预编译 Pattern 时，构造期即
        包装为 RegexMatcher；空正则在 RegexMatcher 构造期被拒绝（零宽命
        中无定位能力），配置错误尽早暴露。Matcher 的非正则实现（如带
        Luhn 确认的银行卡识别器）由使用方显式传入实例。

        Args:
            matcher: 构造传入的识别器或正则表达式。

        Returns:
            可用的 Matcher 实例。

        Raises:
            ValueError: matcher 既非 Matcher 实例亦非正则表达式。
        """
        if isinstance(matcher, (str, Pattern)):
            return RegexMatcher(matcher)
        if isinstance(matcher, Matcher):
            return matcher
        raise ValueError("matcher 必须是 Matcher 实例或正则表达式")

    def find(self, text: str) -> list[MaskMatch]:
        """在文本中查找本规则的全部命中。

        候选区间由 matcher 定位并经其确认（accepts）——Luhn 等真实性
        校验在识别器内部完成；确认通过的候选按出现顺序组装为本规则的
        命中。matcher 契约保证候选非零宽（start < end），不构成可替换
        片段的零宽区间由识别器实现自行忽略。

        Args:
            text: 待扫描文本。

        Returns:
            按出现顺序排列的命中列表；无命中时为空列表。
        """
        return [
            MaskMatch(
                strategy=self.strategy,
                priority=self.priority,
                start=match.start,
                end=match.end,
                value=match.value,
            )
            for match in self.matcher.find(text)
            if self.matcher.accepts(match)
        ]

    def with_strategy(
        self,
        strategy: MaskStrategy,
        *,
        priority: int | None = None,
    ) -> Self:
        """派生新规则：替换脱敏策略，可一并显式指定新优先级。

        原规则不可变且不受影响，已注入 Masker 的规则不会被派生改写；
        派生结果通常用于替换原规则（如定制预置规则为保留位格式）。
        需要让派生规则与原规则共存并胜出时，显式传入更高的 priority，
        如 ID_CARD_RULE.with_strategy(mask, priority=210)。

        Args:
            strategy: 新规则的脱敏策略。
            priority: 新规则的优先级；None（默认）时沿用原规则的值。

        Returns:
            携带新策略、其余字段（matcher 与优先级）与原规则一致的新规则实例。
        """
        update: dict[str, object] = {"strategy": strategy}
        if priority is not None:
            update["priority"] = priority
        return self.model_copy(update=update)
